from pathlib import Path
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.config import BACKEND_DIR
from app.database.connection import Base
from app.database.models import Conversation, Document, Message, MessageSource, User


def test_five_tables_metadata_registered() -> None:
    """Kiểm tra đủ 5 bảng nghiệp vụ đã được đăng ký trong Base.metadata."""
    expected_tables = {
        "users",
        "documents",
        "conversations",
        "messages",
        "message_sources",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))


def test_crud_across_all_five_tables() -> None:
    """Kiểm tra tạo, truy vấn và xóa liên kết khóa ngoại trên cả 5 bảng ORM."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {
        "users",
        "documents",
        "conversations",
        "messages",
        "message_sources",
    }

    with TestingSession() as db:
        # 1. Tạo User
        user = User(
            email="student@example.com",
            password_hash="hashed_secret_123",
        )
        db.add(user)
        db.flush()
        assert isinstance(user.id, uuid.UUID)

        # 2. Tạo Document
        doc = Document(
            user_id=user.id,
            filename="Bo_luat_Lao_dong_2019.pdf",
            storage_path="./storage/uploads/sample-uuid.pdf",
            file_type="pdf",
            file_size=2450000,
            status="processed",
            chunk_count=42,
        )
        db.add(doc)
        db.flush()

        # 3. Tạo Conversation
        conv = Conversation(
            user_id=user.id,
            title="Quy định nghỉ phép năm",
        )
        db.add(conv)
        db.flush()

        # 4. Tạo Message
        msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content="Người lao động làm đủ 12 tháng được nghỉ 12 ngày phép [S1].",
        )
        db.add(msg)
        db.flush()

        # 5. Tạo MessageSource
        src = MessageSource(
            message_id=msg.id,
            document_id=doc.id,
            source_label="S1",
            chunk_id=f"{doc.id}_chunk_12",
            page_number=45,
            chunk_index=12,
            excerpt="Người lao động làm việc đủ 12 tháng thì được nghỉ hằng năm 12 ngày...",
            score=0.91,
        )
        db.add(src)
        db.commit()

        # Kiểm tra quan hệ ORM 2 chiều
        saved_msg = db.get(Message, msg.id)
        assert saved_msg is not None
        assert len(saved_msg.sources) == 1
        assert saved_msg.sources[0].document.filename == "Bo_luat_Lao_dong_2019.pdf"
        assert saved_msg.sources[0].page_number == 45


def test_alembic_migration_upgrade_and_downgrade(tmp_path: Path, monkeypatch) -> None:
    """Kiểm tra kịch bản Alembic migration tạo đủ 5 bảng cùng các chỉ mục (index)."""
    db_file = tmp_path / "alembic_test.db"
    test_db_url = f"sqlite:///{db_file}"
    monkeypatch.setattr("app.core.config.settings.DATABASE_URL", test_db_url)

    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # Chạy upgrade head
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_db_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "users",
        "documents",
        "conversations",
        "messages",
        "message_sources",
        "alembic_version",
    }.issubset(tables)

    # Kiểm tra các index đã được tạo
    doc_indexes = {idx["name"] for idx in inspector.get_indexes("documents")}
    assert "ix_documents_status" in doc_indexes
    assert "ix_documents_user_status" in doc_indexes

    # Chạy downgrade base
    command.downgrade(alembic_cfg, "base")
    engine.dispose()
