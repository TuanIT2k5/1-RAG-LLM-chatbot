from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.database.connection import Base
import app.database.models  # noqa: F401 - Đăng ký toàn bộ 5 bảng ORM vào Base.metadata

# Đối tượng cấu hình Alembic đọc từ alembic.ini
config = context.config

# Ghi đè sqlalchemy.url bằng giá trị thực tế từ settings.DATABASE_URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Thiết lập logging cho Alembic
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy migrations ở chế độ 'offline' (sinh câu lệnh SQL mà không cần kết nối DB)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migrations ở chế độ 'online' (kết nối trực tiếp tới CSDL)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

