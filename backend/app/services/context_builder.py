from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Union
import uuid

from app.core.logging import get_logger
from app.schemas.chat_schema import SourceCitation
from app.services.retriever import RetrievedChunk
from app.services.text_splitter import count_tokens as estimate_tokens
from app.utils.text_cleaner import normalize_unicode_nfc

logger = get_logger(__name__)

DEFAULT_MAX_CONTEXT_TOKENS = 3000
MIN_USEFUL_CHUNK_TOKENS = 35
BLOCK_SEPARATOR = "\n\n---\n\n"


@dataclass
class SourceMapEntry:
    """
    [SP4-01.3] Đối tượng lưu trữ toàn bộ metadata thật của một Chunk gắn với mã nguồn 'S1', 'S2'...
    trong bảng ánh xạ tạm thời (source_map) tại Backend để phục vụ đối chiếu trích dẫn hai lớp.
    """

    source_id: str  # Ví dụ: "S1", "S2"
    label: str  # Ví dụ: "[S1]", "[S2]"
    chunk_id: str
    document_id: str
    filename: str
    excerpt: str
    score: Optional[float] = None
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    section_title: Optional[str] = None
    chunk_index: Optional[int] = None
    source_type: str = "pdf"

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_source_citation(self) -> SourceCitation:
        """
        Chuyển đổi trực tiếp sang Pydantic schema SourceCitation để trả về cho Frontend
        sau khi mô-đun citation_service xác thực mã [Sx].
        """
        doc_uuid = (
            uuid.UUID(str(self.document_id))
            if not isinstance(self.document_id, uuid.UUID)
            else self.document_id
        )
        valid_page = (
            int(self.page_number)
            if (self.page_number is not None and int(self.page_number) >= 1)
            else None
        )
        valid_chunk_idx = (
            int(self.chunk_index)
            if (self.chunk_index is not None and int(self.chunk_index) >= 0)
            else None
        )
        return SourceCitation(
            source_id=self.source_id,
            document_id=doc_uuid,
            filename=self.filename,
            page_number=valid_page,
            chunk_index=valid_chunk_idx,
            chunk_id=self.chunk_id or None,
            excerpt=self.excerpt,
            score=self.score,
        )


@dataclass
class BuiltContext:
    """
    Kết quả đầu ra của ContextBuilder ([SP4-01.1 -> SP4-01.4]):
    - context_text: Chuỗi ngữ cảnh hoàn chỉnh đã gắn nhãn [S1], [S2]... để đưa vào LLM Prompt.
    - source_map: Bảng ánh xạ từ mã 'S1', 'S2'... sang SourceMapEntry chứa toàn bộ metadata thật.
    - formatted_blocks: Danh sách từng khối ngữ cảnh [Sx] riêng lẻ.
    - total_tokens: Tổng số lượng token ước tính của context_text.
    - total_chars: Tổng số ký tự của context_text.
    - included_count: Số lượng đoạn văn đã đưa vào ngữ cảnh.
    - omitted_count: Số lượng đoạn văn bị lược bỏ do vượt giới hạn Context Window.
    """

    context_text: str
    source_map: Dict[str, SourceMapEntry] = field(default_factory=dict)
    formatted_blocks: List[str] = field(default_factory=list)
    total_tokens: int = 0
    total_chars: int = 0
    included_count: int = 0
    omitted_count: int = 0

    def __iter__(self) -> Iterator[Any]:
        """Hỗ trợ giải nén bộ đôi: context_text, source_map = builder.build(chunks)."""
        yield self.context_text
        yield self.source_map


def format_location_label(
    page_number: Optional[int] = None,
    paragraph_index: Optional[int] = None,
    section_title: Optional[str] = None,
    chunk_index: Optional[int] = None,
) -> str:
    """
    [SP4-01.2] Định dạng chuỗi hiển thị vị trí nguồn (Số trang PDF hoặc Vị trí đoạn/Mục DOCX).
    """
    parts: List[str] = []

    if page_number is not None and int(page_number) >= 1:
        parts.append(f"Trang {int(page_number)}")

    if section_title:
        clean_sec = str(section_title).strip()
        if clean_sec:
            parts.append(f"Mục: {clean_sec}")

    if paragraph_index is not None and int(paragraph_index) >= 0:
        parts.append(f"Đoạn #{int(paragraph_index)}")
    elif chunk_index is not None and int(chunk_index) >= 0:
        parts.append(f"Đoạn #{int(chunk_index)}")

    return " | ".join(parts) if parts else "Không rõ vị trí"


