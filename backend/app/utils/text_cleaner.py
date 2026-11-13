import re
from typing import List, Sequence
import unicodedata

from app.services.document_processor import ExtractedUnit

# Các ký tự zero-width / vô hình thường gặp trong PDF/DOCX
ZERO_WIDTH_PATTERN = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff\u00ad]")

# Các ký tự điều khiển ASCII/Unicode (trừ \n và \t)
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# [Phần 2 - Bước 2] Biểu thức chính quy nhận diện ký tự hợp lệ (chữ cái Việt/Anh, chữ số và dấu câu chuẩn)
VALID_VIETNAMESE_TEXT_CHAR_PATTERN = re.compile(
    r"[a-zA-Z0-9"
    r"àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    r".,;:!?\(\)\[\]\{\}\-\–\—\/'\"“”‘’%$+=@#&\*_<>|~`^\\]",
    flags=re.IGNORECASE | re.UNICODE,
)

# Mẫu nhận diện các ký tự ngoại lai (Cyrillic, IPA mở rộng, Hy Lạp) xuất hiện khi PDF bị hỏng bảng mã ToUnicode CMap
# Ví dụ điển hình: 'LRK /ЎX RРM 1]750 Pɧ QШX LЖ G WЮ Hо PMЖY UYER LЖ TLФ FMЎR RLϴX'
MOJIBAKE_FOREIGN_GLYPH_PATTERN = re.compile(r"[\u0250-\u02af\u0370-\u052f]")

# Mẫu nhận diện từ bị dịch mã ASCII (chứa dấu ngoặc vuông hoặc số kẹp giữa cụm chữ in hoa như '4]XLSR', '1]750', '[SVPH')
SHIFTED_ASCII_TOKEN_PATTERN = re.compile(r"(?:\b\d\][A-Z0-9]{2,}\b|\[[A-Z]{3,}\b|\b[A-Z]{2,}\][A-Z]{2,}\b)")

MOJIBAKE_DOCUMENT_ERROR_MESSAGE = (
    "Tài liệu bị lỗi mã hóa font chữ. Vui lòng in lại file PDF hoặc sử dụng file khác."
)

MOJIBAKE_CHAT_REFUSAL_MESSAGE = (
    "Xin lỗi, nội dung tài liệu tại đoạn này đang bị lỗi mã hóa chữ nên tôi không thể trích xuất được thông tin."
)

# Mẫu nhận diện dòng chỉ chứa số trang hoặc đường kẻ trang trí vô nghĩa ([SP2-04.4])
STANDALONE_PAGE_NUMBER_PATTERNS = [
    # Số trang đơn thuần: "12", "- 12 -", "— 12 —", "[12]", "(12)"
    re.compile(r"^[\-\–\—\[\(\s]*\d{1,5}[\-\–\—\]\)\s]*$"),
    # "Trang 12", "Trang 12/45", "Trang 12 / 45", "Page 5", "Page 5 of 20"
    re.compile(
        r"^(?:trang|page|tr\.?)\s*\d{1,5}(?:\s*(?:/|of|trên)\s*\d{1,5})?$",
        re.IGNORECASE,
    ),
    # Dòng chỉ toàn dấu gạch ngang, dấu chấm, dấu bằng, dấu sao trang trí
    re.compile(r"^[\-\=\_\.\*\~•\s]{3,}$"),
]

# Mẫu nhận diện đầu mục danh sách, điều khoản hoặc dòng bảng biểu cần giữ ngắt dòng riêng
STRUCTURAL_LINE_START_PATTERN = re.compile(
    r"^(?:"
    r"[\•\-\*\+\▪\➢]\s+"  # Bullet list
    r"|\d{1,3}[\.\)]\s+"  # Numbered list: 1. hoặc 1)
    r"|[a-zđ][\)\.]\s+"  # Lettered list: a) hoặc đ)
    r"|(?:điều|chương|mục|phần|khoản|phụ lục)\s+[\dIVXLCDM]+"  # Cấu trúc văn bản luật/quy chế
    r")",
    re.IGNORECASE,
)


