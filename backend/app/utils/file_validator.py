from dataclasses import dataclass
from pathlib import Path
import re
from typing import BinaryIO, Dict, Optional, Set, Tuple, Union
import uuid
import zipfile

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.core.exceptions import (
    EmptyDocumentException,
    FileTooLargeException,
    InvalidFileException,
)
from app.core.logging import get_logger
from app.database.models import Document
from app.database.repositories.document_repo import DocumentRepository
from app.schemas.document_schema import DocumentCreate

logger = get_logger(__name__)

# Kích thước mỗi khối đọc theo luồng (64KB)
STREAM_CHUNK_SIZE = 64 * 1024

# Ánh xạ phần mở rộng hợp lệ sang tập MIME type chuẩn ([SP2-01.1])
ALLOWED_MIME_TYPES: Dict[str, Set[str]] = {
    ".pdf": {
        "application/pdf",
        "application/x-pdf",
    },
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
}

PDF_MAGIC_HEADER = b"%PDF-"
ZIP_MAGIC_HEADER = b"PK\x03\x04"


@dataclass(frozen=True)
class SavedUploadResult:
    """Thông tin tệp vật lý sau khi đã kiểm tra an toàn và lưu xuống ổ cứng."""

    document_id: uuid.UUID
    original_filename: str
    storage_path: Path
    file_type: str
    file_size: int


def get_resolved_upload_dir(custom_upload_dir: Optional[Path] = None) -> Path:
    """Trả về đường dẫn tuyệt đối của thư mục lưu tệp tải lên (storage/uploads)."""
    if custom_upload_dir is not None:
        target = custom_upload_dir.resolve()
    else:
        raw_path = Path(settings.UPLOAD_DIR)
        target = (
            raw_path.resolve()
            if raw_path.is_absolute()
            else (BACKEND_DIR / raw_path).resolve()
        )
    target.mkdir(parents=True, exist_ok=True)
    return target


def sanitize_original_filename(filename: Optional[str]) -> str:
    """Làm sạch tên tệp gốc của người dùng, loại bỏ đường dẫn tương đối và ký tự điều khiển."""
    if not filename or not filename.strip():
        raise InvalidFileException(message="Tên tệp tải lên không được để trống.")

    # Thay thế dấu phân cách đường dẫn Windows/Unix để lấy đúng basename
    normalized = filename.replace("\\", "/").strip()
    base_name = Path(normalized).name

    # Loại bỏ ký tự điều khiển vô hình hoặc null byte
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", base_name).strip()
    if not cleaned or cleaned in {".", ".."}:
        raise InvalidFileException(message="Tên tệp tải lên không hợp lệ.")

    return cleaned[:255]


def validate_extension_and_mime(
    filename: Optional[str],
    content_type: Optional[str] = None,
) -> Tuple[str, str]:
    """
    [SP2-01.1] Kiểm tra phần mở rộng tệp (.pdf, .docx) và đối chiếu MIME type thực tế.
    Trả về bộ (clean_filename, file_type) với file_type là 'pdf' hoặc 'docx'.
    """
    clean_filename = sanitize_original_filename(filename)
    ext = Path(clean_filename).suffix.lower()

    if ext not in ALLOWED_MIME_TYPES:
        raise InvalidFileException(
            message=f"Định dạng tệp '{ext or 'không xác định'}' không được hỗ trợ. Chỉ chấp nhận .pdf và .docx.",
            details={"filename": clean_filename, "extension": ext},
        )

    # Chuẩn hóa MIME type (bỏ phần tham số phụ như '; charset=utf-8' nếu có)
    normalized_mime = (content_type or "").split(";")[0].strip().lower()
    allowed_mimes = ALLOWED_MIME_TYPES[ext]

    if not normalized_mime or normalized_mime not in allowed_mimes:
        raise InvalidFileException(
            message=(
                f"MIME type '{normalized_mime or 'trống'}' không khớp với định dạng tệp {ext}. "
                "Vui lòng tải lên tệp PDF hoặc DOCX hợp lệ."
            ),
            details={
                "filename": clean_filename,
                "extension": ext,
                "content_type": normalized_mime,
                "expected_mime_types": sorted(allowed_mimes),
            },
        )

    file_type = ext.lstrip(".")
    return clean_filename, file_type


