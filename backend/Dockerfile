# ==============================================================================
# [SP6-04.1] Dockerfile tối ưu cho Backend (FastAPI + RAG Pipeline + BGE-M3)
# Sử dụng Python 3.11-slim, tách tầng lưu đệm (cache) thư viện và thư mục BGE-M3
# ==============================================================================
FROM python:3.11-slim

LABEL maintainer="Intelligent Document Chatbot Team"
LABEL description="FastAPI Modular Monolith Backend for RAG Document Chatbot"

# 1. Thiết lập biến môi trường hệ thống và thư mục lưu đệm mô hình BGE-M3 bền vững
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app \
    HF_HOME=/app/storage/model_cache \
    SENTENCE_TRANSFORMERS_HOME=/app/storage/model_cache \
    TORCH_HOME=/app/storage/model_cache \
    CHROMA_PERSIST_DIR=/app/storage/chroma_db \
    UPLOAD_DIR=/app/storage/uploads

WORKDIR ${APP_HOME}

# 2. Cài đặt các gói phụ thuộc hệ điều hành tối thiểu (libpq cho PostgreSQL, curl cho healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Sao chép requirements.txt trước để tận dụng tối đa Docker Layer Caching
COPY requirements.txt ./

# 4. Cài đặt PyTorch CPU-only gọn nhẹ và toàn bộ thư viện Python từ requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# 5. Tạo sẵn cấu trúc thư mục lưu trữ bền vững cho ChromaDB, Uploads và BGE-M3 Model Cache
RUN mkdir -p ${CHROMA_PERSIST_DIR} ${UPLOAD_DIR} ${HF_HOME}

# 6. Sao chép mã nguồn ứng dụng và cấu hình Alembic
COPY alembic.ini ./
COPY app ./app

# Mở cổng dịch vụ FastAPI
EXPOSE 8000

# Kiểm tra sức khỏe dịch vụ định kỳ
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

# 7. Khởi chạy máy chủ ASGI Uvicorn (bảng CSDL tự động khởi tạo an toàn khi startup)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
