import logging
from uuid import UUID

import httpx

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class ExecutorManagerNotifyService:
    """Best-effort notifier for executor-manager run pull wakeups."""

    async def notify_run_enqueued(
        self,
        *,
        run_id: UUID,
        schedule_mode: str,
        session_id: UUID | None = None,
    ) -> bool:
        settings = get_settings()
        if not settings.executor_manager_run_notify_enabled:
            return False

        base_url = (settings.executor_manager_url or "").strip().rstrip("/")
        if not base_url:
            return False

        payload: dict[str, str] = {
            "run_id": str(run_id),
            "schedule_mode": schedule_mode,
        }
        if session_id is not None:
            payload["session_id"] = str(session_id)

        timeout_seconds = max(
            0.1,
            float(settings.executor_manager_run_notify_timeout_seconds),
        )
        try:
            async with httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(timeout_seconds),
                trust_env=False,
            ) as client:
                response = await client.post(
                    "/api/v1/internal/runs/notify",
                    json=payload,
                    headers={"X-Internal-Token": settings.internal_api_token},
                )
                response.raise_for_status()
        except Exception as exc:
            logger.info(
                "executor_manager_run_notify_failed",
                extra={
                    "run_id": str(run_id),
                    "session_id": str(session_id) if session_id else None,
                    "schedule_mode": schedule_mode,
                    "error_type": type(exc).__name__,
                },
            )
            return False

        logger.info(
            "executor_manager_run_notify_sent",
            extra={
                "run_id": str(run_id),
                "session_id": str(session_id) if session_id else None,
                "schedule_mode": schedule_mode,
            },
        )
        return True
