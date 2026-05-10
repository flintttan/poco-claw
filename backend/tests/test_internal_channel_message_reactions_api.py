import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.v1.internal_channel_runtime import router
from app.core.deps import get_db, require_internal_token
from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionOperationResponse,
)


class InternalChannelMessageReactionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.client = TestClient(self.app)
        self.app.dependency_overrides[require_internal_token] = lambda: None
        self.app.dependency_overrides[get_db] = lambda: object()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.internal_channel_runtime.service.add_agent_reaction")
    def test_add_internal_reaction_uses_session_scope(self, add_reaction) -> None:
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()
        add_reaction.return_value = ServerChannelMessageReactionOperationResponse(
            action="add_channel_message_reaction",
            message_id=message_id,
        )

        response = self.client.post(
            f"/api/v1/internal/channel-runtime/reactions/add?session_id={session_id}",
            json={"message_id": str(message_id), "emoji": "👍"},
        )

        self.assertEqual(response.status_code, 200)
        add_reaction.assert_called_once()
        self.assertEqual(add_reaction.call_args.kwargs["session_id"], session_id)

    @patch("app.api.v1.internal_channel_runtime.service.remove_agent_reaction")
    def test_remove_internal_reaction_uses_session_scope(self, remove_reaction) -> None:
        session_id = uuid.uuid4()
        message_id = uuid.uuid4()
        remove_reaction.return_value = ServerChannelMessageReactionOperationResponse(
            action="remove_channel_message_reaction",
            message_id=message_id,
        )

        response = self.client.post(
            f"/api/v1/internal/channel-runtime/reactions/remove?session_id={session_id}",
            json={"message_id": str(message_id), "emoji": "✅"},
        )

        self.assertEqual(response.status_code, 200)
        remove_reaction.assert_called_once()
        self.assertEqual(remove_reaction.call_args.kwargs["session_id"], session_id)


if __name__ == "__main__":
    unittest.main()
