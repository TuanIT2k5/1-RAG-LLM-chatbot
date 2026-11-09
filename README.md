# Intelligent Document Chatbot (LLM + RAG)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?logo=typescript&logoColor=white)
![ChromaDB](https://img.shields.io/badge/Vector_DB-ChromaDB-FF6F00)
![Embedding](https://img.shields.io/badge/Embedding-BAAI%2Fbge--m3-8A2BE2)
![Docker](https://img.shields.io/badge/Docker-Compose_Ready-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/System_Tests-10%2F10_PASSED-2EA043)

Ứng dụng Web **Hỏi - Đáp Tài liệu Thông minh (`PDF`, `DOCX`)** ứng dụng **Large Language Model (LLM)** kết hợp kiến trúc **Retrieval-Augmented Generation (RAG)**. Hệ thống cho phép người dùng tải lên tài liệu đa định dạng tiếng Việt/tiếng Anh, băm nhỏ giữ nguyên cấu trúc số trang/tiêu đề, truy xuất ngữ nghĩa chính xác và sinh câu trả lời bám sát ngữ cảnh kèm **trích dẫn nguồn xác thực 2 lớp (`[S1]`, `[S2]`)** có thể nhấn vào để kiểm chứng trực tiếp trên trang PDF gốc.

> **Hồ sơ tài liệu kỹ thuật & kiểm thử của dự án:**
> - Thiết kế kiến trúc & SRS chi tiết: [`intelligent_document_chatbot.md`](./intelligent_document_chatbot.md)
> - Bộ dữ liệu kiểm thử chuẩn 75 câu hỏi (Golden Dataset): [`docs/golden_dataset/README.md`](./docs/golden_dataset/README.md)
> - Báo cáo đánh giá định lượng RAG & A/B Testing: [`docs/golden_dataset/RAG_EVALUATION_REPORT.md`](./docs/golden_dataset/RAG_EVALUATION_REPORT.md)
> - Biên bản 10 kịch bản kiểm thử lỗi & bảo mật (`TC-01 -> TC-10`): [`docs/SECURITY_AND_TEST_REPORT_TC01_TC10.md`](./docs/SECURITY_AND_TEST_REPORT_TC01_TC10.md)
> - Kịch bản trình diễn (Demo 5 phút): [`docs/DEMO_SCRIPT_5_MINUTES.md`](./docs/DEMO_SCRIPT_5_MINUTES.md)
> - Đúc kết đóng góp kỹ thuật cho CV / Portfolio: [`docs/PORTFOLIO_AND_CV_HIGHLIGHTS.md`](./docs/PORTFOLIO_AND_CV_HIGHLIGHTS.md)

---

## Tính năng Nổi bật (Key Features)

1. **Xử lý Tài liệu Đa định dạng Bảo toàn Ngữ cảnh (`PDF` & `DOCX`):**
   - Kiểm tra chữ ký nhị phân thực tế (**Magic Bytes Validation** `%PDF-` và `PK\x03\x04` + `word/document.xml`), chặn tệp `.exe`/`.zip` giả mạo và giới hạn dung lượng `20MB`.
   - Chuẩn hóa **Unicode dựng sẵn (`NFC`)** tiếng Việt, bảo toàn số trang PDF (`page_number`), tiêu đề chương mục (`section_title`) và cấu trúc bảng biểu DOCX.
2. **Chiến lược Băm Văn bản Đệ quy Giữ Ngữ cảnh (`Recursive Token Chunking`):**
   - Chia nhỏ văn bản theo cấu trúc phân cấp (`\n\n` -> `\n` -> câu `. ` -> từ) với kích thước tối ưu **`400 tokens`** và phần gối đầu **`60 tokens (15%)`**, không cắt ngang câu chữ tiếng Việt.
3. **Truy xuất Ngữ nghĩa Đa ngôn ngữ & Bộ lọc Phạm vi Tài liệu:**
   - Tích hợp mô hình **`BAAI/bge-m3`** (`1024 chiều`, chuẩn hóa `L2` phục vụ tương đồng Cosine) trên **`ChromaDB PersistentClient`**, hỗ trợ lọc chính xác theo danh sách tài liệu người dùng đang tích chọn (`document_ids`).
4. **Cơ chế Xác thực Trích dẫn 2 Lớp & Chống Ảo giác (`Zero Hallucinated Citations`):**
   - **Lớp 1 (Context Grounding):** Đóng gói đoạn văn truy xuất thành các khối `[S1]`, `[S2]`... bên trong thẻ cô lập `<document_context>...</document_context>` chống tấn công **Indirect Prompt Injection**.
   - **Lớp 2 (Regex Post-Verification):** Hậu kiểm câu trả lời của LLM bằng biểu thức chính quy `\[S(\d+)\]`, đối chiếu với bảng `source_map` để loại bỏ 100% nhãn trích dẫn bịa đặt và chỉ giữ lại nguồn có thật.
5. **Giao diện Web SaaS 3 Cột Hiện đại & Đối chiếu Trang PDF Trực tiếp:**
   - **Cột trái:** Kéo-thả tải tệp, tích chọn phạm vi tài liệu truy vấn, quản lý lịch sử các phiên hội thoại.
   - **Cột giữa:** Khung hội thoại thông minh hiển thị Markdown và các huy hiệu trích dẫn tương tác (`[S1]`, `[S2]`).
   - **Cột phải:** Khung kiểm chứng nguồn (`Source Verification Panel`) tự động cuộn, làm nổi bật đoạn trích và mở trực tiếp đúng trang PDF gốc (`#page=N`) khi người dùng nhấn vào `[S1]`.

---

## Kiến trúc Hệ thống (System Architecture)

```mermaid
flowchart TB
    subgraph Client["Frontend Web UI (React 18 + TypeScript + Tailwind CSS)"]
        Sidebar["Cột trái: Quản lý Tài liệu & Lịch sử Chat"]
        Chat["Cột giữa: Khung Hỏi - Đáp & Huy hiệu [S1], [S2]"]
        SourcePanel["Cột phải: Đối chiếu Đoạn trích & Xem PDF (#page=N)"]
    end

    subgraph API["FastAPI Backend (Modular Monolith)"]
        Validator["File Validator (Magic Bytes + 20MB Limit)"]
        Parser["Document Processor (PyMuPDF & python-docx + NFC)"]
        Chunker["Recursive Chunker (400 tokens, 60 overlap)"]
        Embedder["Embedding Service (BAAI/bge-m3 1024-dim)"]
        Retriever["Semantic Retriever (Cosine + Document Filter)"]
        Prompt["Context Builder (<document_context> [S1]..[SK])"]
        Verifier["Citation Verifier (2-Layer Regex Verification)"]
    end

    subgraph Storage["Tầng Lưu trữ Bền vững (Persistent Volumes)"]
        PG[("PostgreSQL 16\n(Documents, Conversations, Messages)")]
        Chroma[("ChromaDB\n(HNSW Cosine Vector Index)")]
        Disk[("Local/Volume Disk\n(Original PDF/DOCX Files)")]
    end

    LLM[["LLM Provider\n(Gemini / OpenAI / Ollama)"]]

    Sidebar -->|Upload PDF/DOCX| Validator --> Parser --> Chunker --> Embedder --> Chroma
    Validator --> Disk
    Parser --> PG

    Chat -->|POST /api/chat| Retriever
    Retriever <-->|Top-K Vectors| Chroma
    Retriever --> Prompt --> LLM --> Verifier
    Verifier -->|Lưu Lịch sử & Nguồn| PG
    Verifier -->|Answer + Verified Sources| Chat
    Chat -->|Nhấn huy hiệu [S1]| SourcePanel
    SourcePanel -->|GET /api/documents/{id}/file#page=N| Disk
```

---

## Công nghệ Sử dụng (Tech Stack)

| Phân hệ | Công nghệ / Thư viện | Vai trò trong hệ thống |
| :--- | :--- | :--- |
| **Backend API** | **Python 3.11+**, **FastAPI**, **Uvicorn**, **Pydantic v2** | Xây dựng RESTful API bất đồng bộ, kiểm tra kiểu dữ liệu chặt chẽ và xử lý ngoại lệ tập trung. |
| **Xử lý Tài liệu** | **PyMuPDF (`fitz`)**, **python-docx**, **unicodedata (`NFC`)** | Bóc tách văn bản PDF theo trang, trích xuất đoạn văn & bảng biểu DOCX, làm sạch văn bản tiếng Việt. |
| **AI & RAG Engine** | **`BAAI/bge-m3`** (`sentence-transformers`), **Gemini / OpenAI / Ollama** | Vector hóa ngữ nghĩa đa ngôn ngữ `1024 chiều` và sinh câu trả lời bám sát ngữ cảnh tài liệu. |
| **Vector Database** | **ChromaDB (`PersistentClient`)** | Lưu trữ chỉ mục vector HNSW bền vững trên đĩa, truy vấn tương đồng Cosine kèm bộ lọc `where`. |
| **Relational DB** | **PostgreSQL 16**, **SQLAlchemy 2.0**, **Alembic** | Lưu trữ metadata tài liệu, phiên hội thoại (`conversations`), tin nhắn (`messages`) và trích dẫn (`message_sources`). |
| **Frontend UI** | **React 18**, **TypeScript**, **Vite**, **Tailwind CSS**, **TanStack Query** | Giao diện SaaS 3 cột phản hồi tức thì, quản lý trạng thái bất đồng bộ và hiển thị trích dẫn tương tác. |
| **DevOps & Testing** | **Docker**, **Docker Compose**, **Nginx**, **Pytest** | Đóng gói multi-stage container, Reverse Proxy và kiểm thử tự động toàn diện. |

---

## Cấu trúc Thư mục Dự án (Monorepo Structure)

```text
1-RAG-LLM-chatbot/
├── backend/                        # Phân hệ Backend (FastAPI + RAG Pipeline)
│   ├── app/
│   │   ├── api/routes/             # Các маршруt API (/health, /documents, /chat, /conversations)
│   │   ├── core/                   # Cấu hình (.env), Mã lỗi chuẩn & Logging
│   │   ├── database/               # SQLAlchemy ORM Models & Repositories
│   │   ├── schemas/                # Pydantic v2 Request / Response Schemas
│   │   ├── services/               # DocumentProcessor, Chunker, Embedding, VectorStore,
│   │   │                           # SemanticRetriever, ContextBuilder, LLMService, CitationService
│   │   └── utils/                  # Kiểm tra Magic Bytes tệp tin & Chuẩn hóa Unicode NFC
│   ├── migrations/                 # Quản lý phiên bản lược đồ CSDL với Alembic
│   ├── tests/                      # Bộ kiểm thử tự động Pytest (Unit & Integration TC-01 -> TC-10)
│   ├── Dockerfile                  # Dockerfile tối ưu cho Backend (Python 3.11-slim + BGE-M3 cache)
│   └── requirements.txt            # Danh sách thư viện Python
├── frontend/                       # Phân hệ Frontend (React 18 + TypeScript + Tailwind CSS)
│   ├── src/
│   │   ├── components/             # Layout 3 cột, UploadDropzone, ChatWindow, CitationBadge, SourceCard...
│   │   ├── features/               # Custom Hooks (useDocuments, useChatSession, useActiveCitation)
│   │   ├── services/               # Tầng giao tiếp API (api-client.ts, document-api.ts, chat-api.ts)
│   │   └── types/                  # Định nghĩa kiểu dữ liệu TypeScript đồng bộ với Backend
│   ├── Dockerfile                  # Multi-stage Dockerfile (Node 20 Alpine -> Nginx 1.27 Alpine)
│   └── nginx.conf                  # Cấu hình Nginx Gzip, SPA Routing & Reverse Proxy /api/
├── docs/                           # Hồ sơ dự án, Báo cáo đánh giá & Kịch bản Demo
│   ├── golden_dataset/             # Bộ 75 câu hỏi kiểm thử chuẩn, 4 tài liệu gốc & Báo cáo RAG
│   ├── SECURITY_AND_TEST_REPORT_TC01_TC10.md
│   ├── DEMO_SCRIPT_5_MINUTES.md
│   └── PORTFOLIO_AND_CV_HIGHLIGHTS.md
├── scripts/                        # Kịch bản sinh Golden Dataset & Đánh giá định lượng RAG tự động
├── docker-compose.yml              # Khởi chạy toàn bộ hệ thống (Postgres + Backend + Frontend) bằng 1 lệnh
└── .env.example                    # Tệp mẫu cấu hình biến môi trường
```

---

##  Hướng dẫn Cài đặt & Khởi chạy Nhanh (Quick Start)

### Cách 1: Khởi chạy tức thì bằng Docker Compose (Khuyến nghị)

Yêu cầu: Đã cài đặt và bật **Docker Desktop**.

```powershell
# 1. Sao chép tệp cấu hình biến môi trường và điền LLM_API_KEY của bạn
Copy-Item .env.example .env

# 2. Xây dựng và khởi chạy toàn bộ 3 dịch vụ (PostgreSQL + Backend + Frontend)
docker compose up --build -d

# 3. Kiểm tra trạng thái hoạt động của các container
docker compose ps
```

- **Giao diện người dùng (Web UI):** [http://localhost:5173](http://localhost:5173)
- **Tài liệu API (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Kiểm tra sức khỏe hệ thống:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Cách 2: Cài đặt & Chạy trực tiếp trên máy cục bộ (Local Development)

#### Bước 1 — Khởi chạy Backend (Cửa sổ Terminal 1):

```powershell
cd backend

# Tạo môi trường ảo Python và cài đặt thư viện
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt

# Sao chép tệp .env và cấu hình LLM_API_KEY
Copy-Item .env.example .env

# Khởi chạy máy chủ FastAPI tại cổng 8000
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Lưu ý tiện lợi khi chạy Local:** Nếu máy bạn chưa bật dịch vụ PostgreSQL ở cổng `5432`, hệ thống ở chế độ `development` sẽ tự động chuyển sang cơ sở dữ liệu SQLite cục bộ (`backend/storage/doc_chatbot.sqlite`) và tự động tạo bảng để bạn trải nghiệm ngay lập tức mà không gặp lỗi kết nối.

#### Bước 2 — Khởi chạy Frontend (Cửa sổ Terminal 2):

```powershell
cd frontend

# Cài đặt gói thư viện Node.js
npm install

# Khởi chạy máy chủ phát triển Vite tại cổng 5173
npm run dev
```

Mở trình duyệt tại **[http://localhost:5173](http://localhost:5173)** để sử dụng ứng dụng.

---

## 🔌 Danh mục RESTful API Cốt lõi

| Phương thức | Đường dẫn (Endpoint) | Mô tả chức năng |
| :---: | :--- | :--- |
| `GET` | `/api/health` | Kiểm tra trạng thái hoạt động của Backend, PostgreSQL/SQLite và ChromaDB. |
| `POST` | `/api/documents/upload` | Tải lên tệp `.pdf`/`.docx`, kiểm tra Magic Bytes, trích xuất, băm nhỏ và lưu vector. |
| `GET` | `/api/documents` | Lấy danh sách toàn bộ tài liệu đã tải lên kèm trạng thái và số lượng `chunk_count`. |
| `GET` | `/api/documents/{id}/file` | Phục vụ tệp PDF/DOCX gốc (`inline`) để trình xem tài liệu mở trực tiếp đến `#page=N`. |
| `DELETE` | `/api/documents/{id}` | Xóa đồng bộ tài liệu ở cả 3 nơi: ChromaDB Vector Store, ổ đĩa vật lý và SQL Database. |
| `POST` | `/api/chat` | Thực thi luồng hỏi đáp RAG, trả về câu trả lời kèm danh sách nguồn trích dẫn đã xác thực. |
| `GET` | `/api/conversations` | Lấy danh sách lịch sử các phiên hội thoại. |
| `GET` | `/api/conversations/{id}/messages` | Tải lại toàn bộ tin nhắn và thẻ trích dẫn của một phiên hội thoại cũ. |
| `DELETE` | `/api/conversations/{id}` | Xóa phiên hội thoại và các tin nhắn liên quan. |

---

## 📊 Kết quả Đánh giá Định lượng Hệ thống RAG & A/B Testing (`SP6-02`)

Hệ thống được đo lường tự động trên bộ dữ liệu kiểm thử chuẩn **[Golden Dataset (75 câu hỏi)](./docs/golden_dataset/README.md)** gồm **40 câu hỏi tra cứu trực tiếp**, **20 câu hỏi tổng hợp nhiều đoạn** và **15 câu hỏi ngoài phạm vi tài liệu** trên 4 tài liệu thực tế (`.pdf` và `.docx`).

> 📈 Xem báo cáo phân tích chi tiết tại: **[`docs/golden_dataset/RAG_EVALUATION_REPORT.md`](./docs/golden_dataset/RAG_EVALUATION_REPORT.md)**

### Bảng so sánh A/B Testing (`Chunk Size: 300 vs 400 vs 500` & `Top-K: 3 vs 5`)

| Mã Cấu Hình | Chunk Size | Overlap | Top-K | Tổng Chunks | Hit Rate@K | Recall@K | Precision@K | MRR | Faithfulness | Answer Relevancy | Citation Accuracy | OOS Refusal | Latency TB | Điểm Tổng Hợp |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **CFG-300-K3** | `300` | `45` | `3` | 141 | 98.3% | 91.9% | 60.0% | 0.964 | 100.0% | 91.5% | 100.0% | 100.0% | 11.6 ms | 0.9598 |
| **CFG-300-K5** | `300` | `45` | `5` | 141 | 98.3% | 94.2% | 41.7% | 0.964 | 100.0% | 94.2% | 100.0% | 100.0% | 12.7 ms | 0.9682 |
| **CFG-400-K3** | `400` | `60` | `3` | 88 | 98.3% | 94.7% | 50.0% | 0.983 | 100.0% | 94.7% | 100.0% | 100.0% | 12.6 ms | 0.9740 |
| **CFG-400-K5** 🏆 | `400` | `60` | `5` | 88 | **98.3%** | **95.8%** | 33.0% | **0.983** | **100.0%** | **95.8%** | **100.0%** | **100.0%** | 16.9 ms | **0.9779** |
| **CFG-500-K3** | `500` | `75` | `3` | 87 | 98.3% | 94.7% | 50.0% | 0.983 | 100.0% | 94.7% | 100.0% | 100.0% | 13.3 ms | 0.9740 |
| **CFG-500-K5** | `500` | `75` | `5` | 87 | 98.3% | 95.8% | 33.0% | 0.983 | 100.0% | 95.8% | 100.0% | 100.0% | 15.9 ms | 0.9779 |

---

## 🛡️ Kết quả 10 Kịch bản Kiểm thử Hệ thống & Bảo mật Cốt lõi (`SP6-03`)

> 🔒 Xem biên bản nghiệm thu chi tiết tại: **[`docs/SECURITY_AND_TEST_REPORT_TC01_TC10.md`](./docs/SECURITY_AND_TEST_REPORT_TC01_TC10.md)**

| Mã TC | Tình huống Kiểm thử | Kết quả |
| :---: | :--- | :---: |
| **`TC-01`** | Tải lên tệp PDF tiếng Việt nhiều trang hợp lệ (`25 trang`) -> Trích xuất đúng Unicode & số trang | ✅ **PASSED** |
| **`TC-02`** | Tải lên tệp DOCX có tiêu đề (`Heading`) và bảng biểu (`Table`) -> Lập chỉ mục thành công | ✅ **PASSED** |
| **`TC-03`** | Tải lên tệp `.exe` (`MZ`), `.zip` giả danh `.pdf` và PDF lỗi hỏng -> Chặn đứng (`HTTP 400 INVALID_FILE`) | ✅ **PASSED** |
| **`TC-04`** | Tải lên tệp vượt quá `20MB` -> Chặn ngay từ luồng đọc (`HTTP 413 FILE_TOO_LARGE`) | ✅ **PASSED** |
| **`TC-05`** | Tải lên tệp PDF ảnh scan không có lớp văn bản -> Cảnh báo `EMPTY_DOCUMENT` (`HTTP 422`) | ✅ **PASSED** |
| **`TC-06`** | Đặt câu hỏi trong phạm vi tài liệu -> Trả lời chính xác kèm nhãn `[S1]` đúng số trang PDF | ✅ **PASSED** |
| **`TC-07`** | Đặt câu hỏi ngoài phạm vi tài liệu -> Từ chối lịch sự, `sources = []`, tiết kiệm 100% lượt gọi LLM | ✅ **PASSED** |
| **`TC-08`** | Xóa tài liệu khi đang mở phiên chat -> Xóa sạch đồng bộ ở cả 3 nơi (ChromaDB, Ổ đĩa, SQL) | ✅ **PASSED** |
| **`TC-09`** | Dịch vụ LLM bị quá thời gian chờ (`Timeout`) -> Tự động Retry 2 lần & trả lỗi `503` thân thiện | ✅ **PASSED** |
| **`TC-10`** | Tài liệu chứa lệnh **Indirect Prompt Injection** & nhãn giả `[S99]` -> Cô lập ngữ cảnh & lọc sạch `[S99]` | ✅ **PASSED** |

---

## 🧪 Lệnh Chạy Kiểm thử Tự động (Automated Testing)

```powershell
# 1. Chạy bộ 10 kịch bản kiểm thử hệ thống & bảo mật cốt lõi (TC-01 -> TC-10)
cd backend
.\venv\Scripts\pytest.exe tests/integration/test_system_security_tc01_tc10.py -v

# 2. Chạy toàn bộ bộ kiểm thử Unit & Integration của dự án
.\venv\Scripts\pytest.exe -v

# 3. Chạy lại kịch bản đánh giá định lượng RAG trên 75 câu hỏi Golden Dataset
cd ..
.\backend\venv\Scripts\python.exe scripts/evaluate_rag.py
```
