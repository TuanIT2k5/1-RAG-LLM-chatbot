from pathlib import Path
import uuid

import numpy as np
import pytest

from app.services.vector_store import (
    MISSING_INTEGER_VALUE,
    VectorStore,
    restore_metadata,
    sanitize_metadata,
)

DIM = 1024


def _random_unit_vectors(count: int, seed: int = 42) -> list[list[float]]:
    rng = np.random.default_rng(seed)
    matrix = rng.standard_normal((count, DIM)).astype(np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix.tolist()


def test_sanitize_metadata_converts_none_and_complex_types() -> None:
    """[SP3-02.4] None -> -1 (khóa số nguyên) hoặc "" (khóa chuỗi); UUID/list -> str."""
    doc_id = uuid.uuid4()
    raw = {
        "document_id": doc_id,
        "filename": "Noi_quy.docx",
        "page_number": None,
        "paragraph_index": 7,
        "section_title": None,
        "chunk_index": "3",
        "score": 0.91,
        "is_table": True,
        "tags": ["luat", "lao dong"],
    }
    cleaned = sanitize_metadata(raw)

    assert cleaned["document_id"] == str(doc_id)
    assert cleaned["page_number"] == MISSING_INTEGER_VALUE
    assert cleaned["paragraph_index"] == 7
    assert cleaned["section_title"] == ""
    assert cleaned["chunk_index"] == 3
    assert cleaned["score"] == 0.91
    assert cleaned["is_table"] is True
    assert cleaned["tags"] == "luat, lao dong"
    assert all(isinstance(v, (str, int, float, bool)) for v in cleaned.values())

    restored = restore_metadata(cleaned)
    assert restored["page_number"] is None
    assert restored["section_title"] is None
    assert restored["paragraph_index"] == 7


def test_persistent_client_and_cosine_collection(tmp_path: Path) -> None:
    """[SP3-02.1 & SP3-02.2] PersistentClient lưu bền vững và Collection dùng khoảng cách Cosine."""
    persist_dir = tmp_path / "chroma_db"
    store = VectorStore(persist_dir=persist_dir)

    assert persist_dir.exists()
    assert store.collection_name == "documents_index"
    assert store.distance_space == "cosine"
    assert store.count() == 0


def test_add_chunks_and_data_survives_restart(tmp_path: Path) -> None:
    """[SP3-02.3] add_chunks() lưu đủ dữ liệu và vẫn còn sau khi khởi tạo lại client (giả lập tắt server)."""
    persist_dir = tmp_path / "chroma_db"
    doc_id = str(uuid.uuid4())

    texts = [
        "Điều 113. Người lao động làm đủ 12 tháng được nghỉ 12 ngày phép.",
        "Điều 114. Cứ đủ 05 năm làm việc được tăng thêm 01 ngày phép.",
        "Bảng phép năm | Nhân viên văn phòng | 12 ngày làm việc",
    ]
    vectors = _random_unit_vectors(len(texts))
    chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(texts))]
    metadatas = [
        {"document_id": doc_id, "filename": "Bo_luat.pdf", "page_number": 45, "chunk_index": 0, "source_type": "pdf"},
        {"document_id": doc_id, "filename": "Bo_luat.pdf", "page_number": 46, "chunk_index": 1, "source_type": "pdf"},
        {"document_id": doc_id, "filename": "Bo_luat.pdf", "page_number": None, "chunk_index": 2, "source_type": "pdf"},
    ]

    store = VectorStore(persist_dir=persist_dir)
    saved = store.add_chunks(texts, vectors, metadatas, chunk_ids)
    assert saved == 3
    assert store.count() == 3

    # Upsert lại cùng chunk_ids không được nhân bản dữ liệu
    store.add_chunks(texts, vectors, metadatas, chunk_ids)
    assert store.count() == 3

    # Giả lập khởi động lại server: tạo client mới trỏ cùng thư mục
    del store
    reopened = VectorStore(persist_dir=persist_dir)
    assert reopened.count() == 3

    items = reopened.get_chunks_by_ids([chunk_ids[0], chunk_ids[2]])
    by_id = {item["chunk_id"]: item for item in items}
    assert by_id[chunk_ids[0]]["metadata"]["page_number"] == 45
    assert by_id[chunk_ids[0]]["metadata"]["filename"] == "Bo_luat.pdf"
    assert by_id[chunk_ids[2]]["metadata"]["page_number"] is None
    assert "Điều 113" in by_id[chunk_ids[0]]["text"]


def test_add_chunks_validates_input_lengths(tmp_path: Path) -> None:
    """[SP3-02.3] Từ chối dữ liệu đầu vào không đồng bộ độ dài hoặc trùng chunk_id."""
    store = VectorStore(persist_dir=tmp_path / "chroma_db")
    vectors = _random_unit_vectors(2)

    with pytest.raises(ValueError):
        store.add_chunks(["a", "b"], vectors, [{"x": 1}], ["id1", "id2"])

    with pytest.raises(ValueError):
        store.add_chunks(["a", "b"], vectors, [{"x": 1}, {"x": 2}], ["dup", "dup"])

    assert store.add_chunks([], [], [], []) == 0

