from dataclasses import asdict, dataclass
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Union
import uuid

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.vector_store import VectorStore, get_vector_store
from app.utils.text_cleaner import normalize_unicode_nfc

logger = get_logger(__name__)

DEFAULT_MIN_SIMILARITY = 0.15


@dataclass
class RetrievedChunk:
    """
    Đoạn văn bản kết quả sau khi truy xuất ngữ nghĩa Top-K ([SP3-04.1 -> SP3-04.4]),
    chứa đầy đủ nội dung, điểm tương đồng Cosine (similarity_score) và metadata nguồn.
    """

    chunk_id: str
    text: str
    document_id: str
    filename: str
    similarity_score: float
    distance: float
    page_number: Optional[int] = None
    paragraph_index: Optional[int] = None
    section_title: Optional[str] = None
    chunk_index: Optional[int] = None
    source_type: str = "pdf"

    @property
    def score(self) -> float:
        """Bí danh tương thích với trường score trong SourceCitation."""
        return self.similarity_score

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "paragraph_index": self.paragraph_index,
            "section_title": self.section_title,
            "chunk_index": self.chunk_index,
            "source_type": self.source_type,
        }

    def __getitem__(self, key: str) -> Any:
        if key == "score":
            return self.similarity_score
        if key == "metadata":
            return self.metadata
        return getattr(self, key)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["score"] = self.similarity_score
        data["metadata"] = self.metadata
        return data


def cosine_distance_to_similarity(distance: float) -> float:
    """
    [SP3-04.3] Chuyển đổi khoảng cách Cosine (distance = 1 - cos_sim) từ ChromaDB
    sang điểm số tương đồng ngữ nghĩa similarity_score thuộc [-1.0, 1.0].
    """
    raw_similarity = 1.0 - float(distance)
    clamped = max(-1.0, min(1.0, raw_similarity))
    return round(clamped, 6)


def build_document_filter(
    document_ids: Optional[Sequence[Union[str, uuid.UUID]]],
) -> Optional[Dict[str, Any]]:
    """
    [SP3-04.2] Thiết lập bộ lọc điều kiện (where filter) trên ChromaDB
    để chỉ tìm kiếm trong phạm vi các document_id mà người dùng đã chọn.
    """
    if document_ids is None:
        return None

    clean_ids = list(
        dict.fromkeys(str(doc_id).strip() for doc_id in document_ids if str(doc_id).strip())
    )
    if not clean_ids:
        return {"document_id": "__EMPTY_DOCUMENT_SELECTION__"}

    if len(clean_ids) == 1:
        return {"document_id": clean_ids[0]}

    return {"document_id": {"$in": clean_ids}}


def _normalize_for_dedup(text: str) -> str:
    """Chuẩn hóa nội dung văn bản để nhận diện và loại bỏ các Chunk trùng lặp ([SP3-04.4])."""
    normalized = normalize_unicode_nfc(text or "").strip().lower()
    return re.sub(r"\s+", " ", normalized)


