import unittest
import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.internal_channel_runtime import router
from app.core.deps import get_db, require_internal_token
from app.schemas.channel_runtime import (
    AgentChannelAgentsListResponse,
    AgentChannelCollaborationResponse,
    AgentChannelMessagesReadResponse,
)


class InternalChannelRuntimeApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.client = TestClient(self.app)
        self.app.dependency_overrides[require_internal_token] = lambda: None
        self.app.dependency_overrides[get_db] = lambda: object()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.internal_channel_runtime.runtime_service.read_messages")
    def test_read_messages_uses_session_scope(self, read_messages) -> None:
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()
        read_messages.return_value = AgentChannelMessagesReadResponse(messages=[])

        response = self.client.post(
            f"/api/v1/internal/channel-runtime/messages/read?session_id={session_id}",
            json={"message_ids": [str(message_id)]},
        )

        self.assertEqual(response.status_code, 200)
        read_messages.assert_called_once()
        self.assertEqual(read_messages.call_args.kwargs["session_id"], session_id)
        self.assertEqual(
            read_messages.call_args.kwargs["request"].message_ids, [message_id]
        )

    @patch("app.api.v1.internal_channel_runtime.runtime_service.list_agents")
    def test_list_agents_uses_session_scope(self, list_agents) -> None:
        session_id = uuid.uuid4()
        list_agents.return_value = AgentChannelAgentsListResponse(agents=[])

        response = self.client.post(
            f"/api/v1/internal/channel-runtime/agents/list?session_id={session_id}",
            json={},
        )

        self.assertEqual(response.status_code, 200)
        list_agents.assert_called_once()
        self.assertEqual(list_agents.call_args.kwargs["session_id"], session_id)

    @patch("app.api.v1.internal_channel_runtime.runtime_service.request_collaboration")
    def test_request_collaboration_uses_session_scope(
        self, request_collaboration
    ) -> None:
        session_id = uuid.uuid4()
        target_agent_id = uuid.uuid4()
        request_collaboration.return_value = AgentChannelCollaborationResponse(
            status="queued",
            target_agent_identity_id=target_agent_id,
            target_agent_handle="api",
            session_id=uuid.uuid4(),
            dedupe_key="dedupe",
        )

        response = self.client.post(
            f"/api/v1/internal/channel-runtime/collaboration/request?session_id={session_id}",
            json={
                "agent_handle": "api",
                "request_text": "Please review this.",
                "mode": "consult",
            },
        )

        self.assertEqual(response.status_code, 200)
        request_collaboration.assert_called_once()
        self.assertEqual(
            request_collaboration.call_args.kwargs["session_id"], session_id
        )
        self.assertEqual(
            request_collaboration.call_args.kwargs["request"].request_text,
            "Please review this.",
        )


if __name__ == "__main__":
    unittest.main()
