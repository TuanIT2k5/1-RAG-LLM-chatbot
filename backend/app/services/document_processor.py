from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

import docx
from docx.document import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
import pymupdf as fitz  # PyMuPDF

from app.core.exceptions import (
    EmptyDocumentException,
    ExtractionFailedException,
    InvalidFileException,
)
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

    # [Phần 2 - Bước 3] Kiểm tra phát hiện văn bản rác / lỗi mã hóa font chữ (Mojibake)
    from app.utils.text_cleaner import MOJIBAKE_DOCUMENT_ERROR_MESSAGE, is_gibberish

    combined_pdf_text = "\n".join(unit.text for unit in extracted_pages)
    if is_gibberish(combined_pdf_text):
        logger.warning(
            "Phát hiện lỗi mã hóa font chữ (Mojibake/Gibberish) trong tệp PDF '%s' (id=%s).",
            effective_filename,
            doc_id_str,
        )
        raise ExtractionFailedException(
            message=MOJIBAKE_DOCUMENT_ERROR_MESSAGE,
            details={
                "filename": effective_filename,
                "document_id": doc_id_str,
                "flag": "GIBBERISH_FONT_ENCODING",
                "error": "Lỗi Font chữ - Không thể đọc tài liệu",
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


def open_docx_safely(docx_path: Path) -> DocxDocument:
    """
    [SP2-03.1] Mở tệp Microsoft Word (.docx) an toàn bằng python-docx,
    bắt ngoại lệ khi tệp bị hỏng cấu trúc hoặc không đọc được (EXTRACTION_FAILED).
    """
    if not docx_path.exists() or not docx_path.is_file():
        raise ExtractionFailedException(
            message=f"Không tìm thấy tệp DOCX trên ổ cứng: '{docx_path.name}'.",
            details={"path": str(docx_path)},
        )

    try:
        return docx.Document(str(docx_path))
    except Exception as exc:
        logger.error("Lỗi mở tệp DOCX '%s': %s", docx_path.name, exc)
        raise ExtractionFailedException(
            message="Không thể đọc tệp DOCX. Tệp bị hỏng cấu trúc hoặc định dạng không hợp lệ.",
            details={"filename": docx_path.name, "error": str(exc)},
        ) from exc


def _is_heading_paragraph(paragraph: Paragraph) -> bool:
    """
    [SP2-03.2] Kiểm tra xem một đoạn văn trong DOCX có phải là dòng tiêu đề
    (Heading 1, Heading 2..., Title, Subtitle) hay không.
    """
    style_name = (paragraph.style.name if paragraph.style else "") or ""
    normalized_style = style_name.strip().lower()
    if normalized_style.startswith(("heading", "title", "subtitle", "tiêu đề")):
        return True

    # Kiểm tra thẻ w:outlineLvl trong XML của đoạn văn (nếu người dùng định dạng outline)
    p_pr = getattr(paragraph._element, "pPr", None)
    if p_pr is not None and getattr(p_pr, "outlineLvl", None) is not None:
        return True

    return False


def _extract_table_text(table: Table) -> str:
    """
    [SP2-03.3] Quét qua các hàng và ô trong bảng biểu (Table) của DOCX,
    khử trùng lặp các ô gộp (merged cells) và ghép thành văn bản có cấu trúc.
    """
    rows_text: List[str] = []
    for row in table.rows:
        seen_tc_ids = set()
        cell_values: List[str] = []
        for cell in row.cells:
            tc_id = id(cell._tc)
            if tc_id in seen_tc_ids:
                continue
            seen_tc_ids.add(tc_id)

            cell_content = " ".join(
                part.strip() for part in cell.text.splitlines() if part.strip()
            )
            if cell_content:
                cell_values.append(cell_content)

        if cell_values:
            rows_text.append(" | ".join(cell_values))

    return "\n".join(rows_text)


def extract_docx(
    file_path: Union[str, Path],
    document_id: Union[uuid.UUID, str],
    filename: Optional[str] = None,
) -> List[ExtractedUnit]:
    """
    [SP2-03.1 -> SP2-03.4] Trích xuất văn bản từng đoạn và bảng biểu từ tệp DOCX:
    - Duyệt tuần tự các đoạn văn (paragraphs) và bảng biểu (tables) theo đúng thứ tự xuất hiện.
    - Nhận diện tiêu đề (Heading 1, Heading 2...) làm thông tin ngữ cảnh mục lục (section_title).
    - Đóng gói từng đơn vị văn bản kèm: document_id, filename, paragraph_index (từ 1) và section_title.
    """
    docx_path = Path(file_path)
    effective_filename = filename or docx_path.name
    doc_id_str = str(document_id)

    word_doc = open_docx_safely(docx_path)

    extracted_units: List[ExtractedUnit] = []
    current_section_title: Optional[str] = None
    paragraph_index = 0
    total_non_whitespace_chars = 0

    # Duyệt theo đúng thứ tự xuất hiện của đoạn văn và bảng biểu trong thân tài liệu
    if hasattr(word_doc, "iter_inner_content"):
        blocks = list(word_doc.iter_inner_content())
    else:
        blocks = list(word_doc.paragraphs) + list(word_doc.tables)

    for block in blocks:
        if isinstance(block, Paragraph):
            raw_text = (block.text or "").strip()
            if not raw_text:
                continue

            if _is_heading_paragraph(block):
                current_section_title = raw_text

            paragraph_index += 1
            total_non_whitespace_chars += len(raw_text)
            extracted_units.append(
                ExtractedUnit(
                    text=raw_text,
                    document_id=doc_id_str,
                    filename=effective_filename,
                    page_number=None,
                    paragraph_index=paragraph_index,
                    section_title=current_section_title,
                    source_type="docx",
                )
            )
        elif isinstance(block, Table):
            table_text = _extract_table_text(block).strip()
            if not table_text:
                continue

            paragraph_index += 1
            total_non_whitespace_chars += len(table_text)
            extracted_units.append(
                ExtractedUnit(
                    text=table_text,
                    document_id=doc_id_str,
                    filename=effective_filename,
                    page_number=None,
                    paragraph_index=paragraph_index,
                    section_title=current_section_title,
                    source_type="docx",
                )
            )

    if total_non_whitespace_chars == 0 or not extracted_units:
        logger.warning(
            "Tệp DOCX '%s' (id=%s) không có nội dung văn bản (EMPTY_DOCUMENT).",
            effective_filename,
            doc_id_str,
        )
        raise EmptyDocumentException(
            message=f"Tài liệu Word '{effective_filename}' rỗng hoặc không chứa nội dung văn bản.",
            details={
                "filename": effective_filename,
                "document_id": doc_id_str,
                "flag": "EMPTY_DOCUMENT",
            },
        )

    logger.info(
        "Trích xuất DOCX thành công: filename='%s', id=%s, units=%d, total_chars=%d",
        effective_filename,
        doc_id_str,
        len(extracted_units),
        total_non_whitespace_chars,
    )
    return extracted_units


def extract_document(
    file_path: Union[str, Path],
    document_id: Union[uuid.UUID, str],
    filename: Optional[str] = None,
) -> List[ExtractedUnit]:
    """Hàm điều phối tự động chọn bộ trích xuất PDF hoặc DOCX theo phần mở rộng tệp."""
    path_obj = Path(file_path)
    ext = path_obj.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(file_path=path_obj, document_id=document_id, filename=filename)
    if ext == ".docx":
        return extract_docx(file_path=path_obj, document_id=document_id, filename=filename)
    raise InvalidFileException(
        message=f"Không hỗ trợ trích xuất định dạng tệp '{ext}'. Chỉ hỗ trợ .pdf và .docx."
    )
