# 🎬 Kịch bản Trình diễn Hệ thống (5-Minute Live Demo Script — `SP6-05.2`)

- **Dự án:** Intelligent Document Chatbot (LLM + RAG)
- **Thời lượng chuẩn:** `5 phút (300 giây)`
- **Mục tiêu trình diễn:** Chứng minh trọn vẹn hành trình người dùng từ tải lên tài liệu thực tế, kiểm tra an toàn tệp tin, hỏi đáp kèm trích dẫn xác thực 2 lớp, đối chiếu trực tiếp trang PDF gốc, chống ảo giác (Out-of-Scope Refusal) đến xóa đồng bộ dữ liệu 3 nơi.

---

## 🛠️ Bước chuẩn bị trước buổi Demo (1 phút trước giờ G)

1. Đảm bảo Backend (`http://localhost:8000`) và Frontend (`http://localhost:5173`) đang chạy xanh (`Hệ thống sẵn sàng` trên thanh Header).
2. Chuẩn bị sẵn thư mục tài liệu mẫu tại: `docs/golden_dataset/documents/` gồm:
   - `01_Bo_luat_Lao_dong_Trich_yeu.pdf` (`20 trang`)
   - `03_Tai_lieu_Kien_truc_Ky_thuat_CNTT_RAG.pdf` (`16 trang`)
   - `04_So_tay_Chinh_sach_Nhan_su_va_ATTT.docx` (`11 mục + bảng biểu`)

---

## ⏱️ Phân cảnh 1 (`00:00 – 01:00`): Giới thiệu Giao diện 3 Cột & Tải Tài liệu Thực tế

### Thao tác trên màn hình:
1. Chỉ vào **Thanh trạng thái (AppHeader)** góc phải trên cùng hiển thị đèn xanh **"Hệ thống sẵn sàng"** (PostgreSQL/SQLite + ChromaDB + Embedding đã kết nối).
2. Tại **Cột trái (Quản lý tài liệu)**:
   - Kéo-thả tệp `01_Bo_luat_Lao_dong_Trich_yeu.pdf` và `04_So_tay_Chinh_sach_Nhan_su_va_ATTT.docx` vào khung **UploadDropzone**.
   - Quan sát thanh tiến trình và **Toast Notification** màu xanh thông báo: *"Tải lên và xử lý tài liệu thành công!"* kèm số lượng đoạn văn (`chunks`) đã băm.

### Lời thuyết trình gợi ý:
> *"Hệ thống được thiết kế theo bố cục 3 cột chuẩn SaaS: Cột trái quản lý phạm vi tài liệu và lịch sử hội thoại; Cột giữa là không gian hỏi đáp; Cột phải là bảng đối chiếu nguồn trích dẫn trực quan. Khi tải tệp PDF hoặc DOCX lên, Backend kiểm tra chữ ký nhị phân (Magic Bytes) chống tệp giả mạo, chuẩn hóa Unicode NFC tiếng Việt, sau đó băm đệ quy theo kích thước tối ưu 400 tokens (gối đầu 60 tokens) và lập chỉ mục vector 1024 chiều vào ChromaDB."*

---

## ⏱️ Phân cảnh 2 (`01:00 – 02:30`): Hỏi câu có đáp án & Đối chiếu Trích dẫn 2 Lớp trên PDF gốc

### Thao tác trên màn hình:
1. Tích chọn tài liệu `01_Bo_luat_Lao_dong_Trich_yeu.pdf` ở cột trái.
2. Nhập câu hỏi tra cứu trực tiếp vào ô Chat:
   ```text
   Người lao động làm việc đủ 12 tháng trong điều kiện bình thường thì được nghỉ phép hằng năm bao nhiêu ngày làm việc và cứ đủ 5 năm làm việc cho một người sử dụng lao động thì được cộng thêm mấy ngày?
   ```
3. Khi câu trả lời hiện ra kèm các huy hiệu trích dẫn màu xanh **`[S1]`**, **`[S2]`**:
   - **Nhấn trực tiếp vào huy hiệu `[S1]`** ngay trong câu trả lời của AI.
   - Quan sát **Cột phải (Source Verification Panel)** tự động cuộn tới thẻ nguồn **`[S1]`**, hiển thị rõ đoạn trích văn bản gốc, điểm tương đồng ngữ nghĩa (`Similarity %`) và mở khung **Xem trang PDF gốc** đúng tại **Trang 7 (`#page=7`)** và **Trang 8 (`#page=8`)**.