def format_context_block(
    source_id: str,
    filename: str,
    text: str,
    page_number: Optional[int] = None,
    paragraph_index: Optional[int] = None,
    section_title: Optional[str] = None,
    chunk_index: Optional[int] = None,
) -> str:
    """
    [SP4-01.2] Định dạng một khối ngữ cảnh chuẩn gồm:
    Mã nguồn [Sx], Tên tài liệu, Số trang/Vị trí đoạn và Nội dung văn bản.
    """
    clean_source_id = source_id.strip().lstrip("[").rstrip("]")
    location_str = format_location_label(
        page_number=page_number,
        paragraph_index=paragraph_index,
        section_title=section_title,
        chunk_index=chunk_index,
    )
    clean_filename = (filename or "unknown").strip()
    clean_text = normalize_unicode_nfc(text or "").strip()

    return (
        f"[{clean_source_id}] Tài liệu: {clean_filename} | Vị trí: {location_str}\n"
        f"Nội dung:\n{clean_text}"
    )


def _truncate_text_to_token_budget(
    text: str,
    max_tokens: int,
    max_chars: Optional[int] = None,
) -> str:
    """
    Cắt gọn văn bản theo ranh giới từ sao cho không vượt quá ngân sách token và ký tự,
    kèm dấu '...' ở cuối.
    """
    cleaned = normalize_unicode_nfc(text or "").strip()
    if not cleaned or max_tokens <= 0:
        return ""

    if max_chars is not None and max_chars > 3 and len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 3].rsplit(" ", 1)[0].strip() + "..."

    if estimate_tokens(cleaned) <= max_tokens:
        return cleaned

    words = cleaned.split()
    if not words:
        return ""

    # Ước lượng số từ tối đa dựa trên tỷ lệ ~1.35 token / từ tiếng Việt
    approx_word_limit = max(1, int((max_tokens - 2) / 1.35))
    candidate_words = words[:approx_word_limit]

    while candidate_words and estimate_tokens(" ".join(candidate_words) + "...") > max_tokens:
        candidate_words.pop()

    if not candidate_words:
        return ""

    result = " ".join(candidate_words).rstrip(".,;:- ") + "..."
    if max_chars is not None and len(result) > max_chars:
        result = result[: max(1, max_chars - 3)].rstrip() + "..."
    return result


