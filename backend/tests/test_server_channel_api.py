import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.server_channel import (
    ServerChannelMemberResponse,
    ServerChannelResponse,
)
from app.schemas.user_profile import UserPublicProfileResponse


def build_channel_response(*, server_id: uuid.UUID) -> ServerChannelResponse:
    now = datetime.now(UTC)
    return ServerChannelResponse(
        channel_id=uuid.uuid4(),
        server_id=server_id,
        name="planning",
        slug="planning",
        description="Roadmap planning",
        conversation_type="channel",
        visibility="public",
        direct_user_id=None,
        direct_agent_identity_id=None,
        created_by="user-1",
        archived_at=None,
        created_at=now,
        updated_at=now,
    )


def build_member_response(*, channel_id: uuid.UUID) -> ServerChannelMemberResponse:
    now = datetime.now(UTC)
    return ServerChannelMemberResponse(
        membership_id=1,
        channel_id=channel_id,
        user_id="user-2",
        user=UserPublicProfileResponse(
            user_id="user-2",
            display_name="Bob",
            avatar_url="https://example.com/bob.png",
        ),
        role="member",
        joined_at=now,
        status="active",
        created_at=now,
        updated_at=now,
    )


class ServerChannelApiTests(unittest.TestCase):
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

    @patch("app.api.v1.server_channels.service.update_channel")
    def test_update_server_channel_returns_channel_payload(
        self, update_channel
    ) -> None:
        server_id = uuid.uuid4()
        channel = build_channel_response(server_id=server_id)
        update_channel.return_value = channel

        response = self.client.patch(
            f"/api/v1/servers/{server_id}/channels/{channel.channel_id}",
            json={"name": "planning", "description": "Roadmap planning"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["channel_id"], str(channel.channel_id))
        self.assertEqual(body["data"]["description"], "Roadmap planning")
        update_channel.assert_called_once()

    @patch("app.api.v1.server_channels.service.delete_channel")
    def test_delete_server_channel_returns_deleted_id(self, delete_channel) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()

        response = self.client.delete(
            f"/api/v1/servers/{server_id}/channels/{channel_id}",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["channel_id"], str(channel_id))
        delete_channel.assert_called_once()

    @patch("app.api.v1.server_channels.service.list_channel_members")
    def test_list_channel_members_returns_human_members(
        self, list_channel_members
    ) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        member = build_member_response(channel_id=channel_id)
        list_channel_members.return_value = [member]

        response = self.client.get(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/members",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["user_id"], "user-2")
        self.assertEqual(body["data"][0]["user"]["display_name"], "Bob")
        list_channel_members.assert_called_once()

    @patch("app.api.v1.server_channels.service.add_channel_member")
    def test_add_channel_member_returns_membership(self, add_channel_member) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        member = build_member_response(channel_id=channel_id)
        add_channel_member.return_value = member

        response = self.client.post(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/members",
            json={"user_id": "user-2"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["user_id"], "user-2")
        self.assertEqual(
            body["data"]["user"]["avatar_url"], "https://example.com/bob.png"
        )
        add_channel_member.assert_called_once()

    @patch("app.api.v1.server_channels.service.remove_channel_member")
    def test_remove_channel_member_returns_removed_id(
        self, remove_channel_member
    ) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()

        response = self.client.delete(
            f"/api/v1/servers/{server_id}/channels/{channel_id}/members/12",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["membership_id"], 12)
        remove_channel_member.assert_called_once()


if __name__ == "__main__":
    unittest.main()
