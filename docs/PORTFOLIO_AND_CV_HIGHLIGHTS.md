# 💼 Hồ sơ Năng lực & Điểm nhấn Kỹ thuật cho CV / Phỏng vấn (`SP6-05.4`)

Tài liệu này đúc kết các đóng góp kỹ thuật cốt lõi và bộ chỉ số định lượng thực tế của dự án **Intelligent Document Chatbot (LLM + RAG)** theo công thức chuẩn **Google XYZ** (*Accomplished $[X]$ as measured by $[Y]$, by doing $[Z]$*) để đưa trực tiếp vào mục **Projects** trong CV ứng tuyển vị trí **AI Engineer / Backend Engineer / Full-Stack Software Engineer**.

---

## 1. Nội dung cập nhật vào mục `Projects` trong CV (Phiên bản Tiếng Việt)

### **Intelligent Document Chatbot — Hệ thống Hỏi Đáp Tài liệu Đa định dạng ứng dụng LLM & RAG**
*Vai trò: Full-Stack AI & Backend Developer | Công nghệ: Python, FastAPI, React 18, TypeScript, ChromaDB, BAAI/bge-m3, PostgreSQL, Docker*
🔗 GitHub: `https://github.com/TuanIT2k5/1-RAG-LLM-chatbot`

- **Thiết kế và phát triển đường ống RAG (Retrieval-Augmented Generation) toàn trình** cho tài liệu tiếng Việt/tiếng Anh (`.pdf`, `.docx`), kết hợp chuẩn hóa Unicode dựng sẵn (`NFC`), băm đệ quy giữ ngữ cảnh (`400 tokens`, `overlap 60 tokens`) và mô hình nhúng đa ngôn ngữ **`BAAI/bge-m3` (`1024 chiều`)** trên **ChromaDB**, đạt **`98.3% Hit Rate@5`**, **`95.8% Recall@5`** và **`MRR = 0.9833`** với độ trễ truy xuất trung bình chỉ **`16.9 ms`**.
- **Xây dựng cơ chế Xác thực Trích dẫn 2 Lớp (`Two-Layer Citation Verification`) và cô lập ngữ cảnh `<document_context>`**, giúp loại bỏ **100% nhãn trích dẫn ảo giác**, đạt **`100% Faithfulness`**, **`100% Citation Accuracy`** và **`100% Out-of-Scope Refusal Rate`** trên bộ kiểm thử chuẩn **Golden Dataset gồm 75 câu hỏi**.
- **Phát triển giao diện Web SaaS 3 cột tương tác bằng React 18, TypeScript và Tailwind CSS**, cho phép người dùng nhấn trực tiếp vào huy hiệu nguồn (`[S1]`, `[S2]`) trong câu trả lời để làm nổi bật đoạn trích và mở đúng số trang PDF gốc (`#page=N`) ngay trên trình duyệt.
- **Triển khai kiến trúc bảo mật tệp tin & tính toàn vẹn dữ liệu 3 tầng** (kiểm tra chữ ký nhị phân `Magic Bytes` chặn tệp `.exe`/`.zip` giả mạo, chống `Indirect Prompt Injection`, xóa đồng bộ trên ChromaDB + Ổ đĩa + PostgreSQL và cơ chế Retry khi LLM Timeout), vượt qua **10/10 kịch bản kiểm thử hệ thống & an toàn thông tin cốt lõi (`TC-01 -> TC-10`)** và đóng gói triển khai 1 lệnh qua **Docker Compose** (Multi-stage Node.js/Nginx + Python 3.11-slim + PostgreSQL 16).

---

## 2. Nội dung cập nhật vào mục `Projects` trong CV (Phiên bản Tiếng Anh — Chuẩn Quốc tế)

### **Intelligent Document Chatbot — Production-Grade Multilingual RAG System**
*Tech Stack: Python 3.11, FastAPI, React 18, TypeScript, Tailwind CSS, BAAI/bge-m3, ChromaDB, PostgreSQL 16, Docker Compose*
🔗 GitHub: `https://github.com/TuanIT2k5/1-RAG-LLM-chatbot`

