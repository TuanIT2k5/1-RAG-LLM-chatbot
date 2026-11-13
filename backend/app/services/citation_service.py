from dataclasses import dataclass, field
import re
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Union
import uuid

from app.core.logging import get_logger
from app.schemas.chat_schema import SourceCitation
from app.services.context_builder import SourceMapEntry
from app.services.llm_service import NO_CONTEXT_REFUSAL_MESSAGE, clean_robotic_phrases
from app.utils.text_cleaner import normalize_unicode_nfc

logger = get_logger(__name__)

# [SP4-03.1] Biểu thức chính quy nhận diện các thẻ trích dẫn trong ngoặc vuông:
# Hỗ trợ cả dạng đơn [S1], [S2] lẫn dạng gộp [S1, S2], [S1; S3], [Nguồn S1]
BRACKET_CITATION_GROUP_PATTERN = re.compile(
    r"\[\s*(?:nguồn\s*)?(S\d+(?:\s*[,;/]\s*S\d+)*)\s*\]",
    flags=re.IGNORECASE | re.UNICODE,
)
SINGLE_SOURCE_ID_PATTERN = re.compile(r"S\d+", flags=re.IGNORECASE)

# Các cụm từ nhận diện câu trả lời từ chối khi tài liệu không có thông tin
REFUSAL_PHRASES = (
    "không tìm thấy thông tin liên quan trong các tài liệu hiện có",
    "tài liệu hiện có không đề cập",
    "không đủ thông tin trong ngữ cảnh",
)


@dataclass
class VerifiedCitationResult:
    """
    Kết quả xác thực trích dẫn hai lớp từ CitationService ([SP4-03.1 -> SP4-03.4]):
    - answer: Câu trả lời đã được làm sạch các thẻ [Sx] không hợp lệ (nếu LLM bịa mã).
    - sources: Danh sách đối tượng SourceCitation chứa metadata thật từ Backend.
    - valid_source_ids: Danh sách mã nguồn hợp lệ đã đối chiếu thành công (ví dụ ['S1', 'S3']).
    - removed_source_ids: Danh sách mã nguồn ảo giác đã bị loại bỏ (ví dụ ['S99']).
    - skipped_llm: Cờ đánh dấu trường hợp không có ngữ cảnh phù hợp nên không tốn lượt gọi LLM.
    """

    answer: str
    sources: List[SourceCitation] = field(default_factory=list)
    valid_source_ids: List[str] = field(default_factory=list)
    removed_source_ids: List[str] = field(default_factory=list)
    skipped_llm: bool = False

    def __iter__(self) -> Iterator[Any]:
        """Hỗ trợ giải nén bộ đôi: verified_answer, sources = citation_service.verify(...)."""
        yield self.answer
        yield self.sources


def extract_citation_ids(answer_text: str) -> List[str]:
    """
    [SP4-03.1] Quét câu trả lời của LLM bằng Regex để trích xuất tất cả các mã nguồn
    được nhắc tới (ví dụ: [S1], [S3] hoặc [S1, S3]), giữ nguyên thứ tự xuất hiện đầu tiên
    và loại bỏ trùng lặp.
    """
    if not answer_text or not answer_text.strip():
        return []

    extracted: List[str] = []
    seen = set()

    for group_match in BRACKET_CITATION_GROUP_PATTERN.finditer(answer_text):
        inner_content = group_match.group(1)
        for id_match in SINGLE_SOURCE_ID_PATTERN.finditer(inner_content):
            norm_id = id_match.group(0).upper()
            if norm_id not in seen:
                seen.add(norm_id)
                extracted.append(norm_id)

    return extracted


def _is_refusal_answer(answer_text: str) -> bool:
    """Kiểm tra xem câu trả lời có phải là thông báo từ chối do ngoài phạm vi tài liệu hay không."""
    lower = normalize_unicode_nfc(answer_text or "").strip().lower()
    if not lower:
        return True
    if lower == NO_CONTEXT_REFUSAL_MESSAGE.lower():
        return True
    return any(phrase in lower for phrase in REFUSAL_PHRASES)


