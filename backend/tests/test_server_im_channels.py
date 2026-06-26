"""Tests for the server-scoped IM channels API and service."""

from __future__ import annotations

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
from app.models.user import User
from app.schemas.im_binding import ServerImChannelUpdateRequest
from app.schemas.user_profile import UserPublicProfileResponse
from app.services.server_im_channel_service import ServerImChannelService

get_settings.cache_clear()
_api_module = importlib.import_module("app.api.v1.server_im_channels")
list_server_im_channels = _api_module.list_server_im_channels
update_server_im_channel = _api_module.update_server_im_channel
unbind_server_im_channel = _api_module.unbind_server_im_channel


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
    last_bound_by_user_id: str | None = "u-owner",
) -> Channel:
    channel = MagicMock(spec=Channel)
    channel.id = channel_id
    channel.server_id = server_id
    channel.provider = provider
    channel.destination = destination
    channel.chat_type = chat_type
    channel.enabled = enabled
    channel.last_bound_by_user_id = last_bound_by_user_id
    channel.last_bound_at = None
    return channel


def _server(server_id: uuid.UUID) -> Server:
    server = MagicMock(spec=Server)
    server.id = server_id
    server.is_deleted = False
    return server


def _profile(user_id: str, display_name: str = "Owner") -> UserPublicProfileResponse:
    return UserPublicProfileResponse(user_id=user_id, display_name=display_name)


class ListServerImChannelsEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_endpoint_returns_service_rows(self) -> None:
        server_id = uuid.uuid4()
        user = _user()
        db = MagicMock()
        row = MagicMock()

        with patch.object(_api_module, "service") as service_mock:
            service_mock.list_channels.return_value = [row]
            response = await list_server_im_channels(
                server_id=server_id,
                current_user=user,
                db=db,
            )

        self.assertIsNotNone(response)
        service_mock.list_channels.assert_called_once_with(db, user, server_id)

    async def test_update_endpoint_calls_service(self) -> None:
        server_id = uuid.uuid4()
        user = _user()
        db = MagicMock()
        request = ServerImChannelUpdateRequest(enabled=False)

        with patch.object(_api_module, "service") as service_mock:
            service_mock.update_channel.return_value = MagicMock()
            response = await update_server_im_channel(
                server_id=server_id,
                channel_id=7,
                request=request,
                current_user=user,
                db=db,
            )

        self.assertIsNotNone(response)
        service_mock.update_channel.assert_called_once_with(
            db,
            user,
            server_id,
            7,
            request,
        )

    async def test_unbind_endpoint_calls_service(self) -> None:
        server_id = uuid.uuid4()
        user = _user()
        db = MagicMock()

        with patch.object(_api_module, "service") as service_mock:
            response = await unbind_server_im_channel(
                server_id=server_id,
                channel_id=11,
                current_user=user,
                db=db,
            )

        self.assertIsNotNone(response)
        service_mock.unbind_channel.assert_called_once_with(db, user, server_id, 11)


class ServerImChannelServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ServerImChannelService()
        self.db = MagicMock()
        self.current_user = _user()

    def test_list_requires_existing_server(self) -> None:
        server_id = uuid.uuid4()
        with patch(
            "app.services.server_im_channel_service.ServerRepository.get_by_id",
            return_value=None,
        ):
            with self.assertRaises(AppException) as cm:
                self.service.list_channels(self.db, self.current_user, server_id)
        self.assertEqual(cm.exception.error_code, ErrorCode.NOT_FOUND)

    def test_list_returns_profile_enriched_rows(self) -> None:
        server_id = uuid.uuid4()
        channels = [
            _channel(channel_id=1, server_id=server_id, last_bound_by_user_id="u-owner")
        ]
        with (
            patch(
                "app.services.server_im_channel_service.ServerRepository.get_by_id",
                return_value=_server(server_id),
            ),
            patch("app.services.server_im_channel_service.require_server_member"),
            patch(
                "app.services.server_im_channel_service.ChannelRepository.list_by_server",
                return_value=channels,
            ),
            patch(
                "app.services.server_im_channel_service.list_user_public_profiles_by_id",
                return_value={"u-owner": _profile("u-owner", "Alice")},
            ),
        ):
            rows = self.service.list_channels(self.db, self.current_user, server_id)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].last_bound_by_user_id, "u-owner")
        self.assertIsNotNone(rows[0].last_bound_by_user)
        self.assertEqual(rows[0].last_bound_by_user.display_name, "Alice")

    def test_update_requires_admin(self) -> None:
        server_id = uuid.uuid4()
        with (
            patch(
                "app.services.server_im_channel_service.ServerRepository.get_by_id",
                return_value=_server(server_id),
            ),
            patch(
                "app.services.server_im_channel_service.require_server_admin",
                side_effect=AppException(
                    error_code=ErrorCode.FORBIDDEN,
                    message="forbidden",
                ),
            ),
        ):
            with self.assertRaises(AppException) as cm:
                self.service.update_channel(
                    self.db,
                    self.current_user,
                    server_id,
                    3,
                    ServerImChannelUpdateRequest(enabled=False),
                )
        self.assertEqual(cm.exception.error_code, ErrorCode.FORBIDDEN)

    def test_update_changes_enabled_and_commits(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(channel_id=3, server_id=server_id, enabled=True)
        with (
            patch(
                "app.services.server_im_channel_service.ServerRepository.get_by_id",
                return_value=_server(server_id),
            ),
            patch("app.services.server_im_channel_service.require_server_admin"),
            patch(
                "app.services.server_im_channel_service.ChannelRepository.get_by_id",
                return_value=channel,
            ),
            patch(
                "app.services.server_im_channel_service.list_user_public_profiles_by_id",
                return_value={},
            ),
        ):
            row = self.service.update_channel(
                self.db,
                self.current_user,
                server_id,
                3,
                ServerImChannelUpdateRequest(enabled=False),
            )

        self.assertFalse(channel.enabled)
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(channel)
        self.assertFalse(row.enabled)

    def test_unbind_clears_server_binding_and_commits(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(channel_id=8, server_id=server_id)
        channel.server_channel_id = uuid.uuid4()
        channel.last_bound_at = MagicMock()
        with (
            patch(
                "app.services.server_im_channel_service.ServerRepository.get_by_id",
                return_value=_server(server_id),
            ),
            patch("app.services.server_im_channel_service.require_server_admin"),
            patch(
                "app.services.server_im_channel_service.ChannelRepository.get_by_id",
                return_value=channel,
            ),
        ):
            self.service.unbind_channel(self.db, self.current_user, server_id, 8)

        self.assertIsNone(channel.server_id)
        self.assertIsNone(channel.server_channel_id)
        self.assertIsNone(channel.last_bound_by_user_id)
        self.assertIsNone(channel.last_bound_at)
        self.db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
