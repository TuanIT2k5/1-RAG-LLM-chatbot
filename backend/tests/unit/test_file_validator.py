import io
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import (
    EmptyDocumentException,
    FileTooLargeException,
    InvalidFileException,
)
from app.database.connection import Base
from app.utils.file_validator import (
    save_upload_file_stream,
    validate_and_register_document,
    validate_extension_and_mime,
)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"


def create_minimal_docx_bytes() -> bytes:
    """Tạo gói nhị phân .docx hợp lệ tối thiểu trong bộ nhớ."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Xin chào</w:t></w:r></w:p></w:body></w:document>',
        )
    return buffer.getvalue()


def test_validate_extension_and_mime_success() -> None:
    """[SP2-01.1] Kiểm tra chấp nhận đúng đuôi .pdf/.docx và MIME type hợp lệ."""
    name_pdf, ext_pdf = validate_extension_and_mime("Tai_lieu.PDF", PDF_MIME)
    assert name_pdf == "Tai_lieu.PDF"
    assert ext_pdf == "pdf"

    name_docx, ext_docx = validate_extension_and_mime("Bao_cao.docx", DOCX_MIME)
    assert name_docx == "Bao_cao.docx"
    assert ext_docx == "docx"


def test_validate_extension_and_mime_rejects_invalid_types() -> None:
    """[SP2-01.1] Từ chối phần mở rộng lạ hoặc MIME type không khớp."""
    with pytest.raises(InvalidFileException) as exc_ext:
        validate_extension_and_mime("malware.exe", "application/octet-stream")
    assert exc_ext.value.error_code == "INVALID_FILE"
    assert exc_ext.value.status_code == 400

    with pytest.raises(InvalidFileException) as exc_mime:
        validate_extension_and_mime("gia_mao.pdf", "application/x-msdownload")
    assert exc_mime.value.error_code == "INVALID_FILE"


def test_rejects_spoofed_exe_renamed_to_pdf(tmp_path: Path) -> None:
    """[TC-03] Chặn tệp .exe giả mạo đổi đuôi thành .pdf dù gửi kèm MIME application/pdf."""
    fake_pdf_stream = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00This is an EXE file")
    with pytest.raises(InvalidFileException) as exc_info:
        save_upload_file_stream(
            file_obj=fake_pdf_stream,
            filename="virus_doi_duoi.pdf",
            content_type=PDF_MIME,
            upload_dir=tmp_path,
        )
    assert exc_info.value.error_code == "INVALID_FILE"
    assert list(tmp_path.glob("*")) == []


def test_stream_size_limit_rejects_over_20mb(tmp_path: Path) -> None:
    """[SP2-01.2 & TC-04] Từ chối ngay lập tức tệp vượt quá giới hạn dung lượng (413 FILE_TOO_LARGE)."""
    # Đặt ngưỡng kiểm thử nhỏ (1MB) và truyền luồng 1.5MB
    limit_1mb = 1 * 1024 * 1024
    oversized_stream = io.BytesIO(b"%PDF-1.7\n" + (b"A" * int(1.5 * 1024 * 1024)))

    with pytest.raises(FileTooLargeException) as exc_info:
        save_upload_file_stream(
            file_obj=oversized_stream,
            filename="tai_lieu_nang.pdf",
            content_type=PDF_MIME,
            max_size_bytes=limit_1mb,
            upload_dir=tmp_path,
        )
    assert exc_info.value.error_code == "FILE_TOO_LARGE"
    assert exc_info.value.status_code == 413
    # Đảm bảo tệp dở dang đã bị xóa sạch khỏi ổ cứng
    assert list(tmp_path.glob("*")) == []


def test_empty_zero_byte_file_rejected(tmp_path: Path) -> None:
    """Từ chối tệp rỗng 0 byte."""
    with pytest.raises(EmptyDocumentException):
        save_upload_file_stream(
            file_obj=io.BytesIO(b""),
            filename="empty.pdf",
            content_type=PDF_MIME,
            upload_dir=tmp_path,
        )
    assert list(tmp_path.glob("*")) == []


def test_uuid_filename_and_db_registration_processing(tmp_path: Path) -> None:
    """[SP2-01.3 & SP2-01.4] Chống Path Traversal, lưu tên UUID v4 và tạo bản ghi 'processing' trong DB."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    docx_bytes = create_minimal_docx_bytes()
    with TestingSession() as db:
        doc = validate_and_register_document(
            db=db,
            upload_file=io.BytesIO(docx_bytes),
            filename="../../etc/passwd/Noi_quy_2026.docx",
            content_type=DOCX_MIME,
            upload_dir=tmp_path,
        )

        # Kiểm tra bản ghi trong bảng 'documents'
        assert doc.status == "processing"
        assert doc.filename == "Noi_quy_2026.docx"
        assert doc.file_type == "docx"
        assert doc.file_size == len(docx_bytes)

        # Kiểm tra tệp trên ổ cứng được đặt tên bằng đúng UUID v4
        saved_path = Path(doc.storage_path)
        assert saved_path.exists()
        assert saved_path.parent == tmp_path.resolve()
        assert saved_path.name == f"{doc.id}.docx"

