import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.server_channel_message import (
    ServerChannelMessageResponse,
    ServerChannelThreadResponse,
)
from app.schemas.user_profile import UserPublicProfileResponse


def build_message_response(
    *,
    channel_id: uuid.UUID,
    thread_root_message_id: uuid.UUID | None = None,
) -> ServerChannelMessageResponse:
    now = datetime.now(UTC)
    return ServerChannelMessageResponse(
        message_id=uuid.uuid4(),
        channel_id=channel_id,
        author_user_id="user-1",
        author_user=UserPublicProfileResponse(
            user_id="user-1",
            display_name="Alice",
            avatar_url="https://example.com/alice.png",
        ),
        message_type="user",
        content={"text": "hello"},
        text_preview="hello",
        thread_root_message_id=thread_root_message_id,
        created_at=now,
        updated_at=now,
    )


class ServerChannelMessageApiTests(unittest.TestCase):
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

    @patch("app.api.v1.server_channel_messages.service.send_message")
    def test_send_channel_message_returns_message_payload(self, send_message) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        message = build_message_response(channel_id=channel_id)
        send_message.return_value = message

        response = self.client.post(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/messages",
            json={"content": {"text": "hello"}, "text_preview": "hello"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["message_id"], str(message.message_id))
        self.assertEqual(body["data"]["message_type"], "user")
        self.assertEqual(body["data"]["author_user"]["display_name"], "Alice")
        send_message.assert_called_once()

    @patch("app.api.v1.server_channel_messages.service.list_messages")
    def test_list_channel_messages_returns_history(self, list_messages) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        message = build_message_response(channel_id=channel_id)
        list_messages.return_value = [message]

        response = self.client.get(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/messages",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["message_id"], str(message.message_id))
        self.assertEqual(
            body["data"][0]["author_user"]["avatar_url"],
            "https://example.com/alice.png",
        )
        list_messages.assert_called_once()

    @patch("app.api.v1.server_channel_messages.service.get_thread")
    def test_get_channel_thread_returns_root_and_replies(self, get_thread) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        root = build_message_response(channel_id=channel_id)
        reply = build_message_response(
            channel_id=channel_id,
            thread_root_message_id=root.message_id,
        )
        get_thread.return_value = ServerChannelThreadResponse(
            root=root, replies=[reply]
        )

        response = self.client.get(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/threads/{root.message_id}",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["root"]["message_id"], str(root.message_id))
        self.assertEqual(
            body["data"]["replies"][0]["message_id"], str(reply.message_id)
        )
        self.assertEqual(body["data"]["root"]["author_user"]["display_name"], "Alice")
        get_thread.assert_called_once()


if __name__ == "__main__":
    unittest.main()