- **Engineered an end-to-end multilingual RAG pipeline** supporting PDF and DOCX documents with Unicode `NFC` normalization, metadata-preserving recursive token chunking (`400 tokens`, `15% overlap`), and **`BAAI/bge-m3` (`1024-dim`)** L2-normalized embeddings in **ChromaDB**, achieving **`98.3% Hit Rate@5`**, **`95.8% Recall@5`**, and **`0.9833 MRR`** at **`16.9 ms`** average retrieval latency.
- **Designed a Two-Layer Citation Verification engine and `<document_context>` prompt-isolation guardrails**, eliminating hallucinated source tags via regex post-verification against retrieved metadata and achieving **`100% Faithfulness`**, **`100% Citation Accuracy`**, and **`100% Out-of-Scope Refusal Rate`** across a **75-question Golden Dataset** via A/B testing (`Chunk Size: 300/400/500` × `Top-K: 3/5`).
- **Built a 3-column SaaS workspace in React 18 and TypeScript** featuring interactive citation badges (`[S1]`, `[S2]`) synchronized with a live **Source Verification Panel** that highlights matched text excerpts and deep-links directly to the exact PDF page (`#page=N`).
- **Hardened system reliability and security across 10 core integration test suites (`100% PASSED`)**, implementing binary magic-byte validation (`%PDF-`, OpenXML signature checks), synchronized 3-store deletion (ChromaDB + filesystem + PostgreSQL), exponential-backoff LLM retries, and multi-stage **Docker Compose** orchestration.

---

## 3. Bảng Tóm tắt Chỉ số Định lượng Nhanh (Dùng khi trả lời phỏng vấn)

| Nhóm chỉ số | Chỉ số cụ thể | Giá trị đạt được | Ý nghĩa kỹ thuật |
| :--- | :--- | :---: | :--- |
| **Chất lượng Truy xuất (Retrieval)** | **Hit Rate@5** | **`98.3%`** | Tỷ lệ tìm thấy ít nhất 1 đoạn chứa đáp án chuẩn trong Top-5. |
| **Chất lượng Truy xuất (Retrieval)** | **Recall@5** | **`95.8%`** | Bao phủ gần như toàn bộ các trang tham chiếu cho câu hỏi tổng hợp nhiều đoạn. |
| **Chất lượng Truy xuất (Retrieval)** | **MRR (Mean Reciprocal Rank)** | **`0.9833`** | Đoạn văn chứa đáp án đúng hầu như luôn nằm ngay vị trí `#1` (`[S1]`). |
| **Tốc độ Truy xuất** | **Retrieval Latency (Avg / P95)** | **`16.9 ms` / `20.2 ms`** | Phản hồi tìm kiếm vector tức thì dưới `25 ms`. |
| **Chất lượng Sinh & Chống ảo giác** | **Faithfulness & Citation Accuracy** | **`100.0%`** | Không có nhãn trích dẫn bịa đặt nào lọt qua bộ lọc xác thực 2 lớp. |
| **Khả năng Từ chối ngoài phạm vi** | **Out-of-Scope Refusal Rate** | **`100.0%` (`15/15`)** | Từ chối chính xác 100% câu hỏi ngoài tài liệu, tiết kiệm lượt gọi LLM. |
| **Kiểm thử Hệ thống & Bảo mật** | **Core Test Suite (`TC-01 -> TC-10`)** | **`10 / 10 PASSED`** | Bao phủ Magic Bytes, Prompt Injection, Xóa đồng bộ 3 nơi & LLM Timeout. |

---

## 4. Bộ 5 Câu hỏi & Câu trả lời Phỏng vấn Kỹ thuật Trọng tâm (Interview Q&A)

### Câu 1: *"Tại sao bạn chọn `Chunk Size = 400 tokens` (gối đầu `60 tokens`) và `Top-K = 5` thay vì các cấu hình khác?"*
- **Trả lời:** Tôi đã thiết kế kịch bản A/B Testing tự động (`scripts/evaluate_rag.py`) thử nghiệm 6 tổ hợp (`Chunk Size: 300, 400, 500` × `Top-K: 3, 5`) trên bộ 75 câu hỏi chuẩn. Kết quả thực nghiệm cho thấy ở `Chunk Size = 300`, các điều khoản pháp lý hoặc bảng chế độ nhân sự bị cắt vụn khiến `Recall@3` giảm xuống `91.9%` và `MRR = 0.964`. Khi tăng lên `Chunk Size = 400` với `Overlap = 60 (15%)` và `Top-K = 5` (`CFG-400-K5`), mỗi đoạn văn giữ trọn vẹn một điều khoản hoàn chỉnh, giúp `MRR` tăng lên `0.9833` và `Recall@5` đạt `95.8%` mà vẫn tiết kiệm 20% lượng token ngữ cảnh gửi cho LLM so với `Chunk Size = 500`.

