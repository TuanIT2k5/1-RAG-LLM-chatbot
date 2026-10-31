from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    summary="Kiểm tra trạng thái hoạt động của máy chủ Backend",
    response_description="Thông tin trạng thái máy chủ và cấu hình hiện tại",
)
async def health_check() -> Dict[str, Any]:
    """Endpoint kiểm tra tình trạng sẵn sàng của hệ thống (GET /api/health)."""
    logger.info("Nhận yêu cầu kiểm tra sức khỏe hệ thống (GET /api/health)")
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

