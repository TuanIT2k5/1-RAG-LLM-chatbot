from pathlib import Path
from typing import Dict

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.text_splitter import RecursiveTextSplitter
from app.services.vector_store import VectorStore
from app.utils.file_validator import DOCX_MIME, PDF_MIME
from tests.unit.test_embedding_service import FakeBGEM3Model


def test_indexing_pipeline_end_to_end_pdf_and_docx(
    sample_files: Dict[str, Path],
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    [SP3-03.1, SP3-03.2, SP3-03.4] Kiểm tra đường ống Indexing Pipeline khép kín:
    Nhận tệp -> Trích xuất -> Làm sạch -> Chia Chunk -> Sinh Embedding -> Lưu ChromaDB
    -> Cập nhật trạng thái 'processed' và ghi log thời gian từng công đoạn.
    """
    caplog.set_level("INFO")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    embedding_service = EmbeddingService()
    embedding_service.set_model(FakeBGEM3Model(dim=1024))
    vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")
    uploads_dir = tmp_path / "uploads"

    with TestingSession() as db:
        service = DocumentService(
            db=db,
            embedding_service=embedding_service,
            vector_store=vector_store,
            text_splitter=RecursiveTextSplitter(chunk_size=60, chunk_overlap=10),
        )

        # 1. Nạp tệp PDF 25 trang
        with sample_files["pdf_25_pages"].open("rb") as f_pdf:
            doc_pdf = service.ingest_upload(
                upload_file=f_pdf,
                filename="Bo_luat_25_trang.pdf",
                content_type=PDF_MIME,
                upload_dir=uploads_dir,
            )

        assert doc_pdf.status == "processed"
        assert doc_pdf.chunk_count >= 25
        assert doc_pdf.error_message is None
        assert vector_store.count_by_document_id(doc_pdf.id) == doc_pdf.chunk_count

        # 2. Nạp tệp DOCX có tiêu đề và bảng biểu
        with sample_files["docx_with_table"].open("rb") as f_docx:
            doc_docx = service.ingest_upload(
                upload_file=f_docx,
                filename="Noi_quy_Cong_ty.docx",
                content_type=DOCX_MIME,
                upload_dir=uploads_dir,
            )

        assert doc_docx.status == "processed"
        assert doc_docx.chunk_count >= 1
        assert vector_store.count_by_document_id(doc_docx.id) == doc_docx.chunk_count
        assert vector_store.count() == doc_pdf.chunk_count + doc_docx.chunk_count

        # Kiểm tra log ghi nhận thời gian thực thi của các công đoạn ([SP3-03.4])
        log_output = "\n".join(caplog.messages)
        assert "extract=" in log_output
        assert "chunk=" in log_output
        assert "embed=" in log_output
        assert "store=" in log_output


def test_indexing_pipeline_rollback_on_failure(
    sample_files: Dict[str, Path],
    tmp_path: Path,
) -> None:
    """
    [SP3-03.3] Kiểm tra cơ chế Rollback: khi bước lưu ChromaDB hoặc Embedding gặp lỗi,
    hệ thống tự động dọn dẹp dữ liệu vector dở dang và đánh dấu trạng thái 'failed' trong CSDL.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    embedding_service = EmbeddingService()
    embedding_service.set_model(FakeBGEM3Model(dim=1024))
    vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")
    uploads_dir = tmp_path / "uploads"

    # Giả lập lỗi xảy ra sau khi đã ghi một phần dữ liệu vào ChromaDB
    original_add_chunks = vector_store.add_chunks

    def failing_add_chunks(texts, embeddings, metadatas, chunk_ids, batch_size=256):
        # Ghi thử 1 chunk đầu tiên rồi ném lỗi để kiểm tra rollback xóa sạch chunk dở dang
        original_add_chunks(
            texts[:1],
            embeddings[:1],
            metadatas[:1],
            chunk_ids[:1],
        )
        raise RuntimeError("Simulated ChromaDB disk write error midway")

    vector_store.add_chunks = failing_add_chunks  # type: ignore[method-assign]

    with TestingSession() as db:
        service = DocumentService(
            db=db,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        with pytest.raises(RuntimeError, match="Simulated ChromaDB disk write error"):
            with sample_files["docx_with_table"].open("rb") as f_docx:
                service.ingest_upload(
                    upload_file=f_docx,
                    filename="Loi_giua_chung.docx",
                    content_type=DOCX_MIME,
                    upload_dir=uploads_dir,
                )

        # Kiểm tra bản ghi trong DB đã được chuyển sang 'failed' kèm error_message
        docs = service.list_documents()
        assert len(docs) == 1
        failed_doc = docs[0]
        assert failed_doc.status == "failed"
        assert failed_doc.chunk_count == 0
        assert "Simulated ChromaDB disk write error" in (failed_doc.error_message or "")

        # Kiểm tra dữ liệu dở dang trong ChromaDB đã được dọn sạch hoàn toàn (0 chunk)
        assert vector_store.count_by_document_id(failed_doc.id) == 0
        assert vector_store.count() == 0
