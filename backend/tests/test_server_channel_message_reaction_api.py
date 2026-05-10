import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.server_channel_message_reaction import (
    ServerChannelMessageReactionOperationResponse,
)


class ServerChannelMessageReactionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.current_user = User(
            id="user-1",
            primary_email="alice@example.com",
            display_name="Alice",
            avatar_url=None,
            status="active",
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.app.dependency_overrides[get_db] = lambda: object()

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @patch("app.api.v1.server_channel_messages.reaction_service.add_user_reaction")
    def test_add_reaction_returns_payload(self, add_reaction) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        message_id = uuid.uuid4()
        add_reaction.return_value = ServerChannelMessageReactionOperationResponse(
            action="add_channel_message_reaction",
            message_id=message_id,
        )

        response = self.client.post(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/messages/{message_id}/reactions",
            json={"emoji": "👍"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["message_id"], str(message_id))
        add_reaction.assert_called_once()

    @patch("app.api.v1.server_channel_messages.reaction_service.remove_user_reaction")
    def test_remove_reaction_returns_payload(self, remove_reaction) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        message_id = uuid.uuid4()
        remove_reaction.return_value = ServerChannelMessageReactionOperationResponse(
            action="remove_channel_message_reaction",
            message_id=message_id,
        )

        response = self.client.request(
            "DELETE",
            f"/api/v1/servers/{server_id}/channels/{channel_id}/messages/{message_id}/reactions",
            json={"emoji": "✅"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["message_id"], str(message_id))
        remove_reaction.assert_called_once()


if __name__ == "__main__":
    unittest.main()
