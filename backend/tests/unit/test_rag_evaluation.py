import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_DIR = PROJECT_ROOT / "docs" / "golden_dataset"
EVAL_JSON_PATH = GOLDEN_DIR / "rag_evaluation_results.json"
EVAL_MD_PATH = GOLDEN_DIR / "RAG_EVALUATION_REPORT.md"


def test_sp6_02_rag_evaluation_and_ab_testing_results() -> None:
    """
    [SP6-02.1 -> SP6-02.4] Kiểm thử kết quả đánh giá định lượng RAG và A/B Testing:
    1. Tệp rag_evaluation_results.json và RAG_EVALUATION_REPORT.md tồn tại đầy đủ.
    2. Chứa đầy đủ 6 cấu hình thử nghiệm A/B Testing (Chunk Size: 300, 400, 500 x Top-K: 3, 5).
    3. Các chỉ số định lượng của cấu hình tối ưu vượt ngưỡng tiêu chuẩn:
       - Hit Rate@K >= 90%
       - Recall@K >= 90%
       - MRR >= 0.85
       - Faithfulness == 100%
       - Answer Relevancy >= 90%
       - Citation Accuracy >= 90%
       - Out-of-Scope Refusal Rate == 100%
    """
    assert EVAL_JSON_PATH.exists(), "Thiếu tệp rag_evaluation_results.json"
    assert EVAL_MD_PATH.exists(), "Thiếu tệp RAG_EVALUATION_REPORT.md"

    data = json.loads(EVAL_JSON_PATH.read_text(encoding="utf-8"))
    ab_results = data["ab_testing_results"]
    assert len(ab_results) == 6

    config_ids = {item["config_id"] for item in ab_results}
    assert config_ids == {
        "CFG-300-K3",
        "CFG-300-K5",
        "CFG-400-K3",
        "CFG-400-K5",
        "CFG-500-K3",
        "CFG-500-K5",
    }

    best = data["best_configuration"]
    assert best["hit_rate_at_k"] >= 0.90
    assert best["recall_at_k"] >= 0.90
    assert best["mrr"] >= 0.85
    assert best["faithfulness"] == 1.0
    assert best["answer_relevancy"] >= 0.90
    assert best["citation_accuracy"] >= 0.90
    assert best["out_of_scope_refusal_rate"] == 1.0
    assert best["hallucinated_citation_rate"] == 0.0

    breakdown = data["best_config_question_breakdown"]
    assert len(breakdown) == 75
