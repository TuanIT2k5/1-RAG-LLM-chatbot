# Bộ Dữ Liệu Kiểm Thử Chuẩn RAG (Golden Dataset — SP6-01)

Bộ dữ liệu kiểm thử chuẩn (**Golden Dataset**) gồm **75 câu hỏi** kèm đáp án tham chiếu (`ground_truth_answer`), tên tệp nguồn (`expected_documents`), số trang tham chiếu (`expected_pages`) và từ khóa bằng chứng (`evidence_keywords`) dùng để đánh giá định lượng hệ thống **Intelligent Document Chatbot (LLM + RAG)**.

---

## 1. Danh mục 4 Tài liệu Kiểm thử Chuẩn (`docs/golden_dataset/documents/`)

| STT | Tên tệp tài liệu | Định dạng | Quy mô | Lĩnh vực nội dung |
| :-- | :--- | :---: | :---: | :--- |
| 1 | `01_Bo_luat_Lao_dong_Trich_yeu.pdf` | PDF | 20 trang | Bộ luật Lao động 2019 (Hợp đồng, Thử việc, Tiền lương, Làm thêm giờ, Nghỉ phép, Kỷ luật, Thai sản, BHXH) |
| 2 | `02_Quy_che_Dao_tao_Tin_chi_Dai_hoc.pdf` | PDF | 18 trang | Quy chế Đào tạo Đại học theo Hệ thống Tín chỉ (Khối lượng học tập, Thang điểm, Cảnh báo học vụ, Bảo lưu, Tốt nghiệp) |
| 3 | `03_Tai_lieu_Kien_truc_Ky_thuat_CNTT_RAG.pdf` | PDF | 16 trang | Đặc tả Kiến trúc Kỹ thuật CNTT & Hệ thống RAG (SLA 99.95%, PostgreSQL, ChromaDB HNSW, Bảo mật, RPO/RTO, CI/CD) |
| 4 | `04_So_tay_Chinh_sach_Nhan_su_va_ATTT.docx` | DOCX | 11 mục + Bảng | Sổ tay Chính sách Nhân sự, Hybrid Work, Phụ cấp, Đào tạo & An toàn Thông tin Nội bộ |

---

## 2. Phân bổ 75 Câu hỏi Kiểm thử (`golden_dataset_75.json` & `golden_dataset_75.csv`)

| Phân loại (`category`) | Mã câu hỏi | Số lượng | Mục đích đánh giá |
| :--- | :---: | :---: | :--- |
| **`direct_lookup`** (Tra cứu trực tiếp) | `GD-001` $\rightarrow$ `GD-040` | **40 câu** | Đánh giá độ chính xác truy xuất (`Hit Rate@K`, `MRR`) và trích dẫn đúng số trang/đoạn trên thông tin đơn lẻ. |
| **`multi_chunk_synthesis`** (Tổng hợp nhiều đoạn) | `GD-041` $\rightarrow$ `GD-060` | **20 câu** | Đánh giá khả năng kết hợp thông tin từ nhiều trang/đoạn khác nhau hoặc liên tài liệu (`Recall@K`, `Faithfulness`, `Answer Relevancy`). |
| **`out_of_scope`** (Ngoài phạm vi tài liệu) | `GD-061` $\rightarrow$ `GD-075` | **15 câu** | Kiểm tra khả năng chống ảo giác (Hallucination): bắt buộc từ chối lịch sự và trả về mảng `sources = []`. |
| **TỔNG CỘNG** | `GD-001` $\rightarrow$ `GD-075` | **75 câu** | Phục vụ chạy tự động kịch bản đánh giá RAG (`SP6-02`). |

---

## 3. Cách tạo lại hoặc cập nhật Golden Dataset

Chạy lệnh sau từ thư mục gốc của dự án:

```powershell
.\backend\venv\Scripts\python.exe scripts/generate_golden_dataset.py
```
