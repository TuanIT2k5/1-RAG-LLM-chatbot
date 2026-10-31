import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from app.core.config import BACKEND_DIR, settings

LOG_DIR = BACKEND_DIR / "logs"
LOG_FILE_PATH = LOG_DIR / "app.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Thiết lập cấu hình ghi nhật ký chuẩn ra cả Console và File (UTF-8)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Xóa các handler cũ nếu hàm được gọi lại để tránh nhân bản dòng log
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 1. Console Handler (stdout với UTF-8)
    console_stream = (
        open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        if hasattr(sys.stdout, "fileno")
        else sys.stdout
    )
    console_handler = logging.StreamHandler(stream=console_stream)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # 2. Rotating File Handler (tối đa 10MB/file, lưu tối đa 5 bản sao lưu)
    file_handler = RotatingFileHandler(
        filename=LOG_FILE_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Đồng bộ mức log cho uvicorn
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = root_logger.handlers
        uvicorn_logger.propagate = False

    app_logger = logging.getLogger(settings.APP_NAME)
    app_logger.info(
        "Hệ thống Logging đã khởi tạo thành công (env=%s, file=%s)",
        settings.APP_ENV,
        LOG_FILE_PATH,
    )
    return app_logger


def get_logger(module_name: str) -> logging.Logger:
    """Trả về logger gắn với tên module cụ thể."""
    return logging.getLogger(module_name)

