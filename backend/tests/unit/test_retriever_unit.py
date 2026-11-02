from pathlib import Path
from typing import Sequence
import uuid

import numpy as np
import pytest

from app.services.embedding_service import EmbeddingService
from app.services.retriever import (
    SemanticRetriever,
    build_document_filter,
    cosine_distance_to_similarity,
    retrieve,
)
from app.services.vector_store import VectorStore


class ConceptSemanticFakeModel:
    """
    Mô hình embedding ngữ nghĩa có chủ đích cho kiểm thử:
    Gán các câu thuộc cùng chủ đề (nghỉ phép / thử việc / lương) về cùng hướng vector
    để kiểm tra độ tương đồng Cosine, ngưỡng lọc và khử trùng lặp.
    """

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _text_to_vector(self, text: str) -> np.ndarray:
        lower = text.lower()
        vec = np.zeros(self.dim, dtype=np.float32)

        # Trục 0: Chủ đề nghỉ phép năm / phép hằng năm
        if any(k in lower for k in ["nghỉ phép", "nghỉ hằng năm", "12 ngày", "phép năm"]):
            vec[0] += 10.0
        # Trục 1: Chủ đề thời gian thử việc
        if any(k in lower for k in ["thử việc", "60 ngày", "tập sự"]):
            vec[1] += 10.0
        # Trục 2: Chủ đề tiền lương / bảo hiểm
        if any(k in lower for k in ["tiền lương", "bảo hiểm", "thưởng"]):
            vec[2] += 10.0
        # Nhiễu nhỏ cố định để vector không bao giờ bằng 0 hoàn toàn
        vec[3] = 0.1

        norm = np.linalg.norm(vec)
        return vec / (norm if norm > 0 else 1.0)

    def encode(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        return np.vstack([self._text_to_vector(t) for t in texts])


def test_cosine_distance_conversion_and_where_filter() -> None:
    """[SP3-04.2 & SP3-04.3] Kiểm tra chuyển đổi khoảng cách Cosine và tạo bộ lọc where."""
    assert cosine_distance_to_similarity(0.0) == 1.0
    assert cosine_distance_to_similarity(0.15) == pytest.approx(0.85)
    assert cosine_distance_to_similarity(1.0) == 0.0

    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    assert build_document_filter(None) is None
    assert build_document_filter([id1]) == {"document_id": str(id1)}
    assert build_document_filter([id1, id2]) == {
        "document_id": {"$in": [str(id1), str(id2)]}
    }


def test_semantic_retriever_top_k_filtering_dedup_and_sorting(tmp_path: Path) -> None:
    """
    [SP3-04.1 -> SP3-04.4] Kiểm tra truy xuất Top-K, lọc theo document_ids,
    lọc ngưỡng similarity_score, khử trùng lặp nội dung và sắp xếp giảm dần.
    """
    embedding_service = EmbeddingService()
    embedding_service.set_model(ConceptSemanticFakeModel(dim=1024))
    vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")

    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())

    texts = [
        # Doc 1 - Chunk 0 (Nghỉ phép)
        "Điều 113. Người lao động làm việc đủ 12 tháng thì được nghỉ hằng năm 12 ngày phép.",
        # Doc 1 - Chunk 1 (Trùng lặp nội dung với Chunk 0 để kiểm tra deduplication)
        "Điều 113. Người lao động làm việc đủ 12 tháng thì được nghỉ hằng năm 12 ngày phép.",
        # Doc 1 - Chunk 2 (Thử việc - khác chủ đề câu hỏi nghỉ phép)
        "Điều 25. Thời gian thử việc không quá 60 ngày đối với trình độ đại học.",
        # Doc 2 - Chunk 0 (Nghỉ phép trong tài liệu 2)
        "Mục 4. Nhân viên chính thức được nghỉ phép năm 12 ngày hưởng nguyên lương.",
    ]
    embeddings = embedding_service.encode_documents(texts)
    metadatas = [
        {"document_id": doc1_id, "filename": "Bo_luat_2019.pdf", "page_number": 45, "chunk_index": 0, "source_type": "pdf"},
        {"document_id": doc1_id, "filename": "Bo_luat_2019.pdf", "page_number": 45, "chunk_index": 1, "source_type": "pdf"},
        {"document_id": doc1_id, "filename": "Bo_luat_2019.pdf", "page_number": 12, "chunk_index": 2, "source_type": "pdf"},
        {"document_id": doc2_id, "filename": "Noi_quy.docx", "page_number": None, "paragraph_index": 8, "chunk_index": 0, "source_type": "docx"},
    ]
    chunk_ids = [
        f"{doc1_id}_chunk_0",
        f"{doc1_id}_chunk_1",
        f"{doc1_id}_chunk_2",
        f"{doc2_id}_chunk_0",
    ]
    vector_store.add_chunks(texts, embeddings, metadatas, chunk_ids)

    # 1. Truy vấn toàn bộ tài liệu về "nghỉ phép năm" với ngưỡng min_similarity=0.5
    results_all = retrieve(
        question="Quy định về số ngày nghỉ phép năm của người lao động?",
        top_k=5,
        document_ids=None,
        min_similarity=0.5,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    # Chunk 0 và Chunk 1 trùng nội dung nên chỉ giữ lại 1 bản; Chunk 2 (thử việc) có sim < 0.5 bị loại
    assert len(results_all) == 2
    assert results_all[0].similarity_score >= results_all[1].similarity_score
    assert all(r.similarity_score >= 0.5 for r in results_all)

    # 2. Lọc chỉ trong phạm vi doc1_id ([SP3-04.2])
    retriever_obj = SemanticRetriever(
        embedding_service=embedding_service,
        vector_store=vector_store,
        min_similarity=0.5,
    )
    results_doc1_only = retriever_obj.retrieve(
        question="Quy định nghỉ phép hằng năm?",
        top_k=5,
        document_ids=[doc1_id],
    )
    assert len(results_doc1_only) == 1
    assert results_doc1_only[0].document_id == doc1_id
    assert results_doc1_only[0].page_number == 45
    assert results_doc1_only[0].filename == "Bo_luat_2019.pdf"
