import hashlib
from typing import List, Sequence
import unicodedata

import numpy as np
import pytest

from app.services.embedding_service import (
    EmbeddingService,
    detect_compute_device,
    get_embedding_service,
)


class FakeBGEM3Model:
    """Mô hình giả lập BAAI/bge-m3 (1024 chiều) xác định phục vụ kiểm thử nhanh."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim
        self.encode_calls: list[dict] = []

    def encode(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        self.encode_calls.append(
            {
                "count": len(texts),
                "batch_size": batch_size,
                "normalize_embeddings": normalize_embeddings,
            }
        )
        rows: List[np.ndarray] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], "big") % (2**32 - 1)
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(self.dim).astype(np.float32)
            if normalize_embeddings:
                vec = vec / np.linalg.norm(vec)
            rows.append(vec)
        return np.vstack(rows)


def test_embedding_service_singleton_pattern() -> None:
    """[SP3-01.1] Kiểm tra EmbeddingService đảm bảo mẫu thiết kế Singleton."""
    service_a = EmbeddingService()
    service_b = get_embedding_service()
    assert service_a is service_b
    assert service_a.model_name == "BAAI/bge-m3"


def test_detect_compute_device() -> None:
    """[SP3-01.2] Kiểm tra hàm tự động nhận diện thiết bị phần cứng (CUDA/MPS/CPU)."""
    detected = detect_compute_device()
    assert detected in {"cuda", "mps", "cpu"}
    assert detect_compute_device("CPU") == "cpu"


def test_encode_documents_batch_and_l2_normalization() -> None:
    """[SP3-01.3] Kiểm tra encode_documents xử lý theo lô và chuẩn hóa vector L2 = 1.0."""
    fake_model = FakeBGEM3Model(dim=1024)
    service = get_embedding_service()
    service.set_model(fake_model)

    docs = [
        "Điều 113. Người lao động làm đủ 12 tháng được nghỉ 12 ngày phép.",
        "Điều 114. Ngày nghỉ hằng năm tăng thêm theo thâm niên làm việc.",
        "Điều 115. Nghỉ việc riêng mà vẫn hưởng nguyên lương.",
    ]
    vectors = service.encode_documents(docs, batch_size=2, normalize_embeddings=True)

    assert len(vectors) == 3
    assert len(vectors[0]) == 1024
    assert fake_model.encode_calls[-1]["batch_size"] == 2
    assert fake_model.encode_calls[-1]["normalize_embeddings"] is True

    # Kiểm tra độ dài chuẩn L2 của từng vector xấp xỉ 1.0
    for vec in vectors:
        norm = float(np.linalg.norm(np.asarray(vec, dtype=np.float32)))
        assert pytest.approx(norm, rel=1e-5) == 1.0


def test_encode_query_compatibility_and_nfc_consistency() -> None:
    """[SP3-01.4] Kiểm tra encode_query tương thích không gian vector và chuẩn hóa NFC."""
    fake_model = FakeBGEM3Model(dim=1024)
    service = get_embedding_service()
    service.set_model(fake_model)

    text_nfc = unicodedata.normalize("NFC", "Quy định nghỉ phép năm")
    text_nfd = unicodedata.normalize("NFD", "Quy định nghỉ phép năm")

    doc_vec = service.encode_documents([text_nfc])[0]
    query_vec = service.encode_query(text_nfd)

    assert len(query_vec) == 1024
    # Tích vô hướng (Cosine similarity) giữa NFC và NFD của cùng câu phải bằng 1.0
    cosine_sim = float(np.dot(doc_vec, query_vec))
    assert pytest.approx(cosine_sim, rel=1e-5) == 1.0

    # Câu hỏi rỗng phải bị từ chối
    with pytest.raises(ValueError):
        service.encode_query("   ")

