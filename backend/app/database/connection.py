from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Lớp cơ sở cho toàn bộ các bảng SQLAlchemy ORM."""

    pass


# Khởi tạo SQLAlchemy Engine (hỗ trợ cả PostgreSQL và SQLite khi chạy unit test)
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args,
)

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