def _extract_chunk_fields(
    chunk: Union[RetrievedChunk, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Chuẩn hóa dữ liệu đầu vào từ RetrievedChunk hoặc dict bất kỳ."""
    if isinstance(chunk, RetrievedChunk):
        return {
            "chunk_id": str(chunk.chunk_id or ""),
            "text": str(chunk.text or ""),
            "document_id": str(chunk.document_id or ""),
            "filename": str(chunk.filename or "unknown"),
            "score": float(chunk.similarity_score),
            "page_number": chunk.page_number,
            "paragraph_index": chunk.paragraph_index,
            "section_title": chunk.section_title,
            "chunk_index": chunk.chunk_index,
            "source_type": str(chunk.source_type or "pdf"),
        }

    meta = chunk.get("metadata") if isinstance(chunk.get("metadata"), Mapping) else {}
    score_val = chunk.get("similarity_score", chunk.get("score"))
    return {
        "chunk_id": str(chunk.get("chunk_id") or meta.get("chunk_id") or ""),
        "text": str(chunk.get("text") or chunk.get("excerpt") or ""),
        "document_id": str(chunk.get("document_id") or meta.get("document_id") or ""),
        "filename": str(chunk.get("filename") or meta.get("filename") or "unknown"),
        "score": float(score_val) if score_val is not None else None,
        "page_number": (
            chunk.get("page_number")
            if chunk.get("page_number") is not None
            else meta.get("page_number")
        ),
        "paragraph_index": (
            chunk.get("paragraph_index")
            if chunk.get("paragraph_index") is not None
            else meta.get("paragraph_index")
        ),
        "section_title": (
            chunk.get("section_title")
            if chunk.get("section_title") is not None
            else meta.get("section_title")
        ),
        "chunk_index": (
            chunk.get("chunk_index")
            if chunk.get("chunk_index") is not None
            else meta.get("chunk_index")
        ),
        "source_type": str(
            chunk.get("source_type") or meta.get("source_type") or "pdf"
        ),
    }


class ContextBuilder:
    """
    [SP4-01.1 -> SP4-01.4] Bộ ghép nối ngữ cảnh từ danh sách Top-K đoạn văn truy xuất được,
    gán mã định danh nguồn tạm thời [S1], [S2]... và tạo bảng ánh xạ source_map phục vụ
    đối chiếu trích dẫn hai lớp chống ảo giác.
    """

    def __init__(
        self,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
        max_context_chars: Optional[int] = None,
        block_separator: str = BLOCK_SEPARATOR,
    ) -> None:
        if max_context_tokens <= 0:
            raise ValueError("max_context_tokens phải lớn hơn 0.")
        if max_context_chars is not None and max_context_chars <= 0:
            raise ValueError("max_context_chars phải lớn hơn 0 nếu được cấu hình.")

        self.max_context_tokens = max_context_tokens
        self.max_context_chars = max_context_chars
        self.block_separator = block_separator

    def build(
        self,
        chunks: Sequence[Union[RetrievedChunk, Mapping[str, Any]]],
        max_context_tokens: Optional[int] = None,
        max_context_chars: Optional[int] = None,
    ) -> BuiltContext:
        """
        [SP4-01.1 -> SP4-01.4] Duyệt qua danh sách Top-K đoạn văn:
        1. Gán nhãn tuần tự [S1], [S2], [S3]... cho từng đoạn hợp lệ.
        2. Định dạng từng khối gồm [Sx], Tên tài liệu, Số trang/Vị trí đoạn và Nội dung.
        3. Lưu bảng ánh xạ source_map['S1'] -> SourceMapEntry chứa toàn bộ metadata thật.
        4. Kiểm soát tổng độ dài chuỗi Context không vượt quá giới hạn Context Window.
        """
        token_limit = (
            max_context_tokens
            if max_context_tokens is not None
            else self.max_context_tokens
        )
        char_limit = (
            max_context_chars
            if max_context_chars is not None
            else self.max_context_chars
        )
        if token_limit <= 0:
            raise ValueError("Giới hạn max_context_tokens phải lớn hơn 0.")

        if not chunks:
            return BuiltContext(
                context_text="",
                source_map={},
                formatted_blocks=[],
                total_tokens=0,
                total_chars=0,
                included_count=0,
                omitted_count=0,
            )

        source_map: Dict[str, SourceMapEntry] = {}
        formatted_blocks: List[str] = []
        sep_tokens = estimate_tokens(self.block_separator)
        sep_chars = len(self.block_separator)
        used_tokens = 0
        used_chars = 0
        omitted_count = 0
        next_source_number = 1

        for raw_chunk in chunks:
            fields = _extract_chunk_fields(raw_chunk)
            raw_text = normalize_unicode_nfc(fields["text"]).strip()
            if not raw_text:
                continue

            source_id = f"S{next_source_number}"
            label = f"[{source_id}]"

            # Tạo khối ngữ cảnh đầy đủ cho đoạn văn hiện tại
            candidate_block = format_context_block(
                source_id=source_id,
                filename=fields["filename"],
                text=raw_text,
                page_number=fields["page_number"],
                paragraph_index=fields["paragraph_index"],
                section_title=fields["section_title"],
                chunk_index=fields["chunk_index"],
            )
            block_tokens = estimate_tokens(candidate_block)
            block_chars = len(candidate_block)

            extra_sep_tokens = sep_tokens if formatted_blocks else 0
            extra_sep_chars = sep_chars if formatted_blocks else 0

            fits_tokens = (used_tokens + extra_sep_tokens + block_tokens) <= token_limit
            fits_chars = (
                True
                if char_limit is None
                else (used_chars + extra_sep_chars + block_chars) <= char_limit
            )

            final_excerpt = raw_text
            final_block = candidate_block

            if not (fits_tokens and fits_chars):
                # [SP4-01.4] Kiểm tra ngân sách còn lại để quyết định cắt gọn hay dừng nạp thêm
                header_only = format_context_block(
                    source_id=source_id,
                    filename=fields["filename"],
                    text="",
                    page_number=fields["page_number"],
                    paragraph_index=fields["paragraph_index"],
                    section_title=fields["section_title"],
                    chunk_index=fields["chunk_index"],
                )
                header_tokens = estimate_tokens(header_only)
                header_chars = len(header_only)

                remaining_tokens = token_limit - used_tokens - extra_sep_tokens - header_tokens
                remaining_chars = (
                    (char_limit - used_chars - extra_sep_chars - header_chars)
                    if char_limit is not None
                    else None
                )

                # Cho phép cắt gọn nếu là đoạn đầu tiên (S1) hoặc ngân sách còn đủ >= MIN_USEFUL_CHUNK_TOKENS
                can_truncate = (
                    len(formatted_blocks) == 0 and remaining_tokens >= 5
                ) or (remaining_tokens >= MIN_USEFUL_CHUNK_TOKENS)

                if can_truncate and (remaining_chars is None or remaining_chars >= 20):
                    truncated_text = _truncate_text_to_token_budget(
                        raw_text,
                        max_tokens=max(1, remaining_tokens),
                        max_chars=remaining_chars,
                    )
                    if truncated_text:
                        final_excerpt = truncated_text
                        final_block = format_context_block(
                            source_id=source_id,
                            filename=fields["filename"],
                            text=final_excerpt,
                            page_number=fields["page_number"],
                            paragraph_index=fields["paragraph_index"],
                            section_title=fields["section_title"],
                            chunk_index=fields["chunk_index"],
                        )
                    else:
                        omitted_count += 1
                        continue
                else:
                    omitted_count += 1
                    continue

            # Ghi nhận khối ngữ cảnh và lưu vào bảng ánh xạ source_map ([SP4-01.1 & SP4-01.3])
            formatted_blocks.append(final_block)
            used_tokens += (extra_sep_tokens + estimate_tokens(final_block))
            used_chars += (extra_sep_chars + len(final_block))

            source_map[source_id] = SourceMapEntry(
                source_id=source_id,
                label=label,
                chunk_id=fields["chunk_id"],
                document_id=fields["document_id"],
                filename=fields["filename"],
                excerpt=final_excerpt,
                score=fields["score"],
                page_number=fields["page_number"],
                paragraph_index=fields["paragraph_index"],
                section_title=fields["section_title"],
                chunk_index=fields["chunk_index"],
                source_type=fields["source_type"],
            )
            next_source_number += 1

        context_text = self.block_separator.join(formatted_blocks)
        total_tokens = estimate_tokens(context_text) if context_text else 0
        total_chars = len(context_text)

        logger.info(
            "Đã đóng gói Context gồm %d/%d đoạn văn (tokens=%d/%d, chars=%d, omitted=%d).",
            len(formatted_blocks),
            len(chunks),
            total_tokens,
            token_limit,
            total_chars,
            omitted_count,
        )

        return BuiltContext(
            context_text=context_text,
            source_map=source_map,
            formatted_blocks=formatted_blocks,
            total_tokens=total_tokens,
            total_chars=total_chars,
            included_count=len(formatted_blocks),
            omitted_count=omitted_count,
        )


def build_context(
    chunks: Sequence[Union[RetrievedChunk, Mapping[str, Any]]],
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    max_context_chars: Optional[int] = None,
) -> BuiltContext:
    """
    Hàm tiện ích cấp mô-đun để ghép nối ngữ cảnh và tạo bảng ánh xạ source_map
    từ danh sách các đoạn văn truy xuất được.
    """
    builder = ContextBuilder(
        max_context_tokens=max_context_tokens,
        max_context_chars=max_context_chars,
    )
    return builder.build(chunks)