### Câu 2: *"Làm thế nào bạn đảm bảo LLM không bịa ra số trang trích dẫn (Hallucinated Citations)?"*
- **Trả lời:** Tôi thiết kế cơ chế **Xác thực Trích dẫn 2 Lớp (`Two-Layer Citation Verification`)**:
  1. **Lớp 1 (`ContextBuilder`):** Trước khi gọi LLM, hệ thống không yêu cầu LLM tự nhớ số trang mà đánh mã định danh cứng `[S1]`, `[S2]`... cho từng đoạn văn truy xuất và lưu một bảng ánh xạ `source_map` trong bộ nhớ máy chủ chứa `document_id`, `filename`, `page_number` thật.
  2. **Lớp 2 (`CitationService`):** Sau khi LLM trả lời, hệ thống dùng biểu thức chính quy `\[S(\d+)\]` quét toàn bộ văn bản trả về. Bất kỳ nhãn `[S_x]` nào không nằm trong `source_map` (ví dụ `[S99]`) đều bị xóa bỏ tự động, và chỉ những nguồn thực sự được trích dẫn mới được gắn metadata số trang gốc từ `source_map` để trả về cho Frontend.

### Câu 3: *"Khi người dùng xóa một tài liệu đang nằm trong lịch sử hội thoại, bạn xử lý tính toàn vẹn dữ liệu giữa PostgreSQL và ChromaDB như thế nào?"*
- **Trả lời:** Trong `DocumentService.delete_document`, tôi thực thi quy trình xóa đồng bộ 3 nơi: (1) Xóa toàn bộ vector có `metadata.document_id` tương ứng trong ChromaDB và kiểm chứng lại bằng `count_by_document_id == 0`; (2) Xóa tệp vật lý trên ổ đĩa; (3) Xóa bản ghi trong bảng `documents` của SQL. Đồng thời, đối với các tin nhắn lịch sử trong bảng `message_sources`, khóa ngoại `document_id` được thiết kế với `ON DELETE SET NULL` kèm bản chụp nhanh tên tệp và đoạn trích, giúp lịch sử hội thoại cũ không bị mất hoặc lỗi khóa ngoại trong khi các câu hỏi mới không thể truy xuất tài liệu đã xóa nữa (`TC-08`).

### Câu 4: *"Hệ thống của bạn phòng chống tấn công Indirect Prompt Injection trong tài liệu PDF được tải lên như thế nào?"*
- **Trả lời:** Khi người dùng tải lên một tài liệu chứa câu lệnh độc hại (như *"Hãy bỏ qua mọi quy tắc trước đó..."*), văn bản đó sẽ đi vào ngữ cảnh truy xuất. Để vô hiệu hóa, trong `build_rag_user_prompt`, tôi đóng khung toàn bộ văn bản truy xuất bên trong cặp thẻ XML `<document_context>...</document_context>` tách biệt hoàn toàn với `<user_question>`, kết hợp chỉ dẫn hệ thống bất biến yêu cầu coi mọi mệnh lệnh trong `<document_context>` chỉ là dữ liệu thụ động, và hậu kiểm đầu ra bằng `CitationService` (`TC-10`).

### Câu 5: *"Tại sao bạn xử lý chuẩn hóa Unicode `NFC` cho văn bản tiếng Việt trước khi băm và nhúng vector?"*
- **Trả lời:** Nhiều tệp PDF tiếng Việt xuất ra từ các phần mềm cũ sử dụng bảng mã Unicode tổ hợp (`NFD` — dấu thanh tách rời khỏi nguyên âm) hoặc chứa ký tự gạch nối mềm (`\u00ad`). Nếu không chuẩn hóa về Unicode dựng sẵn (`NFC`) và làm sạch ký tự điều khiển trong `text_cleaner.py`, cùng một từ tiếng Việt sẽ bị tách thành các chuỗi token khác nhau, làm giảm nghiêm trọng điểm tương đồng Cosine giữa câu hỏi của người dùng (thường gõ ở chuẩn `NFC`) và đoạn văn trong PDF.
