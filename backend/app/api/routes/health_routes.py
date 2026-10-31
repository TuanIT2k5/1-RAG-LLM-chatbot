from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from app.core.config import settings
from app.core.logging import get_logger
from app.database.connection import check_db_connection

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    summary="Kiểm tra trạng thái hoạt động của máy chủ Backend và CSDL",
    response_description="Thông tin trạng thái máy chủ, kết nối PostgreSQL và cấu hình hiện tại",
)
async def health_check() -> Dict[str, Any]:
    """Endpoint kiểm tra tình trạng sẵn sàng của hệ thống (GET /api/health)."""
    db_ok = check_db_connection()
    logger.info(
        "Nhận yêu cầu kiểm tra sức khỏe hệ thống (GET /api/health, db_connected=%s)",
        db_ok,
    )
    return {
        "status": "healthy",
        "database": "connected" if db_ok else "disconnected",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
