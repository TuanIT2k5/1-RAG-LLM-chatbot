import io
from pathlib import Path
import time
from typing import Dict, List, Sequence

import numpy as np
import pymupdf as fitz
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import Base
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.retriever import SemanticRetriever, retrieve
from app.services.text_splitter import RecursiveTextSplitter
from app.services.vector_store import (
    VectorStore,
    count_by_document_id,
    delete_by_document_id,
)


class VietnameseSynonymSemanticModel:
    """
    Mô hình giả lập không gian vector ngữ nghĩa đa ngôn ngữ (1024 chiều, chuẩn hóa L2)
    nhận diện các cụm từ đồng nghĩa tiếng Việt (synonym clusters) để kiểm thử tích hợp
    SP3-05.3, SP3-05.4 và Definition of Done của Sprint 3.
    """

    SYNONYM_CLUSTERS: Dict[int, List[str]] = {
        # Cluster 0: Nghỉ phép hằng năm / Chế độ phép thường niên / Ngày nghỉ hưởng lương
        0: [
            "nghỉ hằng năm",
            "nghỉ phép",
            "phép thường niên",
            "ngày nghỉ có lương",
            "trọn một năm",
            "đủ 12 tháng",
            "12 ngày phép",
        ],
        # Cluster 1: Thời gian thử việc / Thời hạn tập sự / Trình độ đại học 60 ngày
        1: [
            "thử việc",
            "tập sự",
            "thời hạn thử thách",
            "60 ngày",
            "trình độ đại học",
            "kỹ sư mới tuyển",
        ],
        # Cluster 2: Làm thêm giờ / Tăng ca / Phụ cấp ngoài giờ
        2: [
            "làm thêm giờ",
            "tăng ca",
            "ngoài giờ hành chính",
            "phụ cấp làm thêm",
            "tối đa 40 giờ",
            "200 giờ một năm",
        ],
        # Cluster 3: Bảo mật dữ liệu / An toàn thông tin / Quyền riêng tư
        3: [
            "bảo mật",
            "an toàn thông tin",
            "dữ liệu mật",
            "mã hóa tài liệu",
            "rò rỉ thông tin",
        ],
        # Cluster 4: Chấm dứt hợp đồng / Đơn phương nghỉ việc / Báo trước 30 ngày
        4: [
            "chấm dứt hợp đồng",
            "nghỉ việc",
            "thôi việc",
            "báo trước 30 ngày",
            "bàn giao công việc",
        ],
    }

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def _encode_single(self, text: str) -> np.ndarray:
        lower = text.lower()
        vec = np.zeros(self.dim, dtype=np.float32)

        matched_any = False
        for axis, keywords in self.SYNONYM_CLUSTERS.items():
            hits = sum(1 for kw in keywords if kw in lower)
            if hits > 0:
                vec[axis] = 10.0 + float(hits)
                matched_any = True

        # Thêm thành phần đặc trưng nhẹ theo trang/nội dung để phân biệt các trang khác nhau
        for page_num in range(1, 30):
            if f"trang {page_num}" in lower or f"trang số {page_num}" in lower:
                vec[20 + page_num] += 3.0

        if not matched_any:
            seed = sum(ord(ch) for ch in lower) % 500
            vec[100 + seed] = 5.0

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
        return np.vstack([self._encode_single(t) for t in texts])


