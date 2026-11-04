from pathlib import Path
import time
from typing import BinaryIO, List, Optional, Union
import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import DocumentNotFoundException, EmptyDocumentException
from app.core.logging import get_logger
from app.database.models import Document
from app.database.repositories.document_repo import DocumentRepository
from app.schemas.document_schema import DocumentStatusUpdate
from app.services.document_processor import extract_document
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.text_splitter import RecursiveTextSplitter
from app.services.vector_store import VectorStore, get_vector_store
from app.utils.file_validator import validate_and_register_document
from app.utils.text_cleaner import clean_extracted_units

logger = get_logger(__name__)


class DocumentService:
    """
    [SP3-03.1 -> SP3-03.4] Dịch vụ điều phối toàn bộ vòng đời tài liệu và đường ống
    Indexing Pipeline: Nhận tệp -> Trích xuất -> Làm sạch -> Chia Chunk -> Sinh Embedding -> Lưu ChromaDB.
    """

    def __init__(
        self,
        db: Session,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        text_splitter: Optional[RecursiveTextSplitter] = None,
        default_upload_dir: Optional[Path] = None,
    ) -> None:
        self.db = db
        self.document_repo = DocumentRepository(db)
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()
        self.text_splitter = text_splitter or RecursiveTextSplitter()
        self.default_upload_dir = default_upload_dir

    def index_document(self, document: Document) -> Document:
        """
        [SP3-03.1 -> SP3-03.4] Thực thi đường ống lập chỉ mục khép kín cho một bản ghi Document:
        1. Trích xuất văn bản thô kèm metadata (PDF page_number / DOCX paragraph_index & section_title).
        2. Làm sạch và chuẩn hóa Unicode NFC.
        3. Chia nhỏ thành các Chunk có độ chồng lấp (overlap).
        4. Sinh vector embedding bằng BAAI/bge-m3.
        5. Lưu vào ChromaDB và cập nhật trạng thái 'processed' trong PostgreSQL.
        Nếu bất kỳ bước nào lỗi -> Rollback dọn dẹp ChromaDB và cập nhật trạng thái 'failed'.
        """
        pipeline_start = time.perf_counter()
        doc_id = document.id
        file_path = Path(document.storage_path)

        try:
            # Bước 1: Đọc tệp và trích xuất văn bản thô
            t0 = time.perf_counter()
            raw_units = extract_document(
                file_path=file_path,
                document_id=doc_id,
                filename=document.filename,
            )
            extract_ms = (time.perf_counter() - t0) * 1000.0

            # Bước 2 & 3: Làm sạch văn bản (NFC) và chia nhỏ thành các Chunk
            t1 = time.perf_counter()
            cleaned_units = clean_extracted_units(raw_units, merge_lines=True)
            if not cleaned_units:
                raise EmptyDocumentException(
                    message=f"Tài liệu '{document.filename}' không còn nội dung hợp lệ sau khi làm sạch.",
                    details={"document_id": str(doc_id), "filename": document.filename},
                )

            chunks = self.text_splitter.split_units(
                cleaned_units,
                clean_before_split=False,
            )
            if not chunks:
                raise EmptyDocumentException(
                    message=f"Không tạo được Chunk nào từ tài liệu '{document.filename}'.",
                    details={"document_id": str(doc_id), "filename": document.filename},
                )
            chunk_ms = (time.perf_counter() - t1) * 1000.0

            # Bước 4: Sinh vector embedding (BAAI/bge-m3)
            t2 = time.perf_counter()
            texts = [c.text for c in chunks]
            metadatas = [c.metadata for c in chunks]
            chunk_ids = [c.chunk_id for c in chunks]

            embeddings = self.embedding_service.encode_documents(
                texts=texts,
                normalize_embeddings=True,
            )
            embedding_ms = (time.perf_counter() - t2) * 1000.0

            # Bước 5: Lưu trữ bền vững vào ChromaDB
            t3 = time.perf_counter()
            saved_count = self.vector_store.add_chunks(
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                chunk_ids=chunk_ids,
            )
            store_ms = (time.perf_counter() - t3) * 1000.0

            # [SP3-03.2] Cập nhật trạng thái 'processed' và số lượng Chunk trong PostgreSQL
            updated_doc = self.document_repo.update_status(
                document_id=doc_id,
                update_data=DocumentStatusUpdate(
                    status="processed",
                    chunk_count=saved_count,
                    error_message=None,
                ),
            )
            total_ms = (time.perf_counter() - pipeline_start) * 1000.0

            # [SP3-03.4] Ghi log chi tiết thời gian thực thi của từng công đoạn
            logger.info(
                "Hoàn tất Indexing Pipeline cho tài liệu '%s' (id=%s, chunks=%d) | "
                "extract=%.1fms, chunk=%.1fms, embed=%.1fms, store=%.1fms, total=%.1fms",
                document.filename,
                doc_id,
                saved_count,
                extract_ms,
                chunk_ms,
                embedding_ms,
                store_ms,
                total_ms,
            )
            return updated_doc or document

        except Exception as exc:
            # [SP3-03.3] Cơ chế Rollback: xóa dữ liệu vector dở dang và đánh dấu 'failed'
            logger.error(
                "Lỗi trong Indexing Pipeline cho tài liệu '%s' (id=%s): %s. Đang thực hiện Rollback...",
                document.filename,
                doc_id,
                exc,
            )
            try:
                self.vector_store.delete_by_document_id(doc_id)
            except Exception as cleanup_exc:
                logger.warning(
                    "Không thể dọn dẹp vector ChromaDB khi rollback document_id=%s: %s",
                    doc_id,
                    cleanup_exc,
                )

            self.document_repo.update_status(
                document_id=doc_id,
                update_data=DocumentStatusUpdate(
                    status="failed",
                    chunk_count=0,
                    error_message=str(exc),
                ),
            )
            raise

    def ingest_upload(
        self,
        upload_file: Union[UploadFile, BinaryIO],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        max_size_bytes: Optional[int] = None,
        upload_dir: Optional[Path] = None,
    ) -> Document:
        """
        [SP3-03.1] Tiếp nhận tệp tải lên, kiểm tra hợp lệ, lưu tệp vật lý <uuid>.<ext>,
        tạo bản ghi 'processing' và chạy ngay đường ống Indexing Pipeline.
        """
        effective_upload_dir = upload_dir or self.default_upload_dir
        document = validate_and_register_document(
            db=self.db,
            upload_file=upload_file,
            filename=filename,
            content_type=content_type,
            user_id=user_id,
            max_size_bytes=max_size_bytes,
            upload_dir=effective_upload_dir,
        )
        return self.index_document(document)

    def list_documents(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        """Lấy danh sách tài liệu từ PostgreSQL."""
        return self.document_repo.list_documents(
            user_id=user_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def count_documents(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> int:
        """Đếm tổng số lượng tài liệu trong PostgreSQL thỏa mãn điều kiện lọc."""
        return self.document_repo.count_documents(
            user_id=user_id,
            status=status,
        )

    def get_document(self, document_id: uuid.UUID) -> Document:
        """Lấy chi tiết tài liệu theo ID; ném lỗi 404 nếu không tồn tại."""
        doc = self.document_repo.get_by_id(document_id)
        if doc is None:
            raise DocumentNotFoundException(document_id=str(document_id))
        return doc

    def count_document_chunks_in_vector_store(self, document_id: Union[uuid.UUID, str]) -> int:
        """
        [SP3-05.2] Kiểm tra số lượng Chunk hiện có của một tài liệu trong ChromaDB
        để phục vụ đối soát dữ liệu giữa PostgreSQL và Vector Store.
        """
        return self.vector_store.count_by_document_id(document_id)

    def delete_document(self, document_id: uuid.UUID) -> bool:
        """
        [SP3-05.1 & SP3-05.4] Xóa đồng bộ tài liệu ở cả 3 nơi:
        1. Kho vector ChromaDB (xóa toàn bộ các Chunk có metadata document_id tương ứng)
        2. Tệp vật lý trong thư mục storage/uploads/
        3. Bản ghi trong cơ sở dữ liệu PostgreSQL
        """
        doc = self.get_document(document_id)
        storage_path = Path(doc.storage_path)

        # 1. Xóa toàn bộ vector chunks trong ChromaDB ([SP3-05.1])
        deleted_chunks = self.vector_store.delete_by_document_id(doc.id)

        # 2. Xóa tệp gốc trên ổ cứng
        if storage_path.exists():
            storage_path.unlink(missing_ok=True)

        # 3. Xóa bản ghi trong PostgreSQL
        deleted = self.document_repo.delete(doc.id)
        logger.info(
            "Đã xóa đồng bộ tài liệu '%s' (id=%s, deleted_chunks=%d) khỏi ChromaDB, ổ cứng và PostgreSQL.",
            doc.filename,
            doc.id,
            deleted_chunks,
        )
        return deleted

