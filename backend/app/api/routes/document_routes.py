from typing import Optional
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import get_document_service
from app.schemas.document_schema import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusType,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tải lên tệp PDF/DOCX và kích hoạt đường ống lập chỉ mục RAG",
)
def upload_document(
    file: UploadFile = File(
        ...,
        description="Tệp tài liệu định dạng .pdf hoặc .docx (dung lượng tối đa 20MB)",
    ),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """
    [SP4-04.1] Tiếp nhận tệp tải lên qua multipart/form-data:
    - Kiểm tra định dạng (.pdf, .docx), chữ ký MIME và giới hạn dung lượng (<= 20MB).
    - Lưu tệp vật lý an toàn theo tên <uuid>.<ext> vào thư mục storage/uploads/.
    - Kích hoạt Indexing Pipeline (Trích xuất -> Làm sạch NFC -> Chia Chunk -> BAAI/bge-m3 -> ChromaDB).
    - Trả về thông tin chi tiết của tài liệu đã xử lý.
    """
    doc = document_service.ingest_upload(
        upload_file=file,
        filename=file.filename,
        content_type=file.content_type,
    )
    return DocumentUploadResponse(
        message="Tải lên và xử lý tài liệu thành công.",
        document=DocumentResponse.model_validate(doc),
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách tài liệu đã tải lên kèm trạng thái xử lý",
)
def list_documents(
    status_filter: Optional[DocumentStatusType] = Query(
        default=None,
        alias="status",
        description="Lọc theo trạng thái xử lý: processing | processed | failed",
    ),
    skip: int = Query(default=0, ge=0, description="Số bản ghi bỏ qua (phân trang)"),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Số lượng bản ghi tối đa trả về",
    ),
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """
    [SP4-04.2] Trả về danh sách các tài liệu đã tải lên kèm trạng thái xử lý
    (processing, processed, failed), kích thước (file_size), tổng số Chunk và ngày tạo (created_at).
    """
    docs = document_service.list_documents(
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    total = document_service.count_documents(status=status_filter)
    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.model_validate(d) for d in docs],
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Xem chi tiết thông tin một tài liệu và tổng số Chunk",
)
def get_document_detail(
    document_id: uuid.UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """
    [SP4-04.3] Trả về thông tin chi tiết của một tài liệu theo ID và tổng số Chunk
    đã lập chỉ mục (chunk_count). Trả về lỗi 404 (DOCUMENT_NOT_FOUND) nếu không tồn tại.
    """
    doc = document_service.get_document(document_id)
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Xóa đồng bộ tài liệu khỏi ChromaDB, ổ cứng và PostgreSQL",
)
def delete_document(
    document_id: uuid.UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    """
    [SP4-04.4] Thực hiện xóa đồng bộ tài liệu ở cả 3 nơi:
    1. Toàn bộ vector Chunks của tài liệu trong ChromaDB
    2. Tệp vật lý trong thư mục storage/uploads/
    3. Bản ghi trong cơ sở dữ liệu PostgreSQL
    """
    document_service.delete_document(document_id)
    return DocumentDeleteResponse(
        message="Đã xóa đồng bộ tài liệu khỏi hệ thống.",
        document_id=document_id,
    )