class SemanticRetriever:
    """
    [SP3-04.1 -> SP3-04.4] Bộ truy xuất ngữ nghĩa tìm kiếm Top-K đoạn văn bản
    phù hợp nhất với câu hỏi của người dùng từ ChromaDB.
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None,
        default_top_k: Optional[int] = None,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> None:
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()
        self.default_top_k = (
            default_top_k
            if default_top_k is not None
            else (settings.RETRIEVAL_TOP_K or settings.TOP_K or 5)
        )
        self.min_similarity = min_similarity

    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
        document_ids: Optional[Sequence[Union[str, uuid.UUID]]] = None,
        min_similarity: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """
        [SP3-04.1 -> SP3-04.4] Tìm kiếm Top-K đoạn văn bản có độ tương đồng ngữ nghĩa cao nhất:
        1. Vector hóa câu hỏi bằng mô hình BAAI/bge-m3.
        2. Áp dụng bộ lọc where theo document_ids (nếu có).
        3. Chuyển đổi khoảng cách Cosine sang similarity_score và lọc theo ngưỡng tối thiểu.
        4. Khử trùng lặp nội dung và sắp xếp giảm dần theo similarity_score.
        """
        start_time = time.perf_counter()

        cleaned_question = normalize_unicode_nfc(question or "").strip()
        if not cleaned_question:
            raise ValueError("Câu hỏi truy vấn (question) không được để trống.")

        # Nếu người dùng truyền danh sách document_ids rỗng (không chọn tài liệu nào)
        if document_ids is not None and len(document_ids) == 0:
            return []

        effective_top_k = top_k if (top_k is not None and top_k > 0) else self.default_top_k
        threshold = (
            min_similarity if min_similarity is not None else self.min_similarity
        )

        # [SP3-04.1] Vector hóa câu hỏi
        query_vector = self.embedding_service.encode_query(
            cleaned_question,
            normalize_embeddings=True,
        )

        # [SP3-04.2] Tạo bộ lọc điều kiện where theo document_ids
        where_filter = build_document_filter(document_ids)

        # Lấy dư số lượng ứng viên để sau khi khử trùng lặp vẫn đủ Top-K
        candidate_k = max(effective_top_k * 2, effective_top_k + 5)
        raw_candidates = self.vector_store.query_similar(
            query_embedding=query_vector,
            n_results=candidate_k,
            where=where_filter,
        )

        # [SP3-04.3 & SP3-04.4] Chuyển đổi điểm số, lọc dưới ngưỡng và khử trùng lặp
        dedup_by_text: Dict[str, RetrievedChunk] = {}

        for item in raw_candidates:
            text_content = str(item.get("text") or "").strip()
            if not text_content:
                continue

            distance = float(item.get("distance", 1.0))
            sim_score = cosine_distance_to_similarity(distance)

            if sim_score < threshold:
                continue

            meta = item.get("metadata") or {}
            chunk_obj = RetrievedChunk(
                chunk_id=str(item.get("chunk_id") or meta.get("chunk_id") or ""),
                text=text_content,
                document_id=str(meta.get("document_id") or ""),
                filename=str(meta.get("filename") or "unknown"),
                similarity_score=sim_score,
                distance=distance,
                page_number=(
                    int(meta["page_number"])
                    if meta.get("page_number") is not None
                    else None
                ),
                paragraph_index=(
                    int(meta["paragraph_index"])
                    if meta.get("paragraph_index") is not None
                    else None
                ),
                section_title=(
                    str(meta["section_title"])
                    if meta.get("section_title") is not None
                    else None
                ),
                chunk_index=(
                    int(meta["chunk_index"])
                    if meta.get("chunk_index") is not None
                    else None
                ),
                source_type=str(meta.get("source_type") or "pdf"),
            )

            dedup_key = _normalize_for_dedup(text_content)
            existing = dedup_by_text.get(dedup_key)
            if existing is None or chunk_obj.similarity_score > existing.similarity_score:
                dedup_by_text[dedup_key] = chunk_obj

        # [SP3-04.4] Sắp xếp theo điểm tương đồng giảm dần và cắt đúng Top-K
        sorted_chunks = sorted(
            dedup_by_text.values(),
            key=lambda c: c.similarity_score,
            reverse=True,
        )[:effective_top_k]

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            "Truy xuất ngữ nghĩa hoàn tất trong %.1fms (question='%s...', top_k=%d, returned=%d)",
            elapsed_ms,
            cleaned_question[:50],
            effective_top_k,
            len(sorted_chunks),
        )
        return sorted_chunks


def retrieve(
    question: str,
    top_k: int = 5,
    document_ids: Optional[Sequence[Union[str, uuid.UUID]]] = None,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
    embedding_service: Optional[EmbeddingService] = None,
    vector_store: Optional[VectorStore] = None,
) -> List[RetrievedChunk]:
    """Hàm tiện ích cấp module thực hiện truy xuất Top-K đoạn văn bản phù hợp nhất."""
    retriever = SemanticRetriever(
        embedding_service=embedding_service,
        vector_store=vector_store,
        default_top_k=top_k,
        min_similarity=min_similarity,
    )
    return retriever.retrieve(
        question=question,
        top_k=top_k,
        document_ids=document_ids,
        min_similarity=min_similarity,
    )