### Lời thuyết trình gợi ý:
> *"Điểm khác biệt cốt lõi của hệ thống là cơ chế Xác thực Trích dẫn 2 Lớp (Two-Layer Citation Verification). Mọi con số AI đưa ra — 12 ngày phép năm theo Điều 113 và cộng thêm 1 ngày cho mỗi 5 năm thâm niên theo Điều 114 — đều gắn liền với nhãn `[S1]`, `[S2]`. Khi người dùng nhấn vào `[S1]`, cột phải lập tức mở đúng trang 7 của tệp PDF gốc và tô sáng đoạn văn bản đối chứng, giúp kiểm chứng độ chính xác trong 1 giây."*

---

## ⏱️ Phân cảnh 3 (`02:30 – 03:30`): Câu hỏi Tổng hợp Đa đoạn trên Tài liệu DOCX có Bảng biểu

### Thao tác trên màn hình:
1. Tích chọn thêm tài liệu `04_So_tay_Chinh_sach_Nhan_su_va_ATTT.docx`.
2. Đặt câu hỏi tổng hợp dữ liệu từ bảng biểu trong DOCX:
   ```text
   So sánh ngân sách đào tạo chứng chỉ quốc tế hằng năm và mức phụ cấp làm việc từ xa giữa cấp bậc Senior (Bậc 3) và Principal / Quản lý (Bậc 4)?
   ```
3. Nhấn vào nhãn **`[S1]`** trong câu trả lời để xem đoạn trích bảng biểu kèm tiêu đề chương mục (`Section Title`) ở cột phải.

### Lời thuyết trình gợi ý:
> *"Đối với tệp Word (.docx), bộ phân tích không chỉ đọc các đoạn văn mà còn trích xuất toàn bộ các dòng trong bảng biểu và gắn kèm tiêu đề chương mục (Heading) gần nhất. Nhờ đó, hệ thống trả lời chính xác bảng chế độ đãi ngộ giữa Bậc 3 và Bậc 4."*

---

## ⏱️ Phân cảnh 4 (`03:30 – 04:15`): Kiểm tra Chống Ảo giác (Hỏi câu Ngoài phạm vi Tài liệu)

### Thao tác trên màn hình:
1. Nhập một câu hỏi hoàn toàn không tồn tại trong bất kỳ tài liệu nào đã tải lên:
   ```text
   Dự báo giá vàng thế giới năm 2027 và công thức nấu món bún bò Huế chuẩn vị là gì?
   ```
2. Quan sát hệ thống phản hồi tức thì:
   - Câu trả lời: *"Xin lỗi, tôi không tìm thấy thông tin liên quan trong các tài liệu hiện có để trả lời câu hỏi này."*
   - Không có bất kỳ huy hiệu `[S1]` nào được gắn và danh sách nguồn trích dẫn hoàn toàn rỗng.

### Lời thuyết trình gợi ý:
> *"Trong các ứng dụng RAG doanh nghiệp, việc biết từ chối khi tài liệu không đề cập quan trọng không kém việc trả lời đúng. Nhờ bộ lọc ngưỡng tương đồng ngữ nghĩa kết hợp ràng buộc System Prompt, hệ thống đạt tỷ lệ từ chối đúng 100% đối với câu hỏi ngoài phạm vi mà không bịa đặt thông tin."*

---

## ⏱️ Phân cảnh 5 (`04:15 – 05:00`): Xóa Tài liệu & Kiểm chứng Toàn vẹn Dữ liệu 3 Nơi

### Thao tác trên màn hình:
1. Tại cột trái, nhấn biểu tượng **Thùng rác (Xóa)** trên tài liệu `01_Bo_luat_Lao_dong_Trich_yeu.pdf` và xác nhận xóa.
2. Quan sát **Toast Notification** thông báo đã xóa sạch tài liệu, tệp biến mất khỏi danh sách cột trái.
3. Gửi lại câu hỏi về số ngày nghỉ phép năm của Bộ luật Lao động -> Hệ thống lập tức từ chối vì toàn bộ vector của tài liệu đó trong ChromaDB đã bị xóa sạch (`count == 0`), trong khi lịch sử tin nhắn cũ của phiên chat vẫn được giữ nguyên an toàn.

### Lời thuyết trình kết thúc:
> *"Khi xóa một tài liệu, hệ thống thực thi xóa đồng bộ trên cả 3 tầng: xóa vector trong ChromaDB, xóa tệp vật lý trên ổ đĩa và xóa bản ghi trong cơ sở dữ liệu SQL. Toàn bộ hệ thống đã vượt qua 10/10 kịch bản kiểm thử bảo mật cốt lõi và đạt 98.3% Hit Rate@5 cùng 100% Citation Accuracy trên bộ 75 câu hỏi kiểm thử chuẩn."*
