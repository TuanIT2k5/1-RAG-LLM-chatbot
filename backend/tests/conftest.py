from pathlib import Path
from typing import Dict

import docx
import pymupdf as fitz
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _get_unicode_font_path() -> str | None:
    """Tìm font Unicode hỗ trợ đầy đủ tiếng Việt trên hệ thống (Arial / Segoe UI / Times)."""
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/times.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def generate_sample_25page_vietnamese_pdf(target_path: Path) -> Path:
    """
    [SP2-06.1 & Sprint 2 DoD] Tạo tệp PDF tiếng Việt 25 trang (trên 20 trang),
    mỗi trang chứa các điều khoản cụ thể để đối chiếu chính xác số trang (page_number).
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_doc = fitz.open()
    font_file = _get_unicode_font_path()

    for page_num in range(1, 26):
        page = pdf_doc.new_page(width=595, height=842)
        paragraphs = [
            f"BỘ LUẬT LAO ĐỘNG - TRANG SỐ {page_num}",
            f"Điều {page_num}. Quy định chi tiết tại trang {page_num} về quyền và nghĩa vụ của người lao động.",
            (
                f"Khoản 1 Điều {page_num}: Người lao động làm việc tại trang {page_num} được đảm bảo "
                "đầy đủ chế độ lương, thưởng, bảo hiểm xã hội và thời giờ nghỉ ngơi theo quy định."
            ),
            (
                f"Khoản 2 Điều {page_num}: Mọi tranh chấp phát sinh liên quan đến nội dung ở trang {page_num} "
                "sẽ được giải quyết trên nguyên tắc thương lượng, hòa giải và tuân thủ pháp luật Việt Nam."
            ),
            f"- {page_num} -",  # Dòng đánh số trang đơn lẻ ở cuối trang để kiểm tra bộ lọc text_cleaner
        ]
        full_page_text = "\n\n".join(paragraphs)

        if font_file:
            page.insert_textbox(
                fitz.Rect(50, 50, 545, 790),
                full_page_text,
                fontsize=11,
                fontname="vi_font",
                fontfile=font_file,
            )
        else:
            page.insert_htmlbox(
                fitz.Rect(50, 50, 545, 790),
                f"<div style='font-family: sans-serif; font-size: 11pt;'>{full_page_text.replace(chr(10), '<br/>')}</div>",
            )

    pdf_doc.save(str(target_path))
    pdf_doc.close()
    return target_path


def generate_sample_vietnamese_docx(target_path: Path) -> Path:
    """
    [SP2-06.1 & Sprint 2 DoD] Tạo tệp DOCX tiếng Việt có đầy đủ Heading 1, Heading 2,
    các đoạn văn bản dài và bảng biểu (Table) dữ liệu.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    word_doc = docx.Document()

    word_doc.add_heading("Chương 1: Quy định chung về Quản lý Nhân sự", level=1)
    word_doc.add_paragraph(
        "Nội quy lao động này quy định về thời giờ làm việc, thời giờ nghỉ ngơi, "
        "trật tự tại nơi làm việc và bảo vệ tài sản trí tuệ của doanh nghiệp."
    )
    word_doc.add_paragraph(
        "Mọi cán bộ nhân viên chính thức và thử việc đều có trách nhiệm tuân thủ nghiêm "
        "các điều khoản được ban hành trong văn bản này."
    )

    word_doc.add_heading("Mục 1.1: Bảng tiêu chuẩn ngày nghỉ phép hằng năm", level=2)
    table = word_doc.add_table(rows=4, cols=3)
    headers = ["Nhóm đối tượng", "Điều kiện làm việc", "Số ngày phép/năm"]
    for col_idx, text in enumerate(headers):
        table.cell(0, col_idx).text = text

    rows_data = [
        ["Nhân viên văn phòng", "Điều kiện bình thường", "12 ngày làm việc"],
        ["Kỹ sư vận hành máy", "Nặng nhọc, độc hại", "14 ngày làm việc"],
        ["Chuyên gia đặc biệt", "Đặc biệt nặng nhọc", "16 ngày làm việc"],
    ]
    for row_idx, row_values in enumerate(rows_data, start=1):
        for col_idx, val in enumerate(row_values):
            table.cell(row_idx, col_idx).text = val

    word_doc.add_heading("Chương 2: Quy trình đăng ký nghỉ phép", level=1)
    word_doc.add_paragraph(
        "Người lao động cần gửi đơn xin nghỉ phép trên hệ thống nội bộ trước ít nhất 03 ngày làm việc "
        "để quản lý trực tiếp phê duyệt và sắp xếp nhân sự thay thế."
    )

    word_doc.save(str(target_path))
    return target_path


def generate_sample_empty_scanned_pdf(target_path: Path) -> Path:
    """[SP2-06.1] Tạo tệp PDF 3 trang trắng/ảnh scan không có lớp văn bản."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_doc = fitz.open()
    for _ in range(3):
        page = pdf_doc.new_page()
        # Chỉ vẽ hình chữ nhật đồ họa, không chèn bất kỳ ký tự văn bản nào
        shape = page.new_shape()
        shape.draw_rect(fitz.Rect(100, 100, 300, 300))
        shape.finish(color=(0.2, 0.4, 0.8), fill=(0.9, 0.9, 0.95))
        shape.commit()
    pdf_doc.save(str(target_path))
    pdf_doc.close()
    return target_path


def generate_sample_invalid_format_file(target_path: Path) -> Path:
    """[SP2-06.1] Tạo tệp thực thi giả mạo (.exe) nhưng đổi đuôi thành .pdf."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(
        b"MZ\x90\x00\x03\x00\x00\x00Fake Windows Executable disguised as PDF"
    )
    return target_path


@pytest.fixture(scope="session")
def sample_files() -> Dict[str, Path]:
    """
    Fixture khởi tạo bộ 4 tệp mẫu kiểm thử chuẩn trong backend/tests/fixtures/
    phục vụ [SP2-06.1 -> SP2-06.4] và nghiệm thu Sprint 2.
    Chỉ tạo lại tệp nếu tệp chưa tồn tại trên đĩa để tránh làm bẩn git status.
    """
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    pdf_25_path = FIXTURES_DIR / "sample_vietnamese_25pages.pdf"
    if not pdf_25_path.exists():
        generate_sample_25page_vietnamese_pdf(pdf_25_path)

    docx_path = FIXTURES_DIR / "sample_vietnamese_headings_tables.docx"
    if not docx_path.exists():
        generate_sample_vietnamese_docx(docx_path)

    empty_pdf_path = FIXTURES_DIR / "sample_empty_scanned.pdf"
    if not empty_pdf_path.exists():
        generate_sample_empty_scanned_pdf(empty_pdf_path)

    invalid_file_path = FIXTURES_DIR / "sample_invalid_spoofed.pdf"
    if not invalid_file_path.exists():
        generate_sample_invalid_format_file(invalid_file_path)

    return {
        "pdf_25_pages": pdf_25_path,
        "docx_with_table": docx_path,
        "empty_pdf": empty_pdf_path,
        "invalid_file": invalid_file_path,
    }