def verify_file_signature(file_path: Path, file_type: str) -> None:
    """
    Kiểm tra chữ ký nhị phân (Magic Bytes) và cấu trúc thực tế của tệp trên đĩa
    nhằm chặn các tệp .exe, .zip hoặc văn bản giả mạo đổi đuôi thành .pdf/.docx (TC-03).
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise EmptyDocumentException(
            message="Tệp tải lên hoàn toàn rỗng (0 byte).",
            details={"file_type": file_type},
        )

    with file_path.open("rb") as f:
        header = f.read(8)

    if file_type == "pdf":
        if not header.startswith(PDF_MAGIC_HEADER):
            raise InvalidFileException(
                message="Nội dung tệp không phải là định dạng PDF hợp lệ (sai chữ ký %PDF-).",
                details={"file_type": file_type},
            )
    elif file_type == "docx":
        if not header.startswith(ZIP_MAGIC_HEADER) or not zipfile.is_zipfile(file_path):
            raise InvalidFileException(
                message="Nội dung tệp không phải là định dạng Word (.docx) hợp lệ.",
                details={"file_type": file_type},
            )
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                archive_names = set(zf.namelist())
        except zipfile.BadZipFile as exc:
            raise InvalidFileException(
                message="Cấu trúc gói tệp .docx bị hỏng hoặc không hợp lệ.",
                details={"error": str(exc)},
            ) from exc

        if "word/document.xml" not in archive_names:
            raise InvalidFileException(
                message="Tệp nén không chứa cấu trúc tài liệu Word (thiếu word/document.xml).",
                details={"file_type": file_type},
            )


def build_safe_storage_path(
    file_type: str,
    document_id: Optional[uuid.UUID] = None,
    upload_dir: Optional[Path] = None,
) -> Tuple[uuid.UUID, Path]:
    """
    [SP2-01.3] Sinh mã UUID v4 làm tên tệp lưu trên ổ cứng (storage/uploads/<uuid>.<ext>)
    và kiểm tra chống tấn công Path Traversal.
    """
    clean_ext = file_type.lower().lstrip(".")
    if clean_ext not in {"pdf", "docx"}:
        raise InvalidFileException(message=f"Loại tệp '{file_type}' không hợp lệ.")

    doc_uuid = document_id or uuid.uuid4()
    base_dir = get_resolved_upload_dir(upload_dir)
    safe_filename = f"{doc_uuid}.{clean_ext}"
    target_path = (base_dir / safe_filename).resolve()

    # Đảm bảo đường dẫn đích nằm tuyệt đối bên trong thư mục uploads
    if base_dir not in target_path.parents:
        raise InvalidFileException(
            message="Phát hiện đường dẫn lưu trữ không an toàn (Path Traversal)."
        )

    return doc_uuid, target_path


def save_upload_file_stream(
    file_obj: Union[UploadFile, BinaryIO],
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    max_size_bytes: Optional[int] = None,
    upload_dir: Optional[Path] = None,
) -> SavedUploadResult:
    """
    [SP2-01.1, SP2-01.2, SP2-01.3] Kiểm tra định dạng, đọc tệp theo luồng (stream)
    giới hạn 20MB và lưu xuống ổ cứng bằng tên UUID v4.
    """
    effective_filename = filename or getattr(file_obj, "filename", None)
    effective_content_type = content_type or getattr(file_obj, "content_type", None)

    clean_filename, file_type = validate_extension_and_mime(
        filename=effective_filename,
        content_type=effective_content_type,
    )

    limit_bytes = (
        max_size_bytes
        if max_size_bytes is not None
        else settings.max_file_size_bytes
    )
    max_size_mb = max(1, round(limit_bytes / (1024 * 1024)))

    doc_uuid, target_path = build_safe_storage_path(
        file_type=file_type,
        upload_dir=upload_dir,
    )

    # Lấy luồng nhị phân bên dưới nếu đối tượng là FastAPI UploadFile
    raw_stream: BinaryIO = getattr(file_obj, "file", file_obj)  # type: ignore[assignment]
    if hasattr(raw_stream, "seek"):
        raw_stream.seek(0)

    total_bytes = 0
    try:
        with target_path.open("wb") as out_file:
            while True:
                chunk = raw_stream.read(STREAM_CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > limit_bytes:
                    raise FileTooLargeException(
                        max_size_mb=max_size_mb,
                        details={
                            "filename": clean_filename,
                            "max_size_bytes": limit_bytes,
                        },
                    )
                out_file.write(chunk)

        # Kiểm tra tệp rỗng và chữ ký nhị phân thực tế (%PDF- hoặc cấu trúc DOCX)
        verify_file_signature(target_path, file_type)

    except Exception:
        # Xóa ngay tệp dở dang hoặc không hợp lệ khỏi ổ cứng
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise

    logger.info(
        "Đã lưu tệp hợp lệ xuống đĩa: id=%s, original='%s', path='%s', size=%d bytes",
        doc_uuid,
        clean_filename,
        target_path,
        total_bytes,
    )
    return SavedUploadResult(
        document_id=doc_uuid,
        original_filename=clean_filename,
        storage_path=target_path,
        file_type=file_type,
        file_size=total_bytes,
    )


def validate_and_register_document(
    db: Session,
    upload_file: Union[UploadFile, BinaryIO],
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    max_size_bytes: Optional[int] = None,
    upload_dir: Optional[Path] = None,
) -> Document:
    """
    [SP2-01.4] Kiểm tra tệp tải lên, lưu tệp vật lý <uuid>.<ext> và tạo ngay
    bản ghi ban đầu trong bảng 'documents' với trạng thái 'processing'.
    """
    saved = save_upload_file_stream(
        file_obj=upload_file,
        filename=filename,
        content_type=content_type,
        max_size_bytes=max_size_bytes,
        upload_dir=upload_dir,
    )

    repo = DocumentRepository(db)
    try:
        document = repo.create(
            DocumentCreate(
                id=saved.document_id,
                user_id=user_id,
                filename=saved.original_filename,
                storage_path=str(saved.storage_path),
                file_type=saved.file_type,  # type: ignore[arg-type]
                file_size=saved.file_size,
                status="processing",
            )
        )
        logger.info(
            "Đã tạo bản ghi Document (status='processing') trong CSDL: id=%s",
            document.id,
        )
        return document
    except Exception:
        # Nếu lưu CSDL thất bại, xóa tệp vật lý vừa tạo để đảm bảo tính đồng bộ
        if saved.storage_path.exists():
            saved.storage_path.unlink(missing_ok=True)
        raise

