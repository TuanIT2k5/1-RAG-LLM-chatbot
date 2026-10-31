"""Script tự động tạo database doc_chatbot (nếu chưa có), chạy Alembic migration và kiểm tra 5 bảng PostgreSQL."""
from pathlib import Path
import subprocess
import sys

# Bổ sung đường dẫn backend vào sys.path
BACKEND_PATH = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_PATH))

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.logging import get_logger, setup_logging  # noqa: E402
from app.database.connection import SessionLocal, engine  # noqa: E402
from app.database.models import (  # noqa: E402
    Conversation,
    Document,
    Message,
    MessageSource,
    User,
)

logger = get_logger("verify_db_tables")


def ensure_postgres_database_exists() -> None:
    """Tự động tạo database 'doc_chatbot' trên PostgreSQL nếu chưa tồn tại."""
    url = make_url(settings.DATABASE_URL)
    if not url.drivername.startswith("postgresql"):
        return

    target_db = url.database
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
            {"dbname": target_db},
        ).scalar()
        if not exists:
            logger.info("Đang khởi tạo database '%s' trên PostgreSQL...", target_db)
            conn.execute(text(f'CREATE DATABASE "{target_db}" ENCODING \'UTF8\''))
            logger.info("Đã tạo database '%s' thành công!", target_db)
        else:
            logger.info("Database '%s' đã tồn tại trên PostgreSQL.", target_db)


def run_alembic_upgrade() -> None:
    """Chạy lệnh alembic upgrade head để khởi tạo toàn bộ 5 bảng và index."""
    logger.info("Đang chạy Alembic migration (alembic upgrade head)...")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_PATH),
        check=True,
    )


def verify_five_tables() -> None:
    setup_logging()
    ensure_postgres_database_exists()
    run_alembic_upgrade()

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info("Các bảng hiện có trong CSDL: %s", tables)

    expected = {"users", "documents", "conversations", "messages", "message_sources"}
    missing = expected - set(tables)
    if missing:
        raise RuntimeError(f"Thiếu các bảng CSDL: {missing}")

    with SessionLocal() as db:
        # Tạo thử bản ghi trên cả 5 bảng trong 1 transaction rồi rollback để giữ sạch DB
        user = User(email="verify_sprint1@example.com", password_hash="hashed_pw")
        db.add(user)
        db.flush()

        doc = Document(
            user_id=user.id,
            filename="Tai_lieu_kiem_thu.pdf",
            storage_path="./storage/uploads/test.pdf",
            file_type="pdf",
            file_size=102400,
            status="processed",
            chunk_count=5,
        )
        db.add(doc)
        db.flush()

        conv = Conversation(user_id=user.id, title="Hội thoại kiểm thử Sprint 1")
        db.add(conv)
        db.flush()

        msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content="Câu trả lời kiểm thử có trích dẫn [S1].",
        )
        db.add(msg)
        db.flush()

        src = MessageSource(
            message_id=msg.id,
            document_id=doc.id,
            source_label="S1",
            chunk_id=f"{doc.id}_chunk_1",
            page_number=1,
            chunk_index=0,
            excerpt="Đoạn văn bản gốc dùng để kiểm chứng.",
            score=0.95,
        )
        db.add(src)
        db.flush()

        count_res = db.execute(text("SELECT COUNT(*) FROM message_sources")).scalar()
        logger.info(
            "Tạo thử bản ghi trên 5 bảng thành công! (user_id=%s, doc_id=%s, conv_id=%s, msg_id=%s, src_id=%s, total_sources_in_tx=%s)",
            user.id,
            doc.id,
            conv.id,
            msg.id,
            src.id,
            count_res,
        )
        db.rollback()
        logger.info("Đã rollback dữ liệu kiểm thử thành công. CSDL sẵn sàng!")


if __name__ == "__main__":
    verify_five_tables()
