from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def system_status() -> dict:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "claude_model": settings.claude_model,
        "anthropic_configured": bool(settings.anthropic_api_key),
        "scheduler_enabled": settings.scheduler_enabled,
    }
