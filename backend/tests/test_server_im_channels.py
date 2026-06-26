"""Tests for the server-scoped IM channels endpoint.

Mounted at ``GET /api/v1/servers/{server_id}/im-channels``. Used by
the server-detail page to populate the "Linked IM chats" panel.
"""

from __future__ import annotations

# Provide S3 env stubs before importing any module that initialises
# ``S3StorageService`` (transitively imported via ``app.api.v1``).
# We only need the endpoint function, but Python resolves its
# parent package before letting us import it, which triggers
# ``app.api.v1/__init__.py`` → many submodules → S3StorageService.
import os

os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("S3_ENDPOINT", "https://test.s3.local")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

import importlib
import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import AppException
from app.core.settings import get_settings
from app.models.im import Channel
from app.models.server import Server
from app.models.server_member import ServerMember
from app.models.user import User


# Import the endpoint function without triggering the full
# ``app.api.v1`` package init (which would pull in modules that
# require live S3 credentials). We load the submodule directly.
get_settings.cache_clear()
_module = importlib.import_module("app.api.v1.server_im_channels")
list_server_im_channels = _module.list_server_im_channels


def _user(user_id: str = "u-mine") -> User:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def _channel(
    *,
    channel_id: int = 1,
    server_id: uuid.UUID | None = None,
    provider: str = "feishu",
    destination: str = "oc-test",
    chat_type: str = "group",
    enabled: bool = True,
) -> Channel:
    channel = MagicMock(spec=Channel)
    channel.id = channel_id
    channel.server_id = server_id
    channel.provider = provider
    channel.destination = destination
    channel.chat_type = chat_type
    channel.enabled = enabled
    channel.last_bound_by_user_id = None
    channel.last_bound_at = None
    return channel


def _membership(*, status: str = "active") -> ServerMember:
    m = MagicMock(spec=ServerMember)
    m.status = status
    return m


def _server(server_id: uuid.UUID) -> Server:
    server = MagicMock(spec=Server)
    server.id = server_id
    server.is_deleted = False
    return server


class ListServerImChannelsEndpointTests(unittest.IsolatedAsyncioTestCase):
    """Cover the API endpoint that returns bound channels for a server."""

    async def test_member_receives_their_server_channels(self) -> None:
        server_id = uuid.uuid4()
        channels = [
            _channel(channel_id=10, server_id=server_id, destination="oc-a"),
            _channel(channel_id=11, server_id=server_id, destination="oc-b"),
        ]

        db = MagicMock()
        user = _user()

        with (
            patch.object(_module, "ServerRepository") as server_repo_mock,
            patch.object(_module, "ServerMemberRepository") as member_repo_mock,
            patch.object(_module, "ChannelRepository") as channel_repo_mock,
        ):
            server_repo_mock.get_by_id.return_value = _server(server_id)
            member_repo_mock.get_by_server_and_user.return_value = _membership()
            channel_repo_mock.list_by_server.return_value = channels

            response = await list_server_im_channels(
                server_id=server_id,
                current_user=user,
                db=db,
            )

        # Endpoint returned a JSONResponse wrapping the rows.
        self.assertIsNotNone(response)
        channel_repo_mock.list_by_server.assert_called_once_with(
            db, server_id=server_id
        )

    async def test_non_member_rejected_with_403(self) -> None:
        server_id = uuid.uuid4()
        db = MagicMock()
        user = _user()

        with (
            patch.object(_module, "ServerRepository") as server_repo_mock,
            patch.object(_module, "ServerMemberRepository") as member_repo_mock,
        ):
            server_repo_mock.get_by_id.return_value = _server(server_id)
            member_repo_mock.get_by_server_and_user.return_value = None

            with self.assertRaises(AppException) as cm:
                await list_server_im_channels(
                    server_id=server_id,
                    current_user=user,
                    db=db,
                )

        self.assertEqual(cm.exception.error_code, ErrorCode.FORBIDDEN)

    async def test_inactive_member_rejected(self) -> None:
        server_id = uuid.uuid4()
        db = MagicMock()
        user = _user()

        with (
            patch.object(_module, "ServerRepository") as server_repo_mock,
            patch.object(_module, "ServerMemberRepository") as member_repo_mock,
        ):
            server_repo_mock.get_by_id.return_value = _server(server_id)
            member_repo_mock.get_by_server_and_user.return_value = _membership(
                status="left"
            )

            with self.assertRaises(AppException) as cm:
                await list_server_im_channels(
                    server_id=server_id,
                    current_user=user,
                    db=db,
                )

        self.assertEqual(cm.exception.error_code, ErrorCode.FORBIDDEN)

    async def test_missing_server_rejected_with_404(self) -> None:
        server_id = uuid.uuid4()
        db = MagicMock()
        user = _user()

        with patch.object(_module, "ServerRepository") as server_repo_mock:
            server_repo_mock.get_by_id.return_value = None

            with self.assertRaises(AppException) as cm:
                await list_server_im_channels(
                    server_id=server_id,
                    current_user=user,
                    db=db,
                )

        self.assertEqual(cm.exception.error_code, ErrorCode.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
