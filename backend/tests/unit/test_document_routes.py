from pathlib import Path
from typing import Dict, Sequence
import uuid

from fastapi.testclient import TestClient
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_document_service
from app.database.connection import Base
from app.main import app
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore, count_by_document_id


class FastDeterministicEmbeddingModel:
    """Mô hình embedding giả lập 1024 chiều phục vụ kiểm thử nhanh các REST API tài liệu."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def encode(
        self,
        texts: Sequence[str],
        batch_size: int = 32,
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        rows = []
        for idx, text in enumerate(texts):
            vec = np.zeros(self.dim, dtype=np.float32)
            vec[idx % self.dim] = 1.0
            vec[(len(text) + idx) % self.dim] += 0.5
            norm = np.linalg.norm(vec)
            rows.append(vec / (norm if norm > 0 else 1.0))
        return np.vstack(rows)


def test_sp4_04_document_lifecycle_apis(
    tmp_path: Path,
    sample_files: Dict[str, Path],
) -> None:
    """
    [SP4-04.1 -> SP4-04.4] Kiểm thử toàn bộ vòng đời RESTful API quản lý tài liệu:
    - POST /api/documents/upload (nhận multipart/form-data, lưu tệp, chạy Indexing Pipeline)
    - GET /api/documents (trả về danh sách tài liệu kèm status, file_size, created_at, lọc theo status)
    - GET /api/documents/{id} (trả về chi tiết tài liệu và chunk_count; 404 nếu không tồn tại)
    - DELETE /api/documents/{id} (xóa đồng bộ 3 nơi: ChromaDB, ổ cứng và CSDL)
    """
    db_file = tmp_path / "test_doc_api.sqlite"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db_session = SessionLocal()

    embedding_service = EmbeddingService()
    embedding_service.set_model(FastDeterministicEmbeddingModel(dim=1024))
    vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")
    upload_dir = tmp_path / "uploads"

    def override_get_document_service() -> DocumentService:
        return DocumentService(
            db=db_session,
            embedding_service=embedding_service,
            vector_store=vector_store,
            default_upload_dir=upload_dir,
        )

    app.dependency_overrides[get_document_service] = override_get_document_service

    try:
        client = TestClient(app)

        # 1. [SP4-04.1] POST /api/documents/upload với tệp PDF 25 trang và tệp DOCX hợp lệ
        pdf_bytes = sample_files["pdf_25_pages"].read_bytes()
        resp_pdf = client.post(
            "/api/documents/upload",
            files={"file": ("Bo_luat_25_trang.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp_pdf.status_code == 201
        pdf_payload = resp_pdf.json()
        pdf_doc = pdf_payload["document"]
        pdf_id = pdf_doc["id"]

        assert pdf_doc["filename"] == "Bo_luat_25_trang.pdf"
        assert pdf_doc["file_type"] == "pdf"
        assert pdf_doc["file_size"] == len(pdf_bytes)
        assert pdf_doc["status"] == "processed"
        assert pdf_doc["chunk_count"] >= 25
        assert pdf_doc["created_at"] is not None
        assert count_by_document_id(pdf_id, vector_store=vector_store) == pdf_doc["chunk_count"]

        docx_bytes = sample_files["docx_with_table"].read_bytes()
        resp_docx = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "Noi_quy_nhan_su.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert resp_docx.status_code == 201
        docx_doc = resp_docx.json()["document"]
        docx_id = docx_doc["id"]
        assert docx_doc["status"] == "processed"
        assert docx_doc["chunk_count"] >= 1

        # Kiểm tra tải lên tệp giả mạo (.exe đổi đuôi thành .pdf) -> 400 INVALID_FILE
        spoofed_bytes = sample_files["invalid_file"].read_bytes()
        resp_invalid = client.post(
            "/api/documents/upload",
            files={"file": ("Virus.pdf", spoofed_bytes, "application/pdf")},
        )
        assert resp_invalid.status_code == 400
        assert resp_invalid.json()["error_code"] == "INVALID_FILE"

        # Kiểm tra tải lên tệp PDF ảnh scan rỗng -> 422 EMPTY_DOCUMENT (rollback sang status='failed')
        empty_pdf_bytes = sample_files["empty_pdf"].read_bytes()
        resp_empty = client.post(
            "/api/documents/upload",
            files={"file": ("Scan_rong.pdf", empty_pdf_bytes, "application/pdf")},
        )
        assert resp_empty.status_code == 422
        assert resp_empty.json()["error_code"] == "EMPTY_DOCUMENT"

        # 2. [SP4-04.2] GET /api/documents (Lấy danh sách tài liệu & lọc theo status)
        resp_list_all = client.get("/api/documents")
        assert resp_list_all.status_code == 200
        list_all_data = resp_list_all.json()
        assert list_all_data["total"] == 3
        assert len(list_all_data["items"]) == 3

        resp_list_processed = client.get("/api/documents?status=processed")
        assert resp_list_processed.status_code == 200
        assert resp_list_processed.json()["total"] == 2

        resp_list_failed = client.get("/api/documents?status=failed")
        assert resp_list_failed.status_code == 200
        assert resp_list_failed.json()["total"] == 1
        assert resp_list_failed.json()["items"][0]["filename"] == "Scan_rong.pdf"

        # 3. [SP4-04.3] GET /api/documents/{id} (Lấy chi tiết 1 tài liệu và chunk_count)
        resp_detail = client.get(f"/api/documents/{pdf_id}")
        assert resp_detail.status_code == 200
        detail_data = resp_detail.json()
        assert detail_data["id"] == pdf_id
        assert detail_data["filename"] == "Bo_luat_25_trang.pdf"
        assert detail_data["chunk_count"] == pdf_doc["chunk_count"]
        physical_pdf_path = Path(detail_data["storage_path"])
        assert physical_pdf_path.exists()

        # [SP5-04.4] Kiểm tra GET /api/documents/{id}/file trả về tệp PDF inline để đối chiếu trang
        resp_file = client.get(f"/api/documents/{pdf_id}/file")
        assert resp_file.status_code == 200
        assert resp_file.headers["content-type"] == "application/pdf"
        assert "inline" in resp_file.headers.get("content-disposition", "")
        assert len(resp_file.content) == len(pdf_bytes)

        # Kiểm tra 404 khi ID không tồn tại
        random_id = uuid.uuid4()
        resp_not_found = client.get(f"/api/documents/{random_id}")
        assert resp_not_found.status_code == 404
        assert resp_not_found.json()["error_code"] == "DOCUMENT_NOT_FOUND"

        # 4. [SP4-04.4] DELETE /api/documents/{id} (Xóa đồng bộ 3 nơi: ChromaDB, ổ cứng, PostgreSQL)
        resp_delete = client.delete(f"/api/documents/{pdf_id}")
        assert resp_delete.status_code == 200
        delete_data = resp_delete.json()
        assert delete_data["document_id"] == pdf_id

        # Xác nhận đã xóa sạch ở cả 3 nơi
        assert count_by_document_id(pdf_id, vector_store=vector_store) == 0
        assert not physical_pdf_path.exists()
        assert client.get(f"/api/documents/{pdf_id}").status_code == 404

        # Tài liệu DOCX còn lại vẫn nguyên vẹn
        assert count_by_document_id(docx_id, vector_store=vector_store) == docx_doc["chunk_count"]
    finally:
        app.dependency_overrides.clear()
        db_session.close()

