# Intelligent Document Chatbot (LLM + RAG)

Ứng dụng web hỏi đáp tài liệu thông minh (`PDF`, `DOCX`) ứng dụng **Large Language Model (LLM)** kết hợp **Retrieval-Augmented Generation (RAG)**, cung cấp câu trả lời bám sát ngữ cảnh kèm trích dẫn nguồn xác thực hai lớp (`[S1]`, `[S2]`).

> 📄 Xem tài liệu thiết kế kỹ thuật chi tiết tại: [intelligent_document_chatbot.md](./intelligent_document_chatbot.md)

---

## Cấu trúc thư mục Monorepo

```text
1-RAG-LLM-chatbot/
├── backend/                  # FastAPI + Python 3.11 + RAG Pipeline (Modular Monolith)
│   ├── app/
│   │   ├── api/routes/       # RESTful API Endpoints
│   │   ├── core/             # Config, Exceptions, Logging
│   │   ├── database/         # SQLAlchemy ORM & Repositories (PostgreSQL)
│   │   ├── schemas/          # Pydantic v2 Request/Response Schemas
│   │   ├── services/         # Document Processor, Chunker, Embedding, ChromaDB, LLM, Citation
│   │   └── utils/            # File Validator & Unicode NFC Text Cleaner
│   ├── migrations/           # Alembic Database Migrations
│   ├── storage/              # Local Uploads & ChromaDB Persistence
│   └── tests/                # Pytest Unit & Integration Tests
├── frontend/                 # React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui
├── docs/                     # Tài liệu SRS, Sprint Plan & Golden Dataset
├── scripts/                  # Scripts đánh giá chất lượng RAG & tiện ích hệ thống
├── storage/                  # Thư mục lưu trữ gốc (uploads/, chroma_db/)
├── .env.example              # Mẫu cấu hình biến môi trường
└── .gitignore                # Quy chuẩn loại trừ tệp cho Python & Node.js
```

## Công nghệ cốt lõi (Tech Stack)

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic
- **AI / RAG:** `BAAI/bge-m3` (`sentence-transformers`), `ChromaDB` (`PersistentClient`), Gemini / OpenAI / Ollama
- **Document Parsing:** `PyMuPDF` (`fitz`), `python-docx`
- **Database:** PostgreSQL 16
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, `shadcn/ui`, TanStack Query, Zustand