def _convert_entry_to_citation(
    source_id: str,
    entry: Union[SourceMapEntry, SourceCitation, Mapping[str, Any]],
) -> SourceCitation:
    """
    [SP4-03.3] Chuyển đổi một mục trong bảng source_map của Backend sang đối tượng
    SourceCitation chuẩn (source_id, document_id, filename, page_number, chunk_index, excerpt).
    """
    if isinstance(entry, SourceCitation):
        return entry

    if isinstance(entry, SourceMapEntry):
        return entry.to_source_citation()

    if isinstance(entry, Mapping):
        raw_doc_id = entry.get("document_id")
        doc_uuid = (
            raw_doc_id
            if isinstance(raw_doc_id, uuid.UUID)
            else uuid.UUID(str(raw_doc_id))
        )
        raw_page = entry.get("page_number")
        valid_page = (
            int(raw_page)
            if (raw_page is not None and int(raw_page) >= 1)
            else None
        )
        raw_chunk_idx = entry.get("chunk_index")
        valid_chunk_idx = (
            int(raw_chunk_idx)
            if (raw_chunk_idx is not None and int(raw_chunk_idx) >= 0)
            else None
        )
        raw_score = entry.get("score", entry.get("similarity_score"))
        return SourceCitation(
            source_id=str(entry.get("source_id") or source_id).upper(),
            document_id=doc_uuid,
            filename=str(entry.get("filename") or "unknown"),
            page_number=valid_page,
            chunk_index=valid_chunk_idx,
            chunk_id=str(entry.get("chunk_id")) if entry.get("chunk_id") else None,
            excerpt=str(entry.get("excerpt") or entry.get("text") or "").strip(),
            score=float(raw_score) if raw_score is not None else None,
        )

    raise TypeError(f"Kiểu dữ liệu mục source_map không hợp lệ: {type(entry)}")


