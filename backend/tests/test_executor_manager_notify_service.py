import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.executor_manager_notify_service import ExecutorManagerNotifyService


class ExecutorManagerNotifyServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_notify_failure_returns_false(self) -> None:
        settings = MagicMock(
            executor_manager_run_notify_enabled=True,
            executor_manager_url="http://executor-manager",
            executor_manager_run_notify_timeout_seconds=0.5,
            internal_api_token="internal-token",
        )
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.post.side_effect = httpx.ConnectError("offline")

        with (
            patch(
                "app.services.executor_manager_notify_service.get_settings",
                return_value=settings,
            ),
            patch(
                "app.services.executor_manager_notify_service.httpx.AsyncClient",
                return_value=client,
            ),
        ):
            sent = await ExecutorManagerNotifyService().notify_run_enqueued(
                run_id=uuid4(),
                session_id=uuid4(),
                schedule_mode="immediate",
            )

        self.assertFalse(sent)

    async def test_notify_sends_internal_token(self) -> None:
        settings = MagicMock(
            executor_manager_run_notify_enabled=True,
            executor_manager_url="http://executor-manager",
            executor_manager_run_notify_timeout_seconds=0.5,
            internal_api_token="internal-token",
        )
        response = MagicMock()
        response.raise_for_status.return_value = None
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None
        client.post.return_value = response
        run_id = uuid4()

        with (
            patch(
                "app.services.executor_manager_notify_service.get_settings",
                return_value=settings,
            ),
            patch(
                "app.services.executor_manager_notify_service.httpx.AsyncClient",
                return_value=client,
            ),
        ):
            sent = await ExecutorManagerNotifyService().notify_run_enqueued(
                run_id=run_id,
                schedule_mode="immediate",
            )

        self.assertTrue(sent)
        client.post.assert_awaited_once()
        _, kwargs = client.post.await_args
        self.assertEqual(kwargs["headers"]["X-Internal-Token"], "internal-token")
        self.assertEqual(kwargs["json"]["run_id"], str(run_id))


if __name__ == "__main__":
    unittest.main()