def _create_db_session(tmp_path: Path) -> Session:
    db_file = tmp_path / "test_retriever_integration.sqlite"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def _create_policy_pdf_bytes(company_tag: str = "Tập đoàn Alpha") -> bytes:
    """
    Tạo tệp PDF 6 trang chứa các quy định nhân sự bằng tiếng Việt để kiểm thử
    truy vấn bằng câu hỏi đồng nghĩa (synonym query) và đối chiếu chính xác page_number.
    """
    doc = fitz.open()
    pages_content = [
        (
            1,
            f"CHƯƠNG 1 ({company_tag}): QUY ĐỊNH CHUNG VỀ TUYỂN DỤNG\n\n"
            "Điều 1. Thời gian thử việc áp dụng đối với ứng viên có trình độ đại học trở lên "
            "là tối đa 60 ngày làm việc. Trong thời gian này nhân sự được hưởng 85% mức lương.",
        ),
        (
            2,
            f"CHƯƠNG 2 ({company_tag}): THỜI GIỜ LÀM VIỆC VÀ NGHỈ NGƠI\n\n"
            "Điều 5. Người lao động làm việc đủ 12 tháng tại doanh nghiệp thì được nghỉ hằng năm "
            "12 ngày phép và hưởng nguyên lương theo hợp đồng lao động.",
        ),
        (
            3,
            f"CHƯƠNG 3 ({company_tag}): QUY ĐỊNH VỀ LÀM THÊM GIỜ\n\n"
            "Điều 9. Số giờ làm thêm của người lao động không quá 40 giờ trong một tháng "
            "và tổng cộng không quá 200 giờ một năm.",
        ),
        (
            4,
            f"CHƯƠNG 4 ({company_tag}): BẢO MẬT VÀ AN TOÀN THÔNG TIN\n\n"
            "Điều 12. Mọi tài liệu nội bộ và dữ liệu mật của khách hàng phải được mã hóa tài liệu "
            "trước khi lưu trữ nhằm ngăn chặn nguy cơ rò rỉ thông tin.",
        ),
        (
            5,
            f"CHƯƠNG 5 ({company_tag}): CHẤM DỨT HỢP ĐỒNG LAO ĐỘNG\n\n"
            "Điều 15. Khi đơn phương chấm dứt hợp đồng xác định thời hạn, nhân viên phải "
            "báo trước 30 ngày và hoàn tất biên bản bàn giao công việc.",
        ),
        (
            6,
            f"PHỤ LỤC ({company_tag}): HƯỚNG DẪN NGHỈ PHÉP NĂM BỔ SUNG\n\n"
            "Cứ đủ 05 năm làm việc liên tục cho công ty thì số ngày nghỉ hằng năm của người lao động "
            "được tăng thêm tương ứng 01 ngày phép.",
        ),
    ]
    for page_no, body in pages_content:
        page = doc.new_page(width=595, height=842)
        writer = fitz.TextWriter(page.rect)
        font = fitz.Font("helv")
        writer.append(
            (50, 70),
            f"Tài liệu chính sách nhân sự ({company_tag}) - Trang {page_no}",
            font=font,
            fontsize=12,
        )
        y = 110
        for line in body.split("\n"):
            writer.append((50, y), line, font=font, fontsize=11)
            y += 20
        writer.write_text(page)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_sp3_05_1_and_2_count_and_delete_by_document_id(
    tmp_path: Path,
    sample_files: Dict[str, Path],
) -> None:
    """
    [SP3-05.1 & SP3-05.2] Kiểm tra hàm đối soát số lượng Chunk (count_by_document_id)
    giữa PostgreSQL và ChromaDB, và hàm xóa toàn bộ vector của một tài liệu (delete_by_document_id).
    """
    db = _create_db_session(tmp_path)
    try:
        embedding_service = EmbeddingService()
        embedding_service.set_model(VietnameseSynonymSemanticModel(dim=1024))
        vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")
        doc_service = DocumentService(
            db=db,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        upload_dir = tmp_path / "uploads"

        pdf_25_path = sample_files["pdf_25_pages"]
        docx_path = sample_files["docx_with_table"]

        # Nạp 2 tài liệu mẫu (PDF 25 trang và DOCX tiếng Việt)
        doc_pdf = doc_service.ingest_upload(
            upload_file=io.BytesIO(pdf_25_path.read_bytes()),
            filename="Quy_che_25_trang.pdf",
            content_type="application/pdf",
            upload_dir=upload_dir,
        )
        doc_docx = doc_service.ingest_upload(
            upload_file=io.BytesIO(docx_path.read_bytes()),
            filename="So_tay_nhan_su.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            upload_dir=upload_dir,
        )

        # [SP3-05.2] Đối soát số lượng Chunk trong ChromaDB khớp tuyệt đối với chunk_count trong DB
        pdf_chroma_count = count_by_document_id(doc_pdf.id, vector_store=vector_store)
        docx_chroma_count = count_by_document_id(doc_docx.id, vector_store=vector_store)

        assert pdf_chroma_count == doc_pdf.chunk_count >= 25
        assert docx_chroma_count == doc_docx.chunk_count >= 1
        assert doc_service.count_document_chunks_in_vector_store(doc_pdf.id) == doc_pdf.chunk_count
        assert vector_store.count() == pdf_chroma_count + docx_chroma_count

        # [SP3-05.1] Xóa toàn bộ vector của tài liệu PDF khỏi ChromaDB bằng delete_by_document_id
        deleted_count = delete_by_document_id(doc_pdf.id, vector_store=vector_store)
        assert deleted_count == pdf_chroma_count

        # Đối soát lại sau khi xóa: tài liệu PDF còn 0 chunk, tài liệu DOCX giữ nguyên
        assert count_by_document_id(doc_pdf.id, vector_store=vector_store) == 0
        assert count_by_document_id(doc_docx.id, vector_store=vector_store) == docx_chroma_count
        assert vector_store.count() == docx_chroma_count
    finally:
        db.close()


def test_sp3_05_3_synonym_queries_and_sprint3_dod_top5_under_1s(
    tmp_path: Path,
    sample_files: Dict[str, Path],
) -> None:
    """
    [SP3-05.3 & Sprint 3 DoD]:
    - Nạp văn bản mẫu tiếng Việt (tệp chính sách 6 trang + tệp PDF 25 trang).
    - Truy vấn bằng câu hỏi đồng nghĩa (không dùng y hệt từ khóa gốc).
    - Kiểm tra kết quả Top-5 trả về chứa đúng nội dung trả lời cùng số trang (page_number)
      chính xác trong thời gian dưới 1 giây (< 1.0s).
    """
    db = _create_db_session(tmp_path)
    try:
        embedding_service = EmbeddingService()
        embedding_service.set_model(VietnameseSynonymSemanticModel(dim=1024))
        vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")
        doc_service = DocumentService(
            db=db,
            embedding_service=embedding_service,
            vector_store=vector_store,
            text_splitter=RecursiveTextSplitter(chunk_size=350, chunk_overlap=50),
        )
        upload_dir = tmp_path / "uploads"

        # 1. Nạp tài liệu chính sách 6 trang và tài liệu PDF 25 trang
        policy_doc = doc_service.ingest_upload(
            upload_file=io.BytesIO(_create_policy_pdf_bytes("Công ty Alpha")),
            filename="Chinh_sach_nhan_su_2026.pdf",
            content_type="application/pdf",
            upload_dir=upload_dir,
        )
        large_pdf_doc = doc_service.ingest_upload(
            upload_file=io.BytesIO(sample_files["pdf_25_pages"].read_bytes()),
            filename="Tai_lieu_25_trang.pdf",
            content_type="application/pdf",
            upload_dir=upload_dir,
        )

        retriever = SemanticRetriever(
            embedding_service=embedding_service,
            vector_store=vector_store,
            min_similarity=0.35,
        )

        # 2. Truy vấn bằng câu hỏi đồng nghĩa về "thời hạn tập sự của kỹ sư mới tuyển"
        # (Văn bản gốc ở Trang 1 dùng cụm "Thời gian thử việc ... tối đa 60 ngày")
        t0 = time.perf_counter()
        results_probation = retriever.retrieve(
            question="Thời hạn tập sự đối với kỹ sư mới tuyển trình độ đại học là bao lâu?",
            top_k=5,
            document_ids=[policy_doc.id],
        )
        elapsed_probation = time.perf_counter() - t0

        assert elapsed_probation < 1.0, f"Thời gian truy xuất vượt quá 1 giây: {elapsed_probation:.3f}s"
        assert len(results_probation) >= 1
        assert results_probation[0].page_number == 1
        assert "60 ngày" in results_probation[0].text
        assert results_probation[0].filename == "Chinh_sach_nhan_su_2026.pdf"

        # 3. Truy vấn bằng câu hỏi đồng nghĩa về "chế độ phép thường niên trọn một năm"
        # (Văn bản gốc ở Trang 2 và Trang 6 dùng cụm "nghỉ hằng năm 12 ngày phép")
        t1 = time.perf_counter()
        results_leave = retrieve(
            question="Nhân viên làm việc trọn một năm có chế độ phép thường niên và ngày nghỉ có lương thế nào?",
            top_k=5,
            document_ids=None,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        elapsed_leave = time.perf_counter() - t1

        # Kiểm tra Sprint 3 Definition of Done: Top-5 trả về trong < 1 giây, kèm số trang chính xác
        assert elapsed_leave < 1.0, f"Thời gian truy xuất vượt quá 1 giây: {elapsed_leave:.3f}s"
        assert 1 <= len(results_leave) <= 5
        returned_pages_for_policy = {
            r.page_number for r in results_leave if r.document_id == str(policy_doc.id)
        }
        assert 2 in returned_pages_for_policy or 6 in returned_pages_for_policy
        assert any("12 ngày" in r.text for r in results_leave)

        # Đảm bảo toàn bộ Top-5 đều có page_number hợp lệ và sắp xếp giảm dần theo similarity_score
        for idx, chunk in enumerate(results_leave):
            assert chunk.page_number is not None and chunk.page_number >= 1
            if idx > 0:
                assert results_leave[idx - 1].similarity_score >= chunk.similarity_score

        assert large_pdf_doc.chunk_count >= 25
    finally:
        db.close()


def test_sp3_05_4_after_document_deletion_queries_return_zero_chunks(
    tmp_path: Path,
) -> None:
    """
    [SP3-05.4] Kiểm thử xác nhận sau khi gọi lệnh xóa tài liệu (delete_document / delete_by_document_id),
    mọi truy vấn tiếp theo không còn lấy ra bất kỳ đoạn văn nào của tài liệu đó.
    """
    db = _create_db_session(tmp_path)
    try:
        embedding_service = EmbeddingService()
        embedding_service.set_model(VietnameseSynonymSemanticModel(dim=1024))
        vector_store = VectorStore(persist_dir=tmp_path / "chroma_db")
        doc_service = DocumentService(
            db=db,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        upload_dir = tmp_path / "uploads"

        # Nạp 2 tài liệu PDF của 2 đơn vị khác nhau
        doc_to_delete = doc_service.ingest_upload(
            upload_file=io.BytesIO(_create_policy_pdf_bytes("Chi nhánh Miền Bắc")),
            filename="Tai_lieu_sap_xoa.pdf",
            content_type="application/pdf",
            upload_dir=upload_dir,
        )
        doc_to_keep = doc_service.ingest_upload(
            upload_file=io.BytesIO(_create_policy_pdf_bytes("Chi nhánh Miền Nam")),
            filename="Tai_lieu_giu_lai.pdf",
            content_type="application/pdf",
            upload_dir=upload_dir,
        )
        deleted_doc_id_str = str(doc_to_delete.id)
        kept_doc_id_str = str(doc_to_keep.id)
        deleted_file_path = Path(doc_to_delete.storage_path)

        # Trước khi xóa: truy vấn trả về các đoạn văn của cả 2 tài liệu
        before_results = retrieve(
            question="Quy định về tăng ca và phụ cấp làm thêm ngoài giờ hành chính?",
            top_k=10,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        before_doc_ids = {r.document_id for r in before_results}
        assert deleted_doc_id_str in before_doc_ids
        assert kept_doc_id_str in before_doc_ids

        # Thực hiện xóa đồng bộ tài liệu doc_to_delete
        was_deleted = doc_service.delete_document(doc_to_delete.id)
        assert was_deleted is True
        assert count_by_document_id(deleted_doc_id_str, vector_store=vector_store) == 0
        assert not deleted_file_path.exists()

        # Sau khi xóa:
        # 1) Truy vấn trên toàn bộ kho tài liệu (document_ids=None) tuyệt đối không còn chunk của tài liệu đã xóa
        after_global_results = retrieve(
            question="Quy định về tăng ca và phụ cấp làm thêm ngoài giờ hành chính?",
            top_k=10,
            document_ids=None,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        assert len(after_global_results) >= 1
        assert all(r.document_id != deleted_doc_id_str for r in after_global_results)
        assert all(r.document_id == kept_doc_id_str for r in after_global_results)

        # 2) Truy vấn chỉ định trực tiếp document_ids=[deleted_doc_id_str] trả về danh sách rỗng []
        after_filtered_results = retrieve(
            question="Quy định về tăng ca và phụ cấp làm thêm ngoài giờ hành chính?",
            top_k=5,
            document_ids=[deleted_doc_id_str],
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        assert after_filtered_results == []
    finally:
        db.close()
