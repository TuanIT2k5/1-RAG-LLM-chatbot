from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logging import get_logger
from app.services.document_processor import ExtractedUnit
from app.utils.text_cleaner import clean_text, normalize_unicode_nfc

logger = get_logger(__name__)

# Thứ tự ưu tiên dấu ngắt đệ quy chuẩn ([SP2-05.1]):
# Đoạn văn (\n\n) -> Dòng (\n) -> Dấu kết câu (. / ? / ! / ;) -> Khoảng trắng ( ) -> Ký tự ("")
DEFAULT_SEPARATORS: List[str] = ["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]

# Biểu thức tách token từ vựng + dấu câu tiếng Việt / tiếng Anh
TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", flags=re.UNICODE)


def count_tokens(text: str) -> int:
    """Đếm số lượng token (từ và dấu câu) trong đoạn văn bản tiếng Việt / tiếng Anh."""
    if not text or not text.strip():
        return 0
    return len(TOKEN_PATTERN.findall(text))


@dataclass
class TextChunk:
    """
    Đối tượng Chunk văn bản hoàn chỉnh sau khi phân mảnh ([SP2-05.3 & SP2-05.4]),
    chứa nội dung, mã định danh duy nhất (chunk_id), thứ tự (chunk_index) và toàn bộ metadata gốc.
    """

    chunk_id: str
    chunk_index: int
    text: str
    token_count: int
    document_id: str
    filename: str
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    section_title: Optional[str] = None
    source_type: str = "pdf"

    @property
    def metadata(self) -> Dict[str, Any]:
        """Trả về từ điển metadata đầy đủ của Chunk."""
        return {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "paragraph_index": self.paragraph_index,
            "section_title": self.section_title,
            "source_type": self.source_type,
            "token_count": self.token_count,
        }

    def __getitem__(self, key: str) -> Any:
        if key == "metadata":
            return self.metadata
        return getattr(self, key)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["metadata"] = self.metadata
        return data


class RecursiveTextSplitter:
    """
    [SP2-05.1 -> SP2-05.4] Bộ chia nhỏ văn bản đệ quy có độ chồng lấp (overlap)
    giữ nguyên mạch ngữ nghĩa câu/đoạn và kế thừa nguyên vẹn metadata gốc.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separators: Optional[List[str]] = None,
    ) -> None:
        self.chunk_size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
        self.chunk_overlap = (
            chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP
        )
        if self.chunk_size <= 0:
            raise ValueError("chunk_size phải lớn hơn 0.")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) phải >= 0 và nhỏ hơn chunk_size ({self.chunk_size})."
            )
        self.separators = separators or list(DEFAULT_SEPARATORS)

    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """
        Tách chuỗi theo dấu phân cách nhưng giữ lại dấu chấm câu ở cuối câu trước
        để câu văn không bị mất dấu chấm.
        """
        if separator == "":
            return list(text)

        if separator in {". ", "? ", "! ", "; "}:
            punct = separator.strip()
            parts = text.split(separator)
            result: List[str] = []
            for idx, part in enumerate(parts):
                cleaned = part.strip()
                if not cleaned:
                    continue
                if idx < len(parts) - 1:
                    result.append(f"{cleaned}{punct}")
                else:
                    result.append(cleaned)
            return result

        return [part.strip() for part in text.split(separator) if part.strip()]

    def _recursive_break(self, text: str, sep_index: int = 0) -> List[str]:
        """
        [SP2-05.1] Đệ quy chia nhỏ đoạn văn bản lớn thành các mảnh nhỏ hơn hoặc bằng chunk_size
        theo thứ tự ưu tiên dấu ngắt: \n\n -> \n -> . -> khoảng trắng -> ký tự.
        """
        stripped = text.strip()
        if not stripped:
            return []

        if count_tokens(stripped) <= self.chunk_size:
            return [stripped]

        if sep_index >= len(self.separators):
            return [stripped]

        separator = self.separators[sep_index]
        if separator != "" and separator not in stripped:
            return self._recursive_break(stripped, sep_index + 1)

        raw_pieces = self._split_by_separator(stripped, separator)
        if len(raw_pieces) <= 1:
            return self._recursive_break(stripped, sep_index + 1)

        atomic_pieces: List[str] = []
        for piece in raw_pieces:
            if count_tokens(piece) <= self.chunk_size:
                atomic_pieces.append(piece)
            else:
                atomic_pieces.extend(self._recursive_break(piece, sep_index + 1))

        return atomic_pieces

    def _join_pieces(self, pieces: Sequence[str]) -> str:
        """Ghép các mảnh văn bản thành một chuỗi hoàn chỉnh."""
        if not pieces:
            return ""
        return " ".join(p.strip() for p in pieces if p.strip()).strip()

    def split_text(self, text: str) -> List[str]:
        """
        [SP2-05.1 & SP2-05.2] Chia văn bản thành danh sách các chuỗi Chunk
        có kích thước mục tiêu <= chunk_size tokens và độ chồng lấp chunk_overlap tokens.
        """
        if not text or not text.strip():
            return []

        atomic_pieces = self._recursive_break(text.strip(), sep_index=0)
        if not atomic_pieces:
            return []

        chunks: List[str] = []
        current_pieces: List[str] = []
        current_tokens = 0

        for piece in atomic_pieces:
            piece_tokens = count_tokens(piece)
            if piece_tokens == 0:
                continue

            if current_pieces and (current_tokens + piece_tokens > self.chunk_size):
                # Đóng gói Chunk hiện tại
                chunk_str = self._join_pieces(current_pieces)
                if chunk_str:
                    chunks.append(chunk_str)

                # [SP2-05.2] Tạo phần chồng lấp (overlap) từ cuối Chunk vừa đóng gói
                if self.chunk_overlap > 0:
                    overlap_pieces: List[str] = []
                    overlap_tokens = 0
                    for prev_piece in reversed(current_pieces):
                        prev_t = count_tokens(prev_piece)
                        if (
                            overlap_tokens + prev_t <= self.chunk_overlap
                            or not overlap_pieces
                            and prev_t < self.chunk_size
                        ):
                            if overlap_tokens + prev_t <= self.chunk_overlap:
                                overlap_pieces.insert(0, prev_piece)
                                overlap_tokens += prev_t
                            else:
                                # Nếu 1 câu đơn lẻ dài hơn chunk_overlap, lấy đúng số từ cuối của câu đó
                                words = prev_piece.split()
                                tail_words = words[-self.chunk_overlap :]
                                tail_str = " ".join(tail_words)
                                overlap_pieces.insert(0, tail_str)
                                overlap_tokens = count_tokens(tail_str)
                                break
                        else:
                            break

                    # Đảm bảo overlap_pieces + piece mới không vượt quá chunk_size
                    while (
                        overlap_pieces
                        and (overlap_tokens + piece_tokens) > self.chunk_size
                    ):
                        removed = overlap_pieces.pop(0)
                        overlap_tokens -= count_tokens(removed)

                    current_pieces = overlap_pieces
                    current_tokens = sum(count_tokens(p) for p in current_pieces)
                else:
                    current_pieces = []
                    current_tokens = 0

            current_pieces.append(piece)
            current_tokens += piece_tokens

        if current_pieces:
            final_chunk = self._join_pieces(current_pieces)
            if final_chunk and (not chunks or final_chunk != chunks[-1]):
                chunks.append(final_chunk)

        return chunks

    def split_units(
        self,
        units: Sequence[ExtractedUnit],
        clean_before_split: bool = True,
    ) -> List[TextChunk]:
        """
        [SP2-05.3 & SP2-05.4] Chia danh sách ExtractedUnit (từ PDF/DOCX) thành các đối tượng TextChunk,
        đánh số chunk_index tăng dần toàn tài liệu, gán chunk_id duy nhất và kế thừa đầy đủ metadata.
        """
        all_chunks: List[TextChunk] = []
        chunk_index = 0

        for unit in units:
            content = (
                clean_text(unit.text, merge_lines=True)
                if clean_before_split
                else normalize_unicode_nfc(unit.text).strip()
            )
            if not content:
                continue

            # Nếu là DOCX có section_title mà nội dung đoạn chưa bắt đầu bằng section_title,
            # vẫn lưu nguyên section_title trong metadata để truy xuất chính xác
            sub_texts = self.split_text(content)
            for sub_text in sub_texts:
                tokens = count_tokens(sub_text)
                if tokens == 0:
                    continue

                doc_id_str = str(unit.document_id)
                chunk_id = f"{doc_id_str}_chunk_{chunk_index}"

                chunk_obj = TextChunk(
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    text=sub_text,
                    token_count=tokens,
                    document_id=doc_id_str,
                    filename=normalize_unicode_nfc(unit.filename),
                    page_number=unit.page_number,
                    paragraph_index=unit.paragraph_index,
                    section_title=(
                        normalize_unicode_nfc(unit.section_title)
                        if unit.section_title
                        else None
                    ),
                    source_type=unit.source_type,
                )
                all_chunks.append(chunk_obj)
                chunk_index += 1

        logger.info(
            "Đã phân mảnh tài liệu thành %d Chunks (chunk_size=%d, chunk_overlap=%d)",
            len(all_chunks),
            self.chunk_size,
            self.chunk_overlap,
        )
        return all_chunks


def split_extracted_units(
    units: Sequence[ExtractedUnit],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    clean_before_split: bool = True,
) -> List[TextChunk]:
    """Hàm tiện ích khởi tạo RecursiveTextSplitter và cắt danh sách ExtractedUnit."""
    splitter = RecursiveTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_units(units, clean_before_split=clean_before_split)