def normalize_unicode_nfc(text: str) -> str:
    """
    [SP2-04.1] Chuẩn hóa bảng mã Unicode tiếng Việt từ dạng tổ hợp (NFD)
    về định dạng dựng sẵn (NFC) để đồng nhất khi tạo vector embedding.
    """
    if not text:
        return ""
    return unicodedata.normalize("NFC", text)


def remove_control_chars_and_normalize_spaces(text: str) -> str:
    """
    [SP2-04.2] Loại bỏ ký tự điều khiển vô hình (null bytes, zero-width),
    thu gọn nhiều khoảng trắng liên tiếp và chuẩn hóa dấu xuống dòng.
    """
    if not text:
        return ""

    # Chuẩn hóa kiểu xuống dòng Windows/Mac về '\n'
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

    # Thay thế khoảng trắng không ngắt dòng (NBSP) bằng khoảng trắng chuẩn và chuẩn hóa gạch nối PDF (\u00ad)
    cleaned = cleaned.replace("\u00a0", " ").replace("\u202f", " ").replace("\u00ad", "-")

    # Xóa ký tự zero-width và ký tự điều khiển
    cleaned = ZERO_WIDTH_PATTERN.sub("", cleaned)
    cleaned = CONTROL_CHARS_PATTERN.sub("", cleaned)

    # Thu gọn nhiều khoảng trắng ngang trên từng dòng
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.split("\n")]
    cleaned = "\n".join(lines)

    # Thu gọn từ 3 dấu xuống dòng liên tiếp trở lên thành tối đa 2 ('\n\n')
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def is_noise_or_page_number_line(line: str) -> bool:
    """
    [SP2-04.4] Kiểm tra xem một dòng văn bản có phải là dòng rỗng,
    chỉ chứa ký tự đánh số trang hoặc đường kẻ phân cách vô nghĩa hay không.
    """
    stripped = line.strip()
    if not stripped:
        return True

    for pattern in STANDALONE_PAGE_NUMBER_PATTERNS:
        if pattern.match(stripped):
            return True

    return False


