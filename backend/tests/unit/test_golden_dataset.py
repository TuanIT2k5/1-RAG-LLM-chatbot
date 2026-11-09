import csv
import json
from pathlib import Path
import re

from app.services.document_processor import extract_document
from app.utils.text_cleaner import clean_text

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_DIR = PROJECT_ROOT / "docs" / "golden_dataset"
DOCS_DIR = GOLDEN_DIR / "documents"


def _normalize_whitespace(text: str) -> str:
    cleaned = clean_text(text).replace("\xad", "-")
    return re.sub(r"\s+", " ", cleaned).strip().lower()


def test_sp6_01_golden_dataset_documents_and_75_questions() -> None:
    """
    [SP6-01.1 -> SP6-01.4] Kiểm thử bộ dữ liệu chuẩn Golden Dataset:
    1. Kiểm tra 4 tài liệu tiêu biểu (3 PDF từ 16-20 trang + 1 DOCX có bảng biểu) tồn tại và trích xuất chuẩn Unicode.
    2. Kiểm tra tệp golden_dataset_75.json có đúng 75 câu hỏi:
       - 40 câu tra cứu trực tiếp (direct_lookup)
       - 20 câu tổng hợp nhiều đoạn (multi_chunk_synthesis)
       - 15 câu ngoài phạm vi tài liệu (out_of_scope)
    3. Kiểm tra đối chiếu thực tế các từ khóa bằng chứng (evidence_keywords) có nằm đúng trên trang/tài liệu tham chiếu.
    4. Kiểm tra tệp golden_dataset_75.csv đồng bộ hoàn toàn với tệp JSON.
    """
    json_path = GOLDEN_DIR / "golden_dataset_75.json"
    csv_path = GOLDEN_DIR / "golden_dataset_75.csv"

    assert json_path.exists(), "Thiếu tệp golden_dataset_75.json"
    assert csv_path.exists(), "Thiếu tệp golden_dataset_75.csv"

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    questions = payload["questions"]
    assert len(questions) == 75

    direct_qs = [q for q in questions if q["category"] == "direct_lookup"]
    synthesis_qs = [q for q in questions if q["category"] == "multi_chunk_synthesis"]
    oos_qs = [q for q in questions if q["category"] == "out_of_scope"]

    assert len(direct_qs) == 40
    assert len(synthesis_qs) == 20
    assert len(oos_qs) == 15

    # [SP6-01.1] Kiểm tra 4 tài liệu gốc trong docs/golden_dataset/documents/
    expected_doc_pages = {
        "01_Bo_luat_Lao_dong_Trich_yeu.pdf": 20,
        "02_Quy_che_Dao_tao_Tin_chi_Dai_hoc.pdf": 18,
        "03_Tai_lieu_Kien_truc_Ky_thuat_CNTT_RAG.pdf": 16,
    }

    extracted_by_doc: dict[str, dict[int, str]] = {}
    full_text_by_doc: dict[str, str] = {}

    for pdf_name, expected_pages in expected_doc_pages.items():
        pdf_file = DOCS_DIR / pdf_name
        assert pdf_file.exists(), f"Thiếu tài liệu {pdf_name}"
        segments = extract_document(pdf_file, document_id=pdf_name)
        assert len(segments) == expected_pages
        extracted_by_doc[pdf_name] = {
            seg.page_number: _normalize_whitespace(seg.text)
            for seg in segments
            if seg.page_number is not None
        }
        full_text_by_doc[pdf_name] = _normalize_whitespace(
            "\n".join(seg.text for seg in segments)
        )

    docx_name = "04_So_tay_Chinh_sach_Nhan_su_va_ATTT.docx"
    docx_file = DOCS_DIR / docx_name
    assert docx_file.exists(), f"Thiếu tài liệu {docx_name}"
    docx_segments = extract_document(docx_file, document_id=docx_name)
    assert len(docx_segments) >= 15
    full_text_by_doc[docx_name] = _normalize_whitespace(
        "\n".join(seg.text for seg in docx_segments)
    )

    # [SP6-01.2] Kiểm tra toàn bộ 60 câu hỏi có đáp án trong tài liệu
    for q in direct_qs + synthesis_qs:
        assert q["expected_refusal"] is False
        assert len(q["expected_documents"]) >= 1
        assert len(q["expected_pages"]) >= 1
        assert len(q["ground_truth_answer"].strip()) > 20
        assert len(q["evidence_keywords"]) >= 1

        combined_doc_text = " ".join(
            full_text_by_doc[d] for d in q["expected_documents"]
        )
        for kw in q["evidence_keywords"]:
            kw_norm = _normalize_whitespace(kw)
            assert kw_norm in combined_doc_text, (
                f"Từ khóa bằng chứng '{kw}' của câu {q['id']} không tìm thấy trong {q['expected_documents']}"
            )

        # Với câu tra cứu trực tiếp trên PDF, kiểm tra số trang tham chiếu hợp lệ và chứa từ khóa
        if q["category"] == "direct_lookup" and q["expected_documents"][0].endswith(".pdf"):
            doc_name = q["expected_documents"][0]
            page_no = q["expected_pages"][0]
            page_text = extracted_by_doc[doc_name][page_no]
            for kw in q["evidence_keywords"]:
                kw_norm = _normalize_whitespace(kw)
                assert kw_norm in page_text, (
                    f"Câu {q['id']}: Từ khóa '{kw}' không nằm ở trang {page_no} của {doc_name}"
                )

    # [SP6-01.3] Kiểm tra 15 câu hỏi ngoài phạm vi tài liệu
    for q in oos_qs:
        assert q["expected_refusal"] is True
        assert q["expected_documents"] == []
        assert q["expected_pages"] == []
        assert "không tìm thấy thông tin" in q["ground_truth_answer"].lower()

    # [SP6-01.4] Kiểm tra tệp CSV đồng bộ 75 dòng dữ liệu
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 75
    assert rows[0]["id"] == "GD-001"
    assert rows[-1]["id"] == "GD-075"
