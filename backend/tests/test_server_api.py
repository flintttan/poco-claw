import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.deps import get_current_user, get_db
from app.main import create_app
from app.models.user import User
from app.schemas.server import ServerResponse
from app.schemas.server_channel import ServerChannelResponse
from app.schemas.server_invite import ServerInviteResponse
from app.schemas.server_member import ServerMemberResponse
from app.schemas.user_profile import UserPublicProfileResponse


def build_server_response() -> ServerResponse:
    now = datetime.now(UTC)
    return ServerResponse(
        server_id=uuid.uuid4(),
        name="Poco Core",
        slug="poco-core",
        kind="shared",
        owner_user_id="user-1",
        created_at=now,
        updated_at=now,
    )


def build_channel_response(server_id: uuid.UUID) -> ServerChannelResponse:
    now = datetime.now(UTC)
    return ServerChannelResponse(
        channel_id=uuid.uuid4(),
        server_id=server_id,
        name="general",
        slug="general",
        conversation_type="channel",
        visibility="public",
        created_by="user-1",
        archived_at=None,
        created_at=now,
        updated_at=now,
    )


class ServerApiTests(unittest.TestCase):
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

    @patch("app.api.v1.servers.service.list_servers")
    def test_list_servers_returns_response_envelope(self, list_servers) -> None:
        server = build_server_response()
        list_servers.return_value = [server]

        response = self.client.get("/api/v1/servers")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"][0]["server_id"], str(server.server_id))
        self.assertEqual(body["data"][0]["slug"], "poco-core")
        list_servers.assert_called_once()

    @patch("app.api.v1.server_channels.service.create_channel")
    def test_create_server_channel_returns_channel_payload(
        self,
        create_channel,
    ) -> None:
        server_id = uuid.uuid4()
        channel = build_channel_response(server_id)
        create_channel.return_value = channel

        response = self.client.post(
            f"/api/v1/servers/{server_id}/channels",
            json={"name": "general", "visibility": "public"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["channel_id"], str(channel.channel_id))
        self.assertEqual(body["data"]["visibility"], "public")
        create_channel.assert_called_once()

    @patch("app.api.v1.server_invites.service.accept_invite")
    def test_accept_server_invite_returns_member_payload(self, accept_invite) -> None:
        now = datetime.now(UTC)
        server_id = uuid.uuid4()
        accept_invite.return_value = ServerMemberResponse(
            membership_id=1,
            server_id=server_id,
            user_id="user-2",
            user=UserPublicProfileResponse(
                user_id="user-2",
                display_name="Bob",
                avatar_url="https://example.com/bob.png",
            ),
            role="member",
            joined_at=now,
            invited_by="user-1",
            status="active",
            created_at=now,
            updated_at=now,
        )

        response = self.client.post(
            "/api/v1/server-invites/accept",
            json={"token": "invite-token"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["server_id"], str(server_id))
        self.assertEqual(body["data"]["user"]["display_name"], "Bob")
        accept_invite.assert_called_once()

    @patch("app.api.v1.server_invites.service.create_invite")
    def test_create_server_invite_returns_invite_payload(self, create_invite) -> None:
        now = datetime.now(UTC)
        server_id = uuid.uuid4()
        create_invite.return_value = ServerInviteResponse(
            invite_id=uuid.uuid4(),
            server_id=server_id,
            token="invite-token",
            role="member",
            expires_at=now,
            created_by="user-1",
            max_uses=1,
            used_count=0,
            revoked_at=None,
            created_at=now,
            updated_at=now,
        )

        response = self.client.post(
            f"/api/v1/servers/{server_id}/invites",
            json={"role": "member", "expires_in_days": 7, "max_uses": 1},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 0)
        self.assertEqual(body["data"]["token"], "invite-token")
        create_invite.assert_called_once()


if __name__ == "__main__":
    unittest.main()
