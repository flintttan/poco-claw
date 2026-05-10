import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.deps import require_internal_token
from app.core.settings import get_settings
from app.schemas.response import Response, ResponseSchema
from app.schemas.run_notify import RunNotifyRequest
from app.services.run_pull_service import RunPullService

router = APIRouter(prefix="/internal/runs", tags=["internal-runs"])
logger = logging.getLogger(__name__)


@router.post("/notify", response_model=ResponseSchema[dict[str, bool]])
async def notify_run_enqueued(
    payload: RunNotifyRequest,
    request: Request,
    _: None = Depends(require_internal_token),
) -> JSONResponse:
    """Wake the pull loop after Backend materializes a queued run."""
    settings = get_settings()
    if not settings.task_pull_enabled or not settings.task_pull_notify_enabled:
        return Response.success(
            data={"accepted": False},
            message="Run pull notify disabled",
        )

    service = getattr(request.app.state, "run_pull_service", None)
    if not isinstance(service, RunPullService):
        return Response.success(
            data={"accepted": False},
            message="Run pull service unavailable",
        )

    schedule_mode = payload.schedule_mode.strip() or "immediate"
    logger.info(
        "run_pull_notify_received",
        extra={
            "run_id": payload.run_id,
            "session_id": payload.session_id,
            "schedule_mode": schedule_mode,
        },
    )

    asyncio.create_task(
        service.poll(schedule_modes=[schedule_mode], trigger_source="notify")
    )
    return Response.success(data={"accepted": True}, message="Run pull notify accepted")
