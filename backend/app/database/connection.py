from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import BACKEND_DIR, settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Lớp cơ sở cho toàn bộ các bảng SQLAlchemy ORM."""

    pass


def _build_engine() -> Engine:
    """
    Khởi tạo SQLAlchemy Engine:
    - Ưu tiên kết nối tới DATABASE_URL cấu hình trong .env (PostgreSQL hoặc SQLite).
    - Trong môi trường development, nếu PostgreSQL cục bộ chưa bật, tự động chuyển sang
      SQLite cục bộ (./storage/doc_chatbot.sqlite) để lập trình viên chạy thử ngay lập tức.
    """
    db_url = settings.DATABASE_URL
    is_sqlite = db_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}

    primary_engine = create_engine(
        db_url,
        pool_pre_ping=True,
        echo=False,
        connect_args=connect_args,
    )

    if not is_sqlite and settings.APP_ENV == "development":
        try:
            with primary_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            sqlite_path = (BACKEND_DIR / "storage" / "doc_chatbot.sqlite").resolve()
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            fallback_url = f"sqlite:///{sqlite_path.as_posix()}"
            logger.warning(
                "PostgreSQL chưa khởi động (%s). Tự động dùng SQLite cục bộ tại %s cho môi trường development.",
                exc,
                sqlite_path,
            )
            return create_engine(
                fallback_url,
                pool_pre_ping=True,
                echo=False,
                connect_args={"check_same_thread": False},
            )

    return primary_engine


engine = _build_engine()

# Khởi tạo SessionLocal quản lý phiên làm việc với CSDL
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency cung cấp phiên làm việc SQLAlchemy (Session) cho mỗi HTTP Request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Kiểm tra nhanh kết nối tới cơ sở dữ liệu."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Không thể kết nối tới CSDL: %s", exc)
        return False

