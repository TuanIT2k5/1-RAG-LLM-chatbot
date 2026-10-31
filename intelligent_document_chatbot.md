# Intelligent Document Chatbot — Tài liệu Tổng quan & Thiết kế Kỹ thuật Toàn diện

> **Loại tài liệu:** Project Master Overview & Technical Blueprint (SRS + Architecture + UI/UX + Roadmap)  
> **Phiên bản:** 2.0  
> **Ngày cập nhật:** 01/11/2026  
> **Kiến trúc cốt lõi:** Large Language Model (LLM) + Retrieval-Augmented Generation (RAG)  
> **Mô hình triển khai:** Full-stack Web Application (Modular Monolith Backend + SPA Frontend)

---

## MỤC LỤC
1. [Giới thiệu & Bài toán cần giải quyết](#1-giới-thiệu--bài-toán-cần-giải-quyết)
2. [Phạm vi sản phẩm & Yêu cầu hệ thống (SRS)](#2-phạm-vi-sản-phẩm--yêu-cầu-hệ-thống-srs)
3. [Kiến trúc hệ thống & Công nghệ sử dụng (Tech Stack)](#3-kiến-trúc-hệ-thống--công-nghệ-sử-dụng-tech-stack)
4. [Hệ thống thiết kế giao diện (UI/UX Design System)](#4-hệ-thống-thiết-kế-giao-diện-uiux-design-system)
5. [Cấu trúc thư mục dự án (Monorepo Directory Structure)](#5-cấu-trúc-thư-mục-dự-án-monorepo-directory-structure)
6. [Thiết kế chi tiết Luồng xử lý RAG (RAG Pipeline)](#6-thiết-kế-chi-tiết-luồng-xử-lý-rag-rag-pipeline)
7. [Thiết kế Cơ sở dữ liệu & Đặc tả RESTful API](#7-thiết-kế-cơ-sở-dữ-liệu--đặc-tả-restful-api)
8. [Bảo mật, Kiểm thử & Đánh giá chất lượng RAG](#8-bảo-mật-kiểm-thử--đánh-giá-chất-lượng-rag)
9. [Lộ trình triển khai 6 Sprint (6 Tuần)](#9-lộ-trình-triển-khai-6-sprint-6-tuần)
10. [Cấu hình môi trường & Hướng dẫn khởi chạy](#10-cấu-hình-môi-trường--hướng-dẫn-khởi-chạy)

---

## 1. Giới thiệu & Bài toán cần giải quyết

### 1.1. Mô tả sản phẩm
**Intelligent Document Chatbot** là ứng dụng web cho phép người dùng tải lên các tài liệu văn bản (`PDF`, `DOCX`), đặt câu hỏi bằng ngôn ngữ tự nhiên (tiếng Việt hoặc tiếng Anh) và nhận được câu trả lời chính xác dựa trên nội dung tài liệu đó. Mọi câu trả lời do AI sinh ra đều đi kèm **trích dẫn nguồn xác thực** (tên tệp, số trang PDF hoặc thứ tự đoạn văn DOCX, kèm đoạn văn bản gốc làm bằng chứng).

### 1.2. Bài toán thực tế
* **Tra cứu thủ công tốn thời gian:** Việc đọc và tìm kiếm thông tin trong các tài liệu dài hàng chục đến hàng trăm trang (luật, quy chế, giáo trình, tài liệu kỹ thuật) rất mất thời gian.
* **Hạn chế của tìm kiếm từ khóa (`Ctrl + F`):** Tìm kiếm truyền thống bỏ sót thông tin khi người dùng đặt câu hỏi bằng từ đồng nghĩa hoặc cách diễn đạt khác với văn bản gốc.
* **Rủi ro ảo giác (Hallucination) của LLM thuần túy:** Nếu hỏi trực tiếp các mô hình ngôn ngữ lớn mà không cung cấp tài liệu, mô hình dễ tự suy diễn thông tin sai lệch hoặc dùng dữ liệu cũ.
* **Nhu cầu kiểm chứng nguồn:** Người dùng cần biết chính xác câu trả lời được lấy từ tài liệu nào, trang bao nhiêu để đối chiếu và tin tưởng.

---

## 2. Phạm vi sản phẩm & Yêu cầu hệ thống (SRS)

### 2.1. Danh sách Yêu cầu Chức năng (Functional Requirements)

| Mã YC | Tên chức năng | Mô tả chi tiết | Ưu tiên |
| :--- | :--- | :--- | :--- |
| **FR-01** | Tải lên tài liệu | Hỗ trợ tải lên tệp `.pdf` và `.docx`; kiểm tra định dạng thực tế (MIME type) và giới hạn dung lượng tối đa `20MB/tệp`. | **Must (MVP)** |
| **FR-02** | Trích xuất văn bản | Bóc tách toàn bộ văn bản từ PDF/DOCX; bảo toàn chính xác số trang (`page_number`) với PDF và thứ tự đoạn (`paragraph_index`) với DOCX. | **Must (MVP)** |
| **FR-03** | Phân mảnh văn bản | Chia văn bản thành các đoạn nhỏ (`Chunks`) có độ chồng lấp (`overlap`) để không làm đứt gãy mạch ngữ nghĩa giữa các đoạn. | **Must (MVP)** |
| **FR-04** | Vector hóa & Lưu trữ | Chuyển đổi từng Chunk thành vector số học bằng mô hình đa ngôn ngữ và lưu trữ bền vững trong `ChromaDB` kèm metadata. | **Must (MVP)** |
| **FR-05** | Quản lý tài liệu | Hiển thị danh sách tài liệu, kích thước, ngày tải, trạng thái xử lý (`processing`, `processed`, `failed`) và xóa đồng bộ tài liệu. | **Must (MVP)** |
| **FR-06** | Truy xuất ngữ nghĩa | Tìm kiếm `Top-K` đoạn văn bản có độ tương đồng ngữ nghĩa cao nhất với câu hỏi theo khoảng cách Cosine. | **Must (MVP)** |
| **FR-07** | Sinh câu trả lời RAG | Tổng hợp câu trả lời bám sát hoàn toàn vào ngữ cảnh truy xuất được; từ chối trả lời lịch sự nếu tài liệu không đề cập. | **Must (MVP)** |
| **FR-08** | Trích dẫn nguồn xác thực | Gắn nhãn `[S1]`, `[S2]` trong câu trả lời và đối chiếu ở Backend để hiển thị chính xác tên tệp, số trang PDF và đoạn văn gốc. | **Must (MVP)** |
| **FR-09** | Lịch sử hội thoại | Tạo phiên trò chuyện mới, lưu trữ và tải lại toàn bộ lịch sử tin nhắn cùng nguồn trích dẫn từ `PostgreSQL`. | **Should** |
| **FR-10** | Lọc phạm vi tài liệu | Cho phép người dùng tích chọn hỏi đáp trên một tài liệu cụ thể hoặc kết hợp nhiều tài liệu cùng lúc. | **Should** |

### 2.2. Danh sách Yêu cầu Phi chức năng (Non-Functional Requirements)

| Mã YC | Nhóm yêu cầu | Tiêu chuẩn chất lượng cần đạt |
| :--- | :--- | :--- |
| **NFR-01** | Độ trung thực (Faithfulness) | Tuyệt đối không để LLM tự bịa tên tệp hoặc số trang; mọi trích dẫn hiển thị trên UI phải được Backend xác thực từ metadata thật. |
| **NFR-02** | Hiệu năng phản hồi | Thời gian tìm kiếm vector dưới `1 giây`; tổng thời gian trả lời thông thường từ `3 – 8 giây` tùy độ dài ngữ cảnh. |
| **NFR-03** | Khả năng chịu lỗi | Tệp tải lên bị hỏng, rỗng hoặc lỗi kết nối LLM không làm sập hệ thống; phải trả về mã lỗi và thông báo tiếng Việt rõ ràng. |
| **NFR-04** | Bảo mật & An toàn AI | Lưu tệp bằng tên `UUID`, ẩn `API Key` ở biến môi trường máy chủ và cô lập nội dung tài liệu chống tấn công **Prompt Injection**. |
| **NFR-05** | Khả năng mở rộng | Thiết kế theo kiến trúc **Modular Monolith**, dễ dàng chuyển đổi giữa `Gemini API`, `OpenAI API` và mô hình chạy cục bộ (`Ollama`). |
| **NFR-06** | Ngôn ngữ hỗ trợ | Xử lý chuẩn xác bảng mã Unicode tiếng Việt dựng sẵn (`NFC`) và tiếng Anh ở mọi khâu. |

---

## 3. Kiến trúc hệ thống & Công nghệ sử dụng (Tech Stack)

### 3.1. Sơ đồ kiến trúc tổng thể

```text
                                   [ NGƯỜI DÙNG (USER) ]
                                             |
                                             v
                   +---------------------------------------------------+
                   |      FRONTEND: React 18 + TypeScript + Vite       |
                   |   Tailwind CSS + shadcn/ui (Bố cục SaaS 3 Cột)    |
                   +---------------------------------------------------+
                                             |
                                   HTTP REST API (JSON)
                                             |
                                             v
                   +---------------------------------------------------+
                   |         BACKEND: Python 3.11 + FastAPI            |
                   +---------------------------------------------------+
                               |                           |
         +---------------------+                           +---------------------+
         | (1) LUỒNG NẠP TÀI LIỆU                          | (2) LUỒNG HỎI ĐÁP RAG
         v (Indexing Pipeline)                             v (Retrieval & Generation)
+--------------------------+                      +--------------------------+
| Document Validator       |                      | Query Embedding          |
| (Kiểm tra PDF/DOCX <20MB)|                      | (Mô hình BAAI/bge-m3)    |
+--------------------------+                      +--------------------------+
         |                                                 |
         v                                                 v
+--------------------------+                      +--------------------------+
| Document Processor       |                      | Semantic Retriever       |
| (PyMuPDF & python-docx)  |                      | (Tìm kiếm Cosine Top-K)  |
+--------------------------+                      +--------------------------+
         |                                                 |
         v                                                 v
+--------------------------+                      +--------------------------+
| Text Cleaner & Splitter  |                      | Context Builder          |
| (Chunking + Overlap)     |                      | (Gán nhãn [S1], [S2]...) |
+--------------------------+                      +--------------------------+
         |                                                 |
         v                                                 v
+--------------------------+                      +--------------------------+
| Embedding Service        |                      | LLM Service              |
| (BAAI/bge-m3 1024-dim)   |                      | (Gemini / OpenAI /Ollama)|
+--------------------------+                      +--------------------------+
         |                                                 |
         +--------------------+     +----------------------+
                              |     |
                              v     v
                   +---------------------------+           +--------------------------+
                   |   VECTOR DB: ChromaDB     |           | Citation Service         |
                   | (Lưu Chunks + Metadata)   |           | (Đối chiếu nguồn thật)   |
                   +---------------------------+           +--------------------------+
                                                                   |
                                                                   v
                   +---------------------------------------------------+
                   |      RELATIONAL DB: PostgreSQL + SQLAlchemy       |
                   | (Users, Documents, Conversations, Messages, Refs) |
                   +---------------------------------------------------+
```

### 3.2. Bảng Công nghệ chi tiết (Tech Stack)

| Phân hệ | Thành phần | Công nghệ / Thư viện | Vai trò trong dự án |
| :--- | :--- | :--- | :--- |
| **Frontend** | Core Framework | **React 18 + TypeScript** | Xây dựng giao diện SPA hướng thành phần, kiểm soát kiểu dữ liệu chặt chẽ. |
| | Build Tool | **Vite** | Khởi tạo và đóng gói ứng dụng Frontend tốc độ cao. |
| | Styling & UI | **Tailwind CSS + shadcn/ui** | Thiết kế giao diện chuẩn Modern SaaS, đồng nhất bảng màu và khoảng cách. |
| | State & Fetching | **TanStack Query + Zustand** | Quản lý trạng thái bất đồng bộ khi gọi API và trạng thái giao diện 3 cột. |
| | Icons & Markdown | **Lucide React + react-markdown** | Hiển thị bộ biểu tượng tối giản và render câu trả lời định dạng Markdown. |
| **Backend** | Language & API | **Python 3.11+ & FastAPI** | Xây dựng RESTful API hiệu năng cao, tự động sinh tài liệu Swagger UI. |
| | Validation | **Pydantic v2 + pydantic-settings** | Kiểm tra dữ liệu Request/Response và quản lý cấu hình biến môi trường `.env`. |
| | Document Parsing | **PyMuPDF (`fitz`) & `python-docx`** | Trích xuất văn bản thô kèm số trang PDF và thứ tự đoạn/bảng biểu DOCX. |
| **AI / RAG** | Embedding Model | **`BAAI/bge-m3` (`sentence-transformers`)** | Vector hóa văn bản đa ngôn ngữ (hỗ trợ tiếng Việt rất tốt) ra vector `1024` chiều. |
| | Vector Database | **ChromaDB (`PersistentClient`)** | Lưu trữ vector bền vững trên ổ cứng và tìm kiếm tương đồng Cosine. |
| | LLM Provider | **Gemini API / OpenAI API / Ollama** | Tổng hợp câu trả lời từ ngữ cảnh truy xuất và gắn mã nguồn `[S1]`, `[S2]`. |
| **Database** | Relational DB | **PostgreSQL 16 + SQLAlchemy + Alembic** | Lưu trữ dữ liệu nghiệp vụ, lịch sử hội thoại và quản lý phiên bản schema. |
| **DevOps & QA** | Testing & Deploy | **Pytest, Vitest, Docker Compose** | Kiểm thử đơn vị, kiểm thử tích hợp và đóng gói chạy toàn hệ thống bằng 1 lệnh. |

---

## 4. Hệ thống thiết kế giao diện (UI/UX Design System)

### 4.1. Phong cách thiết kế (Design Direction)
Giao diện được thiết kế theo phong cách **Modern SaaS Workspace** (tương tự Notion, Linear, ChatGPT): ưu tiên không gian đọc thoáng đãng, phân cấp thị giác rõ ràng và hiển thị minh bạch trạng thái xử lý tài liệu.

### 4.2. Bảng màu tiêu chuẩn (Color Palette)

| Vai trò màu | Tên biến (Tailwind / CSS) | Mã HEX | Ứng dụng cụ thể trên giao diện |
| :--- | :--- | :--- | :--- |
| **Primary** | `primary` | `#2563EB` | Nút hành động chính (Tải tệp, Gửi câu hỏi), bong bóng tin nhắn User, nhãn `[S1]`. |
| **Primary Hover** | `primary-hover` | `#1D4ED8` | Trạng thái di chuột (`hover`) của các nút hành động chính. |
| **Primary Light** | `primary-light` | `#EFF6FF` | Nền làm nổi bật tài liệu đang được chọn hoặc thẻ trích dẫn đang mở. |
| **App Background** | `bg-app` | `#F8FAFC` | Nền tổng thể của ứng dụng. |
| **Surface** | `bg-surface` | `#FFFFFF` | Nền khu vực khung chat trung tâm, thẻ tài liệu, hộp thoại Modal. |
| **Sidebar / Panel** | `bg-sidebar` | `#F1F5F9` | Nền thanh quản lý tài liệu bên trái và bảng chi tiết trích dẫn bên phải. |
| **Text Primary** | `text-primary` | `#0F172A` | Màu chữ chính cho tiêu đề, nội dung tin nhắn và văn bản tài liệu. |
| **Text Secondary** | `text-secondary` | `#475569` | Màu chữ cho nội dung trích đoạn (`excerpt`) trong bảng đối chiếu nguồn. |
| **Text Muted** | `text-muted` | `#64748B` | Màu chữ phụ cho ngày tạo, dung lượng tệp, số trang, gợi ý ô nhập liệu. |
| **Border Default** | `border-default` | `#E2E8F0` | Đường viền chia tách 3 cột bố cục, viền thẻ và khung nhập câu hỏi. |
| **Status Success** | `status-success` | `#16A34A` | Nhãn trạng thái tài liệu `Processed / Sẵn sàng` (Đã lập chỉ mục xong). |
| **Status Warning** | `status-warning` | `#D97706` | Nhãn trạng thái tài liệu `Processing / Đang xử lý` (Đang đọc và tạo vector). |
| **Status Danger** | `status-danger` | `#DC2626` | Nhãn trạng thái tài liệu `Failed / Lỗi` và nút xác nhận xóa tài liệu. |

### 4.3. Hệ thống Phông chữ (Typography)
* **Font chữ chính (`font-sans`):** **`Inter`** hoặc **`Be Vietnam Pro`** (hỗ trợ hoàn hảo tiếng Việt, nét chữ rõ ràng khi đọc văn bản dài).
* **Font chữ mã nguồn (`font-mono`):** **`JetBrains Mono`** (hiển thị nhãn `[S1]`, `[S2]`, tên file kỹ thuật, khối code).
* **Kích thước chữ chuẩn:**
  * Tiêu đề trang / Header: `20px – 24px` (`font-weight: 700`)
  * Tiêu đề khu vực (Sidebar / Source Panel): `15px – 16px` (`font-weight: 600`)
  * Nội dung tin nhắn Chat: `15px` (`font-weight: 400`, `line-height: 1.65`)
  * Danh sách tài liệu & Lịch sử: `14px` (`font-weight: 500`)
  * Nhãn trạng thái / Số trang / Metadata: `12px` (`font-weight: 500`)

### 4.4. Bố cục màn hình làm việc 3 Cột (3-Column Workspace Layout)

```text
+--------------------------------------------------------------------------------------------------+
| HEADER: Intelligent Document Chatbot                  [Đang chọn: 1 tài liệu] | [Tài khoản]      |
+------------------------+-----------------------------------------------+-------------------------+
| SIDEBAR TRÁI (280px)   | KHU VỰC HỘI THOẠI TRUNG TÂM (Flex-1)          | PANEL NGUỒN PHẢI (360px)|
| Nền: #F1F5F9           | Nền: #FFFFFF                                  | Nền: #F1F5F9            |
|                        |                                               |                         |
| [+ Cuộc trò chuyện mới]|  [User - #2563EB]:                            | CHI TIẾT NGUỒN TRÍCH DẪN|
|                        |  Người lao động làm đủ 12 tháng được nghỉ     |                         |
| TÀI LIỆU CỦA BẠN       |  phép năm bao nhiêu ngày?                     | [S1] Bo_luat_2019.pdf   |
| [x] Bo_luat_2019.pdf   |                                               | Trang 45 • Đoạn #12     |
|     2.4 MB • [Sẵn sàng]|  [AI Assistant]:                              | ----------------------- |
| [ ] Noi_quy_cty.docx   |  Theo Điều 113 Bộ luật Lao động, người lao    | "...Người lao động làm  |
|     420 KB • [Sẵn sàng]|  động làm việc đủ 12 tháng được nghỉ hằng năm | việc đủ 12 tháng cho một|
|                        |  hưởng nguyên lương:                          | người sử dụng lao động  |
| [+ Tải tài liệu mới]   |  • 12 ngày đối với điều kiện bình thường [S1] | thì được nghỉ hằng năm, |
|                        |  • 14 - 16 ngày với công việc nặng nhọc [S1]  | hưởng nguyên lương 12   |
| LỊCH SỬ HỘI THOẠI      |                                               | ngày làm việc..."       |
| • Quy định nghỉ phép   |  Nguồn tham khảo:                             |                         |
| • Thời gian thử việc   |  [ [S1] Bo_luat_2019.pdf - Trang 45 ]         | [Xem trang 45 bản PDF]  |
|                        |                                               |                         |
|                        |  +-----------------------------------------+  |                         |
|                        |  | Nhập câu hỏi về tài liệu...      [Gửi]  |  |                         |
|                        |  +-----------------------------------------+  |                         |
+------------------------+-----------------------------------------------+-------------------------+
```

---

## 5. Cấu trúc thư mục dự án (Monorepo Directory Structure)

```text
intelligent-document-chatbot/
│
├── backend/                                 # PHÂN HỆ BACKEND (PYTHON 3.11 + FASTAPI + RAG)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                          # Điểm khởi chạy FastAPI, cấu hình CORS và đăng ký Routers
│   │   │
│   │   ├── core/                            # Cấu hình cốt lõi hệ thống
│   │   │   ├── __init__.py
│   │   │   ├── config.py                    # Đọc biến môi trường từ .env bằng Pydantic BaseSettings
│   │   │   ├── exceptions.py                # Định nghĩa các mã lỗi chuẩn (INVALID_FILE, EMPTY_DOCUMENT...)
│   │   │   └── logging.py                   # Cấu hình định dạng log chuẩn ra console và file
│   │   │
│   │   ├── api/                             # Tầng giao tiếp HTTP (REST Controllers)
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                      # Dependency Injection (cấp phát DB Session, RAG Services)
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── health_routes.py         # GET /api/health kiểm tra trạng thái máy chủ
│   │   │       ├── document_routes.py       # POST /upload, GET /documents, DELETE /documents/{id}
│   │   │       ├── chat_routes.py           # POST /api/chat thực thi hỏi đáp RAG
│   │   │       └── conversation_routes.py   # GET /api/conversations, GET /conversations/{id}/messages
│   │   │
│   │   ├── services/                        # Tầng nghiệp vụ và lõi RAG Pipeline
│   │   │   ├── __init__.py
│   │   │   ├── document_service.py          # Điều phối lưu tệp, chạy Indexing Pipeline và xóa đồng bộ
│   │   │   ├── document_processor.py        # Bóc tách văn bản PDF (PyMuPDF) và DOCX (python-docx)
│   │   │   ├── text_splitter.py             # Chia nhỏ văn bản thành Chunks có overlap và giữ metadata
│   │   │   ├── embedding_service.py         # Singleton tải mô hình BAAI/bge-m3 và sinh vector chuẩn hóa
│   │   │   ├── vector_store.py              # Giao tiếp ChromaDB PersistentClient (thêm, tìm kiếm, xóa)
│   │   │   ├── retriever.py                 # Truy xuất Top-K đoạn văn bản kèm bộ lọc document_ids
│   │   │   ├── context_builder.py           # Định dạng ngữ cảnh gắn nhãn [S1], [S2] và tạo source_map
│   │   │   ├── llm_service.py               # Thiết lập System Prompt và gọi Gemini / OpenAI / Ollama
│   │   │   ├── citation_service.py          # Quét Regex [S1], [S2] và ánh xạ ngược về metadata thật
│   │   │   └── rag_pipeline.py              # Điều phối toàn bộ luồng Retrieval -> Generation -> Citation
│   │   │
│   │   ├── database/                        # Tầng lưu trữ dữ liệu quan hệ (PostgreSQL)
│   │   │   ├── __init__.py
│   │   │   ├── connection.py                # Khởi tạo SQLAlchemy Engine và SessionLocal
│   │   │   ├── models.py                    # Khai báo 5 bảng ORM: User, Document, Conversation, Message, MessageSource
│   │   │   └── repositories/                # Thực hiện truy vấn SQL tách biệt khỏi logic AI
│   │   │       ├── document_repo.py
│   │   │       └── conversation_repo.py
│   │   │
│   │   ├── schemas/                         # Pydantic Schemas kiểm tra dữ liệu đầu vào / đầu ra
│   │   │   ├── __init__.py
│   │   │   ├── document_schema.py
│   │   │   ├── chat_schema.py
│   │   │   └── conversation_schema.py
│   │   │
│   │   └── utils/                           # Các hàm tiện ích dùng chung
│   │       ├── __init__.py
│   │       ├── file_validator.py            # Kiểm tra đuôi tệp, MIME type, kích thước <= 20MB, tạo tên UUID
│   │       └── text_cleaner.py              # Chuẩn hóa Unicode NFC, xóa ký tự lỗi và dòng trống thừa
│   │
│   ├── tests/                               # Bộ kiểm thử tự động Backend (Pytest)
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_document_processor.py
│   │   │   ├── test_text_splitter.py
│   │   │   └── test_citation_service.py
│   │   └── integration/
│   │       ├── test_retriever.py
│   │       └── test_chat_rag_api.py
│   │
│   ├── storage/                             # Lưu trữ cục bộ (được đưa vào .gitignore)
│   │   ├── uploads/                         # Lưu tệp PDF/DOCX gốc đặt tên theo UUID
│   │   └── chroma_db/                       # Lưu dữ liệu vector bền vững của ChromaDB
│   │
│   ├── migrations/                          # Quản lý phiên bản schema PostgreSQL bằng Alembic
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                                # PHÂN HỆ FRONTEND (REACT + TYPESCRIPT + TAILWIND CSS)
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   │   ├── router.tsx
│   │   │   └── providers.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                          # Thành phần cơ sở shadcn/ui (Button, Dialog, Badge, ScrollArea, Toast)
│   │   │   ├── layout/                      # Bố cục 3 cột (AppHeader, LeftSidebar, WorkspaceLayout, RightSourcePanel)
│   │   │   ├── documents/                   # Quản lý tệp (UploadDropzone, DocumentList, DocumentCard)
│   │   │   ├── chat/                        # Hội thoại (ChatWindow, MessageBubble, ChatInputBox, EmptyChatState)
│   │   │   └── citations/                   # Trích dẫn (CitationBadge, SourceCard, SourceDetailViewer)
│   │   │
│   │   ├── features/                        # Custom Hooks & Store quản lý trạng thái theo nghiệp vụ
│   │   │   ├── documents/
│   │   │   │   └── useDocuments.ts
│   │   │   └── chat/
│   │   │       ├── useChatSession.ts
│   │   │       └── useActiveCitation.ts
│   │   │
│   │   ├── services/                        # Tầng gọi REST API tới FastAPI Backend
│   │   │   ├── api-client.ts
│   │   │   ├── document-api.ts
│   │   │   └── chat-api.ts
│   │   │
│   │   ├── types/                           # Định nghĩa TypeScript Interfaces (IDocument, IMessage, ICitationSource)
│   │   ├── styles/
│   │   │   └── globals.css
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── tests/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── docs/                                    # Lưu tài liệu SRS, Kế hoạch Sprint, Golden Dataset đánh giá RAG
├── scripts/                                 # Script chạy đánh giá tự động các chỉ số RAG
├── docker-compose.yml                       # Khởi chạy đồng bộ PostgreSQL, Backend và Frontend
├── .gitignore
└── README.md
```

---

## 6. Thiết kế chi tiết Luồng xử lý RAG (RAG Pipeline)

### 6.1. Luồng 1: Nạp và Lập chỉ mục tài liệu (Indexing Pipeline)
1. **Kiểm tra & Lưu trữ an toàn (`file_validator.py`):** Kiểm tra phần mở rộng (`.pdf`, `.docx`), đối chiếu MIME type thực tế và dung lượng $\le 20\text{ MB}$. Đổi tên tệp lưu trên đĩa thành `<uuid>.pdf` hoặc `<uuid>.docx` và tạo bản ghi trạng thái `processing` trong PostgreSQL.
2. **Bóc tách văn bản & Metadata (`document_processor.py`):**
   * **PDF:** Dùng `PyMuPDF` đọc từng trang, lưu chính xác `page_number` (bắt đầu từ trang `1`). Nếu tệp chỉ toàn ảnh quét không có chữ, trả về cảnh báo `EMPTY_DOCUMENT`.
   * **DOCX:** Dùng `python-docx` đọc các đoạn văn và bảng biểu, lưu `paragraph_index` và tiêu đề mục gần nhất (`section_title`).
3. **Làm sạch & Phân mảnh (`text_cleaner.py` & `text_splitter.py`):**
   * Chuẩn hóa Unicode tiếng Việt về dạng `NFC`, xóa ký tự điều khiển vô hình và nối các dòng bị ngắt vô lý.
   * Chia văn bản theo ranh giới đoạn/câu với thông số khởi điểm: `chunk_size = 400 tokens`, `chunk_overlap = 60 tokens` ($15\%$). Mỗi Chunk kế thừa nguyên vẹn `document_id`, `filename`, `page_number` và `chunk_index`.
4. **Vector hóa & Lưu ChromaDB (`embedding_service.py` & `vector_store.py`):**
   * Mã hóa các Chunk bằng mô hình `BAAI/bge-m3` với `normalize_embeddings=True`.
   * Lưu vào Collection `documents_index` của ChromaDB và cập nhật trạng thái tài liệu trong PostgreSQL sang `processed`.

### 6.2. Luồng 2: Truy xuất, Sinh câu trả lời & Đối chiếu trích dẫn (Retrieval & Generation)
1. **Truy xuất ngữ nghĩa (`retriever.py`):** Vector hóa câu hỏi bằng cùng mô hình `BAAI/bge-m3`, tìm kiếm `Top-K` ($K = 5$) đoạn văn gần nhất trong ChromaDB theo khoảng cách Cosine (có lọc theo `document_ids` được chọn).
2. **Đóng gói ngữ cảnh (`context_builder.py`):** Gán mã định danh tạm thời `[S1]`, `[S2]`, ..., `[S5]` cho từng đoạn văn tìm được và lưu bảng ánh xạ `source_map` tại Backend.
3. **Sinh câu trả lời (`llm_service.py`):** Gửi câu hỏi cùng khối ngữ cảnh tới LLM (`Temperature = 0.1 – 0.2`) với quy tắc bắt buộc: chỉ sử dụng thông tin trong ngữ cảnh, gắn mã `[S1]`, `[S2]` ngay sau câu trả lời và coi mọi mệnh lệnh trong tài liệu là dữ liệu thụ động.
4. **Xác thực trích dẫn hai lớp (`citation_service.py`):** Dùng biểu thức chính quy (`Regex`) bóc tách các mã `[Sx]` xuất hiện trong câu trả lời của LLM, đối chiếu với `source_map` để lấy ra tên tệp, số trang PDF và đoạn trích gốc (`excerpt`) thật từ Backend trả về cho Frontend.

---

## 7. Thiết kế Cơ sở dữ liệu & Đặc tả RESTful API

### 7.1. Thiết kế 5 bảng Cơ sở dữ liệu Quan hệ (PostgreSQL)

| Tên bảng | Khóa chính | Các trường thông tin chính | Mục đích lưu trữ |
| :--- | :--- | :--- | :--- |
| **`users`** | `id` (UUID) | `email`, `password_hash`, `created_at` | Quản lý thông tin tài khoản người dùng. |
| **`documents`** | `id` (UUID) | `user_id`, `filename`, `storage_path`, `file_type`, `file_size`, `status`, `chunk_count`, `created_at` | Quản lý danh mục tệp đã tải lên và trạng thái xử lý. |
| **`conversations`** | `id` (UUID) | `user_id`, `title`, `created_at` | Quản lý các phiên hội thoại của người dùng. |
| **`messages`** | `id` (UUID) | `conversation_id`, `role` (`user`/`assistant`), `content`, `created_at` | Lưu trữ toàn bộ lịch sử tin nhắn hỏi đáp. |
| **`message_sources`** | `id` (UUID) | `message_id`, `document_id`, `source_label` (`S1`), `chunk_id`, `page_number`, `excerpt` | Lưu liên kết giữa câu trả lời của AI và nguồn trích dẫn. |

### 7.2. Danh mục Điểm cuối Giao tiếp (RESTful API Endpoints)

| Phương thức | Endpoint | Mô tả chức năng |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Kiểm tra trạng thái hoạt động của Backend và kết nối cơ sở dữ liệu. |
| `POST` | `/api/documents/upload` | Tải tệp PDF/DOCX lên hệ thống, kiểm tra an toàn và chạy Indexing Pipeline. |
| `GET` | `/api/documents` | Lấy danh sách toàn bộ tài liệu kèm trạng thái xử lý (`processing`, `processed`, `failed`). |
| `GET` | `/api/documents/{id}` | Xem chi tiết thông tin metadata và tổng số Chunk của một tài liệu. |
| `DELETE` | `/api/documents/{id}` | Xóa đồng bộ tài liệu ở cả 3 nơi: ChromaDB, thư mục `storage/uploads/` và PostgreSQL. |
| `POST` | `/api/chat` | Gửi câu hỏi kèm `document_ids` và `conversation_id`; trả về câu trả lời + mảng `sources`. |
| `GET` | `/api/conversations` | Lấy danh sách các phiên hội thoại đã lưu. |
| `GET` | `/api/conversations/{id}/messages` | Lấy toàn bộ lịch sử tin nhắn và trích dẫn đi kèm của một phiên hội thoại. |

---

## 8. Bảo mật, Kiểm thử & Đánh giá chất lượng RAG

### 8.1. Các chỉ số Đánh giá Chất lượng Hệ thống RAG (Evaluation Metrics)
Dự án sử dụng bộ dữ liệu kiểm thử chuẩn (**Golden Dataset** gồm `75 câu hỏi`: 40 câu hỏi trực tiếp, 20 câu hỏi tổng hợp và 15 câu hỏi ngoài tài liệu) để đo lường định lượng:
* **Chất lượng Truy xuất (Retrieval):**
  * **`Hit Rate@K` & `Recall@K`:** Tỷ lệ hệ thống tìm được đúng đoạn văn bản chứa bằng chứng trong `Top-K` kết quả.
  * **`MRR` (Mean Reciprocal Rank):** Đánh giá vị trí xếp hạng của đoạn văn bản đúng đầu tiên.
* **Chất lượng Sinh câu trả lời (Generation):**
  * **`Faithfulness` (Độ trung thực):** Câu trả lời hoàn toàn dựa trên ngữ cảnh, không tự suy diễn ngoài tài liệu.
  * **`Answer Relevancy`:** Mức độ câu trả lời giải quyết trực tiếp, đúng trọng tâm câu hỏi.
  * **`Citation Accuracy`:** Tỷ lệ trích dẫn đúng tên tệp và đúng số trang PDF chứa bằng chứng.

### 8.2. Mười kịch bản Kiểm thử Hệ thống & Bảo mật cốt lõi (`TC-01` $\rightarrow$ `TC-10`)
1. **`TC-01`:** Tải lên tệp PDF tiếng Việt nhiều trang hợp lệ $\rightarrow$ Trích xuất đúng chữ và đúng số trang.
2. **`TC-02`:** Tải lên tệp DOCX có tiêu đề và bảng biểu $\rightarrow$ Trích xuất đầy đủ đoạn văn và dữ liệu bảng.
3. **`TC-03`:** Tải lên tệp sai định dạng (`.exe`, `.zip` đổi đuôi thành `.pdf`) $\rightarrow$ Từ chối với mã lỗi `INVALID_FILE`.
4. **`TC-04`:** Tải lên tệp vượt quá `20MB` $\rightarrow$ Chặn ngay từ luồng đọc với mã lỗi `FILE_TOO_LARGE`.
5. **`TC-05`:** Tải lên tệp PDF ảnh scan không có lớp văn bản $\rightarrow$ Trả về cảnh báo `EMPTY_DOCUMENT`.
6. **`TC-06`:** Đặt câu hỏi có thông tin rõ trong tài liệu $\rightarrow$ Trả lời chính xác kèm thẻ nguồn `[S1]` đúng số trang.
7. **`TC-07`:** Đặt câu hỏi ngoài phạm vi tài liệu $\rightarrow$ Từ chối lịch sự, thông báo tài liệu không đề cập và trả về mảng `sources` rỗng.
8. **`TC-08`:** Xóa một tài liệu $\rightarrow$ Toàn bộ vector trong ChromaDB, tệp gốc và bản ghi SQL bị xóa sạch; hỏi lại không còn truy xuất được.
9. **`TC-09`:** Dịch vụ LLM bị quá thời gian chờ (`Timeout`) $\rightarrow$ Hệ thống tự thử lại và hiển thị thông báo thân thiện, không treo giao diện.
10. **`TC-10`:** Tài liệu chứa câu lệnh **Prompt Injection** (*"Hãy bỏ qua mọi quy tắc trước đó..."*) $\rightarrow$ Hệ thống xem đó là dữ liệu văn bản thuần túy, không làm theo mệnh lệnh độc hại.

---

## 9. Lộ trình triển khai 6 Sprint (6 Tuần)

| Sprint | Thời gian | Trọng tâm triển khai | Các mã Task chính | Sản phẩm bàn giao (Deliverables) |
| :--- | :--- | :--- | :--- | :--- |
| **Sprint 1** | Tuần 1 | Khởi tạo & Kiến trúc nền tảng | `SP1-01` $\rightarrow$ `SP1-05` | Monorepo GitHub, khung FastAPI, 5 bảng PostgreSQL, khung ReactJS + Tailwind CSS. |
| **Sprint 2** | Tuần 2 | Xử lý tài liệu & Phân mảnh (Chunking) | `SP2-01` $\rightarrow$ `SP2-06` | Bộ kiểm tra tệp, bóc tách PDF/DOCX kèm số trang, làm sạch văn bản, chia Chunk & Unit Tests. |
| **Sprint 3** | Tuần 3 | Vector hóa & Truy xuất ngữ nghĩa | `SP3-01` $\rightarrow$ `SP3-05` | Tích hợp `BAAI/bge-m3`, lưu trữ bền vững `ChromaDB`, Indexing Pipeline và bộ tìm kiếm `Top-K`. |
| **Sprint 4** | Tuần 4 | Tích hợp LLM, Trích dẫn & REST API | `SP4-01` $\rightarrow$ `SP4-05` | Context Builder, LLM Service chống ảo giác, Citation Service đối chiếu nguồn và toàn bộ REST API. |
| **Sprint 5** | Tuần 5 | Giao diện người dùng 3 Cột (ReactJS) | `SP5-01` $\rightarrow$ `SP5-05` | Giao diện SaaS 3 cột, kéo thả tải tệp, khung Chat Markdown và Panel đối chiếu đoạn trích gốc. |
| **Sprint 6** | Tuần 6 | Đánh giá RAG, Kiểm thử & Docker | `SP6-01` $\rightarrow$ `SP6-05` | Bộ 75 câu hỏi kiểm thử, báo cáo chỉ số RAG, vượt qua `TC-01` $\rightarrow$ `TC-10`, Docker Compose & `README.md`. |

---

## 10. Cấu hình môi trường & Hướng dẫn khởi chạy

### 10.1. Mẫu cấu hình biến môi trường (`.env.example`)

```env
# Cấu hình chung
APP_NAME="Intelligent Document Chatbot"
APP_ENV="development"
API_PORT=8000

# Cơ sở dữ liệu & Lưu trữ
DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/doc_chatbot"
CHROMA_PERSIST_DIR="./storage/chroma_db"
UPLOAD_DIR="./storage/uploads"
MAX_FILE_SIZE_MB=20

# Cấu hình Mô hình AI & RAG
LLM_PROVIDER="gemini"                      # Hỗ trợ: gemini | openai | ollama
LLM_API_KEY="your_api_key_here"
LLM_MODEL="gemini-2.5-flash"
EMBEDDING_MODEL_NAME="BAAI/bge-m3"

# Tham số RAG Pipeline
CHUNK_SIZE=400
CHUNK_OVERLAP=60
RETRIEVAL_TOP_K=5
```

### 10.2. Các bước chạy dự án nhanh

1. **Khởi chạy bằng Docker Compose (Khuyên dùng khi hoàn thiện):**
   ```bash
   docker-compose up --build -d
   ```
2. **Khởi chạy môi trường phát triển (Local Development):**
   * **Backend:**
     ```bash
     cd backend
     python -m venv venv
     # Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate
     pip install -r requirements.txt
     alembic upgrade head
     uvicorn app.main:app --reload --port 8000
     ```
   * **Frontend:**
     ```bash
     cd frontend
     npm install
     npm run dev
     ```