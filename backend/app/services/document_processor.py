from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

import pymupdf as fitz  # PyMuPDF

from app.core.exceptions import EmptyDocumentException, ExtractionFailedException
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedUnit:
    """
    Đơn vị văn bản trích xuất chuẩn hóa từ tài liệu (1 trang PDF hoặc 1 đoạn/bảng DOCX).
    Hỗ trợ truy cập cả theo thuộc tính (unit.text, unit.page_number) lẫn dạng dict (unit['text']).
    """

    text: str
    document_id: str
    filename: str
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    section_title: Optional[str] = None
    source_type: str = "pdf"

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def open_pdf_safely(pdf_path: Path) -> fitz.Document:
    """
    [SP2-02.1] Mở tệp PDF an toàn bằng PyMuPDF (fitz), bắt ngoại lệ khi tệp
    không tồn tại, hỏng cấu trúc hoặc bị khóa mật khẩu (EXTRACTION_FAILED).
    """
    if not pdf_path.exists() or not pdf_path.is_file():
        raise ExtractionFailedException(
            message=f"Không tìm thấy tệp PDF trên ổ cứng: '{pdf_path.name}'.",
            details={"path": str(pdf_path)},
        )

    try:
        pdf_doc = fitz.open(str(pdf_path))
    except Exception as exc:
        logger.error("Lỗi mở tệp PDF '%s': %s", pdf_path.name, exc)
        raise ExtractionFailedException(
            message="Không thể đọc tệp PDF. Tệp bị hỏng cấu trúc hoặc định dạng không hợp lệ.",
            details={"filename": pdf_path.name, "error": str(exc)},
        ) from exc

    # Kiểm tra tệp PDF có bị đặt mật khẩu bảo vệ hay không
    if pdf_doc.needs_pass or pdf_doc.is_encrypted:
        # Thử xác thực bằng mật khẩu rỗng (trường hợp owner password nhưng cho phép đọc)
        if not pdf_doc.authenticate(""):
            pdf_doc.close()
            logger.warning("Tệp PDF '%s' bị khóa mật khẩu.", pdf_path.name)
            raise ExtractionFailedException(
                message="Tệp PDF đang được bảo vệ bằng mật khẩu, hệ thống không thể trích xuất văn bản.",
                details={"filename": pdf_path.name, "encrypted": True},
            )

    return pdf_doc


def extract_pdf(
    file_path: Union[str, Path],
    document_id: Union[uuid.UUID, str],
    filename: Optional[str] = None,
) -> List[ExtractedUnit]:
    """
    [SP2-02.1 -> SP2-02.4] Trích xuất văn bản từng trang PDF bằng PyMuPDF:
    - Duyệt từng trang bắt đầu từ trang 1 (page_number >= 1).
    - Giữ nguyên thứ tự khối văn bản trên trang (sort=True).
    - Đóng gói kết quả gồm: text, page_number, filename, document_id.
    - Phát hiện PDF rỗng hoặc PDF ảnh scan không có lớp văn bản -> EMPTY_DOCUMENT.
    """
    pdf_path = Path(file_path)
    effective_filename = filename or pdf_path.name
    doc_id_str = str(document_id)

    pdf_doc = open_pdf_safely(pdf_path)

    extracted_pages: List[ExtractedUnit] = []
    total_non_whitespace_chars = 0

    try:
        page_count = len(pdf_doc)
        if page_count == 0:
            raise EmptyDocumentException(
                message="Tệp PDF không chứa trang nào (0 trang).",
                details={"filename": effective_filename, "document_id": doc_id_str},
            )

        for page_number, page in enumerate(pdf_doc, start=1):
            try:
                raw_text = page.get_text("text", sort=True) or ""
            except Exception as exc:
                raise ExtractionFailedException(
                    message=f"Lỗi khi trích xuất văn bản tại trang {page_number} của tệp '{effective_filename}'.",
                    details={
                        "filename": effective_filename,
                        "page_number": page_number,
                        "error": str(exc),
                    },
                ) from exc

            stripped_text = raw_text.strip()
            if stripped_text:
                total_non_whitespace_chars += len(stripped_text)
                extracted_pages.append(
                    ExtractedUnit(
                        text=raw_text,
                        page_number=page_number,
                        filename=effective_filename,
                        document_id=doc_id_str,
                        source_type="pdf",
                    )
                )

    finally:
        pdf_doc.close()

    # [SP2-02.4] Nếu tổng lượng chữ trích xuất được bằng 0 (PDF toàn ảnh scan hoặc trang trắng)
    if total_non_whitespace_chars == 0 or not extracted_pages:
        logger.warning(
            "Tệp PDF '%s' (id=%s) không có lớp văn bản (EMPTY_DOCUMENT).",
            effective_filename,
            doc_id_str,
        )
        raise EmptyDocumentException(
            message=(
                f"Tài liệu PDF '{effective_filename}' chỉ chứa hình ảnh quét (scan) "
                "hoặc không có lớp văn bản để trích xuất."
            ),
            details={
                "filename": effective_filename,
                "document_id": doc_id_str,
                "flag": "EMPTY_DOCUMENT",
            },
        )

    logger.info(
        "Trích xuất PDF thành công: filename='%s', id=%s, pages_with_text=%d, total_chars=%d",
        effective_filename,
        doc_id_str,
        len(extracted_pages),
        total_non_whitespace_chars,
    )
    return extracted_pages

