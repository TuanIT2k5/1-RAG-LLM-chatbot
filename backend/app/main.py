from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.chat_routes import router as chat_router
from app.api.routes.conversation_routes import router as conversation_router
from app.api.routes.document_routes import router as document_router
from app.api.routes.health_routes import router as health_router
from app.core.config import BACKEND_DIR, settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.database import models as _models  # noqa: F401
from app.database.connection import Base, engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Quản lý vòng đời khởi động và đóng ứng dụng FastAPI."""
    setup_logging()

    # Đảm bảo thư mục lưu trữ cục bộ (uploads, chroma_db) luôn tồn tại
    upload_path = Path(settings.UPLOAD_DIR)
    if not upload_path.is_absolute():
        upload_path = (BACKEND_DIR / upload_path).resolve()
    chroma_path = Path(settings.CHROMA_PERSIST_DIR)
    if not chroma_path.is_absolute():
        chroma_path = (BACKEND_DIR / chroma_path).resolve()

    upload_path.mkdir(parents=True, exist_ok=True)
    chroma_path.mkdir(parents=True, exist_ok=True)

    # Đảm bảo các bảng dữ liệu (users, documents, conversations, messages, message_sources) đã được tạo
    Base.metadata.create_all(bind=engine)

    logger.info(
        "Khởi động %s v%s thành công tại cổng %d",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.API_PORT,
    )
    yield
    logger.info("Đang đóng ứng dụng %s...", settings.APP_NAME)


def create_app() -> FastAPI:
    """Khởi tạo và cấu hình thực thể FastAPI Application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Hệ thống hỏi đáp tài liệu thông minh (PDF/DOCX) ứng dụng Large Language Model (LLM) "
            "và Retrieval-Augmented Generation (RAG) kèm trích dẫn nguồn xác thực."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Tích hợp CORSMiddleware cho phép Frontend ReactJS kết nối
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Xử lý ngoại lệ chuẩn hóa toàn cục (AppException)
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.error(
            "AppException [%s] tại %s: %s",
            exc.error_code,
            request.url.path,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled Exception (HTTP 500) tại %s: %s",
            request.url.path,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": f"Lỗi xử lý nội bộ trên máy chủ: {exc}",
            },
        )

    # Đăng ký các Routers dưới tiền tố /api
    app.include_router(health_router, prefix="/api")
    app.include_router(document_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(conversation_router, prefix="/api")

    @app.get("/", tags=["Root"], summary="Trang chào mừng API")
    async def root() -> dict:
        return {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs_url": "/docs",
            "health_url": "/api/health",
        }

    return app


app = create_app()

