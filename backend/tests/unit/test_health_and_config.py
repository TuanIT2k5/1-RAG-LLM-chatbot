from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.logging import LOG_FILE_PATH, setup_logging
from app.main import app


def test_settings_loaded_correctly() -> None:
    """Kiểm tra Pydantic BaseSettings đọc đúng cấu hình mặc định / .env."""
    assert settings.APP_NAME == "Intelligent Document Chatbot"
    assert settings.CHUNK_SIZE == 400
    assert settings.CHUNK_OVERLAP == 60
    assert settings.TOP_K == 5
    assert settings.EMBEDDING_MODEL_NAME == "BAAI/bge-m3"
    assert "http://localhost:5173" in settings.cors_origins_list


def test_logging_creates_log_file() -> None:
    """Kiểm tra module logging khởi tạo và ghi ra file logs/app.log."""
    logger = setup_logging()
    logger.info("Test log entry from pytest")
    assert LOG_FILE_PATH.exists()


def test_health_check_endpoint() -> None:
    """Kiểm tra endpoint GET /api/health trả về HTTP 200 và dữ liệu chuẩn."""
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == settings.APP_NAME
        assert "timestamp" in data

