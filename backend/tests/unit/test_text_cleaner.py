import unicodedata

from app.services.document_processor import ExtractedUnit
from app.utils.text_cleaner import (
    clean_extracted_units,
    clean_text,
    is_noise_or_page_number_line,
    merge_broken_lines,
    normalize_unicode_nfc,
    remove_control_chars_and_normalize_spaces,
)


def test_normalize_unicode_nfc_vietnamese() -> None:
    """[SP2-04.1] Chuẩn hóa tiếng Việt tổ hợp (NFD) về dựng sẵn (NFC)."""
    nfd_text = unicodedata.normalize("NFD", "Cộng hòa xã hội chủ nghĩa Việt Nam")
    assert not unicodedata.is_normalized("NFC", nfd_text)

    nfc_result = normalize_unicode_nfc(nfd_text)
    assert unicodedata.is_normalized("NFC", nfc_result)
    assert nfc_result == "Cộng hòa xã hội chủ nghĩa Việt Nam"


def test_remove_control_chars_and_collapse_spaces() -> None:
    """[SP2-04.2] Xóa null bytes, ký tự zero-width và thu gọn khoảng trắng/dòng trống."""
    dirty = "Xin\x00   chào\u200b\ufeff   các   bạn\r\n\r\n\r\n\r\nĐoạn   thứ   hai."
    cleaned = remove_control_chars_and_normalize_spaces(dirty)
    assert "\x00" not in cleaned
    assert "\u200b" not in cleaned
    assert cleaned == "Xin chào các bạn\n\nĐoạn thứ hai."


def test_merge_broken_pdf_lines_while_preserving_lists_and_tables() -> None:
    """[SP2-04.3] Nối câu bị ngắt dòng giữa chừng trong PDF nhưng giữ nguyên danh sách và bảng."""
    raw_pdf_text = (
        "Người lao động làm việc đủ 12 tháng\n"
        "cho một người sử dụng lao động thì được\n"
        "nghỉ hằng năm hưởng nguyên lương:\n"
        "• 12 ngày làm việc đối với điều kiện bình thường.\n"
        "• 14 ngày làm việc đối với công việc nặng nhọc."
    )
    merged = merge_broken_lines(raw_pdf_text)
    expected = (
        "Người lao động làm việc đủ 12 tháng cho một người sử dụng lao động thì được "
        "nghỉ hằng năm hưởng nguyên lương:\n"
        "• 12 ngày làm việc đối với điều kiện bình thường.\n"
        "• 14 ngày làm việc đối với công việc nặng nhọc."
    )
    assert merged == expected


def test_filter_standalone_page_numbers_and_empty_units() -> None:
    """[SP2-04.4] Lọc bỏ dòng chỉ chứa số trang đơn thuần và đoạn văn rỗng."""
    assert is_noise_or_page_number_line("45") is True
    assert is_noise_or_page_number_line("- 12 -") is True
    assert is_noise_or_page_number_line("Trang 15 / 120") is True
    assert is_noise_or_page_number_line("Page 3 of 10") is True
    assert is_noise_or_page_number_line("----------------") is True
    assert is_noise_or_page_number_line("Điều 12. Quyền của người lao động") is False

    raw = "Trang 45/120\nNội dung chính của trang 45.\n- 45 -"
    assert clean_text(raw) == "Nội dung chính của trang 45."

    units = [
        ExtractedUnit(
            text="   Trang 1/10   \n  - 1 -  ",
            document_id="doc-1",
            filename="test.pdf",
            page_number=1,
        ),
        ExtractedUnit(
            text="Nội dung thực tế\ncủa trang 2.",
            document_id="doc-1",
            filename="test.pdf",
            page_number=2,
        ),
    ]
    cleaned_units = clean_extracted_units(units)
    assert len(cleaned_units) == 1
    assert cleaned_units[0].page_number == 2
    assert cleaned_units[0].text == "Nội dung thực tế của trang 2."