def filter_meaningless_lines(text: str) -> str:
    """
    [SP2-04.4] Lọc bỏ các dòng chỉ chứa số trang đơn thuần hoặc ký tự trang trí,
    nhưng vẫn giữ nguyên khoảng cách đoạn văn ('\n\n').
    """
    if not text:
        return ""

    filtered_lines: List[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            # Giữ dòng trống để phân tách đoạn văn
            if filtered_lines and filtered_lines[-1] != "":
                filtered_lines.append("")
            continue

        if is_noise_or_page_number_line(stripped):
            continue

        filtered_lines.append(stripped)

    result = "\n".join(filtered_lines)
    return re.sub(r"\n{3,}", "\n\n", result).strip()


def merge_broken_lines(text: str) -> str:
    """
    [SP2-04.3] Nối lại các từ hoặc câu bị ngắt dòng vô lý giữa chừng
    do định dạng cột hoặc lề trang của tệp PDF, đồng thời bảo toàn cấu trúc
    danh sách, tiêu đề điều khoản và bảng biểu.
    """
    if not text:
        return ""

    # 1. Nối từ tiếng Anh/Việt bị gạch nối ngắt dòng ở cuối lề PDF (ví dụ: "chuyên-\nnghiệp")
    joined_hyphen = re.sub(
        r"([A-Za-zÀ-ỹ]+)-\s*\n\s*([a-zà-ỹ]+)",
        r"\1\2",
        text,
    )

    # 2. Xử lý từng đoạn văn (ngăn cách bởi '\n\n')
    paragraphs = joined_hyphen.split("\n\n")
    merged_paragraphs: List[str] = []

    for para in paragraphs:
        lines = [line.strip() for line in para.split("\n") if line.strip()]
        if not lines:
            continue

        current_lines: List[str] = [lines[0]]
        for next_line in lines[1:]:
            prev_line = current_lines[-1]

            # Không nối nếu dòng trước hoặc dòng sau là dòng bảng biểu ('|') hoặc đầu mục cấu trúc
            is_table_row = "|" in prev_line or "|" in next_line
            is_structural_next = bool(STRUCTURAL_LINE_START_PATTERN.match(next_line))
            ends_with_terminal = prev_line.endswith((".", "!", "?", ":", ";", "”", '"'))

            if not is_table_row and not is_structural_next and not ends_with_terminal:
                current_lines[-1] = f"{prev_line} {next_line}"
            else:
                current_lines.append(next_line)

        merged_paragraphs.append("\n".join(current_lines))

    return "\n\n".join(merged_paragraphs).strip()


def clean_text(text: str, merge_lines: bool = True) -> str:
    """
    Hàm tổng hợp làm sạch và chuẩn hóa văn bản tiếng Việt / tiếng Anh
    kết hợp tuần tự [SP2-04.1] -> [SP2-04.2] -> [SP2-04.4] -> [SP2-04.3].
    """
    if not text:
        return ""

    step1_nfc = normalize_unicode_nfc(text)
    step2_ctrl = remove_control_chars_and_normalize_spaces(step1_nfc)
    step3_filtered = filter_meaningless_lines(step2_ctrl)
    if merge_lines:
        step4_merged = merge_broken_lines(step3_filtered)
    else:
        step4_merged = step3_filtered

    return remove_control_chars_and_normalize_spaces(step4_merged)


def is_gibberish(text: str, min_valid_ratio: float = 0.6) -> bool:
    """
    [Phần 2 - Bước 2] Phát hiện văn bản rác hoặc bị lỗi hỏng mã hóa phông chữ (Mojibake / Corrupted CMap):
    1. Loại bỏ toàn bộ khoảng trắng khỏi cả tử số và mẫu số trước khi tính tỷ lệ ký tự hợp lệ
       (khắc phục lỗi lệch mẫu số khi đếm \\s). Nếu tỷ lệ hợp lệ < min_valid_ratio (60%) -> True.
    2. Kiểm tra mật độ ký tự ngoại lai (Cyrillic/IPA/Hy Lạp: Ш, І, К, Ю, Ў, Ж, Р, ɧ, ɺ, ϴ)
       và các cụm từ lệch mã ASCII ('4]XLSR', '1]750', '[SVPH') đặc trưng của PDF lỗi ToUnicode CMap.
    """
    if not text:
        return True

    normalized = normalize_unicode_nfc(text)
    non_whitespace_text = re.sub(r"\s+", "", normalized)
    total_chars = len(non_whitespace_text)
    if total_chars == 0:
        return True

    # 1. Tính tỷ lệ ký tự tiếng Việt, tiếng Anh, chữ số và dấu câu thông dụng
    valid_chars = len(VALID_VIETNAMESE_TEXT_CHAR_PATTERN.findall(non_whitespace_text))
    valid_ratio = valid_chars / total_chars
    if valid_ratio < min_valid_ratio:
        return True

    # 2. Phát hiện lỗi lệch bảng mã ToUnicode CMap (như 'LRK /ЎX RРM 1]750 Pɧ QШX LЖ...')
    foreign_glyph_count = len(MOJIBAKE_FOREIGN_GLYPH_PATTERN.findall(non_whitespace_text))
    if total_chars >= 20 and (foreign_glyph_count / total_chars) >= 0.03:
        return True

    shifted_tokens = SHIFTED_ASCII_TOKEN_PATTERN.findall(normalized)
    if len(shifted_tokens) >= 2:
        return True

    return False


def clean_extracted_units(
    units: Sequence[ExtractedUnit],
    merge_lines: bool = True,
) -> List[ExtractedUnit]:
    """
    Làm sạch danh sách các ExtractedUnit (từ PDF hoặc DOCX) và tự động loại bỏ
    các đơn vị trở nên rỗng sau khi lọc bỏ ký tự rác / số trang đơn lẻ.
    """
    cleaned_units: List[ExtractedUnit] = []
    for unit in units:
        cleaned_content = clean_text(unit.text, merge_lines=merge_lines)
        if not cleaned_content:
            continue

        cleaned_section = (
            clean_text(unit.section_title, merge_lines=False)
            if unit.section_title
            else None
        )
        cleaned_units.append(
            ExtractedUnit(
                text=cleaned_content,
                document_id=unit.document_id,
                filename=normalize_unicode_nfc(unit.filename),
                page_number=unit.page_number,
                paragraph_index=unit.paragraph_index,
                section_title=cleaned_section,
                source_type=unit.source_type,
            )
        )

    return cleaned_units

