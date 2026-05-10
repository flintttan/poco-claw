import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.internal_runs import router
from app.services.run_pull_service import RunPullService


class InternalRunsNotifyTests(unittest.TestCase):
    def test_notify_endpoint_triggers_background_poll(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        service = RunPullService.__new__(RunPullService)
        service.poll = AsyncMock()
        app.state.run_pull_service = service
        settings = MagicMock(
            task_pull_enabled=True,
            task_pull_notify_enabled=True,
            internal_api_token="internal-token",
        )

        created_coroutines = []

        def capture_create_task(coro):
            created_coroutines.append(coro)
            return MagicMock()

        with (
            patch("app.api.v1.internal_runs.get_settings", return_value=settings),
            patch(
                "app.core.deps.get_settings",
                return_value=settings,
            ),
            patch(
                "app.api.v1.internal_runs.asyncio.create_task",
                side_effect=capture_create_task,
            ),
        ):
            response = TestClient(app).post(
                "/api/v1/internal/runs/notify",
                json={"run_id": "run-1", "schedule_mode": "immediate"},
                headers={"X-Internal-Token": "internal-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["accepted"])
        self.assertEqual(len(created_coroutines), 1)
        asyncio.run(created_coroutines[0])
        service.poll.assert_awaited_once_with(
            schedule_modes=["immediate"],
            trigger_source="notify",
        )

    def test_notify_endpoint_requires_internal_token(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        settings = MagicMock(
            task_pull_enabled=True,
            task_pull_notify_enabled=True,
            internal_api_token="internal-token",
        )

        with patch("app.core.deps.get_settings", return_value=settings):
            response = TestClient(app).post(
                "/api/v1/internal/runs/notify",
                json={"run_id": "run-1", "schedule_mode": "immediate"},
            )

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
