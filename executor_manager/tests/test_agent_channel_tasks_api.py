import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.agent_channel_tasks import router


class AgentChannelTasksApiTests(unittest.TestCase):
    def test_list_tasks_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_tasks.backend_client.list_agent_channel_tasks",
            new=AsyncMock(return_value={"tasks": []}),
        ) as list_tasks:
            response = TestClient(app).post(
                "/api/v1/agent-channel-tasks/list",
                json={"session_id": "session-1", "status": "todo", "limit": 20},
            )

        self.assertEqual(response.status_code, 200)
        list_tasks.assert_awaited_once_with(
            "session-1",
            {"status": "todo", "limit": 20},
        )

    def test_read_task_proxies_session_payload(self) -> None:
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        with patch(
            "app.api.v1.agent_channel_tasks.backend_client.read_agent_channel_task",
            new=AsyncMock(return_value={"task": {"title": "Review"}}),
        ) as read_task:
            response = TestClient(app).post(
                "/api/v1/agent-channel-tasks/read",
                json={"session_id": "session-1", "task_id": "task-1"},
            )

        self.assertEqual(response.status_code, 200)
        read_task.assert_awaited_once_with(
            "session-1",
            {"task_id": "task-1"},
        )


if __name__ == "__main__":
    unittest.main()