class CitationService:
    """
    [SP4-03.1 -> SP4-03.4] Dịch vụ xác thực trích dẫn nguồn hai lớp (Two-Layer Citation Verification):
    - Lớp 1: LLM gắn mã định danh tạm thời [S1], [S2]... trong văn bản trả lời.
    - Lớp 2: Backend dùng Regex bóc tách [Sx], đối chiếu với bảng source_map trong bộ nhớ,
      tự động xóa bỏ mọi mã [Sx] không tồn tại và ánh xạ sang metadata thật (filename, page_number, excerpt).
    """

    def __init__(self, refusal_message: str = NO_CONTEXT_REFUSAL_MESSAGE) -> None:
        self.refusal_message = refusal_message

    def build_no_context_result(self) -> VerifiedCitationResult:
        """
        [SP4-03.4] Trả về câu thông báo từ chối lịch sự và mảng sources rỗng
        khi không tìm thấy ngữ cảnh phù hợp mà không tốn lượt gọi LLM.
        """
        return VerifiedCitationResult(
            answer=self.refusal_message,
            sources=[],
            valid_source_ids=[],
            removed_source_ids=[],
            skipped_llm=True,
        )

    def verify_and_map(
        self,
        answer_text: Optional[str],
        source_map: Optional[Mapping[str, Union[SourceMapEntry, SourceCitation, Mapping[str, Any]]]],
    ) -> VerifiedCitationResult:
        """
        [SP4-03.1 -> SP4-03.4] Quét câu trả lời của LLM, đối chiếu với source_map,
        loại bỏ các mã trích dẫn ảo giác và tạo danh sách SourceCitation chuẩn cho Frontend.
        """
        # [SP4-03.4] Nếu không có ngữ cảnh (source_map rỗng) hoặc chưa có câu trả lời
        if not source_map:
            return self.build_no_context_result()

        cleaned_answer = normalize_unicode_nfc(answer_text or "").strip()
        if not cleaned_answer:
            return self.build_no_context_result()

        # Chuẩn hóa khóa của source_map về chữ hoa ('S1', 'S2'...)
        normalized_map: Dict[str, Union[SourceMapEntry, SourceCitation, Mapping[str, Any]]] = {
            str(k).strip().lstrip("[").rstrip("]").upper(): v
            for k, v in source_map.items()
        }

        # Nếu LLM trả lời từ chối (tài liệu không đề cập), đảm bảo trả về mảng sources rỗng
        if _is_refusal_answer(cleaned_answer):
            stripped_refusal = BRACKET_CITATION_GROUP_PATTERN.sub("", cleaned_answer)
            stripped_refusal = re.sub(r"\s+([.,;!?])", r"\1", stripped_refusal)
            stripped_refusal = re.sub(r" {2,}", " ", stripped_refusal).strip()
            return VerifiedCitationResult(
                answer=stripped_refusal or self.refusal_message,
                sources=[],
                valid_source_ids=[],
                removed_source_ids=[],
                skipped_llm=False,
            )

        valid_source_ids: List[str] = []
        removed_source_ids: List[str] = []
        seen_valid = set()
        seen_removed = set()

        def _replace_citation_group(match: re.Match[str]) -> str:
            inner = match.group(1)
            ids_in_group = [m.group(0).upper() for m in SINGLE_SOURCE_ID_PATTERN.finditer(inner)]
            kept_labels: List[str] = []

            for sid in ids_in_group:
                if sid in normalized_map:
                    kept_labels.append(f"[{sid}]")
                    if sid not in seen_valid:
                        seen_valid.add(sid)
                        valid_source_ids.append(sid)
                else:
                    if sid not in seen_removed:
                        seen_removed.add(sid)
                        removed_source_ids.append(sid)

            return " ".join(kept_labels)

        # [SP4-03.1 & SP4-03.2] Quét và thay thế trực tiếp trên văn bản trả lời:
        # - Giữ lại các nhãn hợp lệ (và tách [S1, S2] -> [S1] [S2])
        # - Xóa sạch các nhãn ảo giác không có trong source_map (ví dụ [S99])
        verified_answer = BRACKET_CITATION_GROUP_PATTERN.sub(
            _replace_citation_group,
            cleaned_answer,
        )
        # Dọn dẹp khoảng trắng thừa trước dấu câu sau khi xóa thẻ ảo giác và lọc bỏ câu mở đầu rập khuôn (Bước 5)
        verified_answer = re.sub(r"\s+([.,;!?])", r"\1", verified_answer)
        verified_answer = re.sub(r"[ \t]{2,}", " ", verified_answer).strip()
        verified_answer = clean_robotic_phrases(verified_answer)

        if removed_source_ids:
            logger.warning(
                "Phát hiện và loại bỏ %d mã trích dẫn không hợp lệ (ảo giác) từ LLM: %s",
                len(removed_source_ids),
                removed_source_ids,
            )

        # [SP4-03.3] Ánh xạ danh sách mã hợp lệ sang đối tượng SourceCitation hoàn chỉnh
        sources: List[SourceCitation] = [
            _convert_entry_to_citation(sid, normalized_map[sid])
            for sid in valid_source_ids
        ]

        return VerifiedCitationResult(
            answer=verified_answer,
            sources=sources,
            valid_source_ids=valid_source_ids,
            removed_source_ids=removed_source_ids,
            skipped_llm=False,
        )


def verify_citations(
    answer_text: Optional[str],
    source_map: Optional[Mapping[str, Union[SourceMapEntry, SourceCitation, Mapping[str, Any]]]],
) -> VerifiedCitationResult:
    """Hàm tiện ích cấp mô-đun thực hiện xác thực trích dẫn hai lớp."""
    service = CitationService()
    return service.verify_and_map(answer_text=answer_text, source_map=source_map)


def resolve_citations_or_refuse(
    chunks: Sequence[Any],
) -> Optional[VerifiedCitationResult]:
    """
    [SP4-03.4] Kiểm tra nhanh trước khi gọi LLM: nếu danh sách đoạn văn truy xuất được
    bị rỗng, trả về ngay câu thông báo lịch sự và mảng sources rỗng mà không gọi LLM.
    Nếu có ngữ cảnh hợp lệ, trả về None để tiếp tục luồng gọi LLM.
    """
    if not chunks:
        return CitationService().build_no_context_result()
    return None

