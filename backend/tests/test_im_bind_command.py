"""Unit tests for the IM binding commands.

Two separate flows coexist:

- ``/bind <code>`` and ``/unbind`` — link an IM identity to a Poco
  user via a web-generated binding code, or remove that link.
- ``/server <server_id>`` and ``/server-off`` — bind a channel to a
  Poco server (enables shared sessions within the chat), or remove
  the binding. Requires server admin/owner.

These exercise the CommandService surface and the thread-local
sender context (set by InboundMessageService) that supplies the
IM-side identifiers.
"""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.models.im import Channel
from app.repositories.im import (
    ImBindingCodeRepository,
    ImBindingRepository,
)
from app.repositories.server_member_repository import ServerMemberRepository
from app.services.im import (
    BackendClient,
    CommandService,
    _set_inbound_sender_context,
)


def _channel(**overrides) -> Channel:
    channel = MagicMock(spec=Channel)
    channel.id = 1
    channel.provider = "feishu"
    channel.destination = "oc-test"
    channel.enabled = True
    channel.subscribe_all = False
    channel.chat_type = overrides.get("chat_type", "group")
    channel.owner_user_id = overrides.get("owner_user_id", "u-anchor")
    channel.server_id = overrides.get("server_id")
    channel.last_bound_by_user_id = overrides.get("last_bound_by_user_id")
    channel.last_bound_at = overrides.get("last_bound_at")
    return channel


def _backend(user_id: str = "u-sender") -> BackendClient:
    return BackendClient(user_id=user_id, channel=None)


def _membership(role: str = "owner", status: str = "active") -> MagicMock:
    m = MagicMock()
    m.role = role
    m.status = status
    return m


def _binding(*, user_id: str = "u-sender") -> MagicMock:
    b = MagicMock()
    b.id = 11
    b.user_id = user_id
    b.provider = "feishu"
    b.im_user_id = "ou-sender"
    b.im_union_id = "on-sender"
    return b


class ServerBindCommandTests(unittest.IsolatedAsyncioTestCase):
    """``/server`` and ``/server-off`` bind a channel to a Poco server."""

    async def test_server_requires_uuid(self) -> None:
        service = CommandService()
        responses = await service.handle_text(
            db=MagicMock(),
            channel=_channel(),
            text="/server not-a-uuid",
            backend=_backend(),
        )
        self.assertIn("UUID", responses[0])

    async def test_server_rejects_non_member(self) -> None:
        service = CommandService()
        with patch.object(
            ServerMemberRepository, "get_by_server_and_user", return_value=None
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text=f"/server {uuid.uuid4()}",
                backend=_backend(),
            )
        self.assertIn("成员", responses[0])

    async def test_server_rejects_non_admin_member(self) -> None:
        service = CommandService()
        with patch.object(
            ServerMemberRepository,
            "get_by_server_and_user",
            return_value=_membership(role="member"),
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text=f"/server {uuid.uuid4()}",
                backend=_backend(),
            )
        self.assertIn("owner/admin", responses[0])

    async def test_server_admin_sets_server_id(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel()
        service = CommandService()

        with patch.object(
            ServerMemberRepository,
            "get_by_server_and_user",
            return_value=_membership(role="admin"),
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=channel,
                text=f"/server {server_id}",
                backend=_backend(user_id="u-admin"),
            )

        self.assertEqual(channel.server_id, server_id)
        self.assertEqual(channel.last_bound_by_user_id, "u-admin")
        self.assertIsInstance(channel.last_bound_at, datetime)
        self.assertIn(str(server_id), responses[0])

    async def test_server_off_requires_existing_binding(self) -> None:
        service = CommandService()
        responses = await service.handle_text(
            db=MagicMock(),
            channel=_channel(server_id=None),
            text="/server-off",
            backend=_backend(),
        )
        self.assertIn("未绑定", responses[0])

    async def test_server_off_owner_allowed(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(server_id=server_id, owner_user_id="u-anchor")
        service = CommandService()

        responses = await service.handle_text(
            db=MagicMock(),
            channel=channel,
            text="/server-off",
            backend=_backend(user_id="u-anchor"),
        )

        self.assertIsNone(channel.server_id)
        self.assertIsNone(channel.last_bound_by_user_id)
        self.assertIsNone(channel.last_bound_at)
        self.assertIn("解绑", responses[0])

    async def test_server_off_admin_allowed(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(server_id=server_id, owner_user_id="u-anchor")
        service = CommandService()

        with patch.object(
            ServerMemberRepository,
            "get_by_server_and_user",
            return_value=_membership(role="owner"),
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=channel,
                text="/server-off",
                backend=_backend(user_id="u-admin"),
            )

        self.assertIsNone(channel.server_id)
        self.assertIn("解绑", responses[0])

    async def test_server_off_random_member_rejected(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(server_id=server_id, owner_user_id="u-anchor")
        service = CommandService()

        with patch.object(
            ServerMemberRepository,
            "get_by_server_and_user",
            return_value=_membership(role="member"),
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=channel,
                text="/server-off",
                backend=_backend(user_id="u-random"),
            )

        self.assertEqual(channel.server_id, server_id)
        self.assertIn("channel owner", responses[0])


class IdentityBindCommandTests(unittest.IsolatedAsyncioTestCase):
    """``/bind <code>`` and ``/unbind`` link an IM identity to a Poco user."""

    def setUp(self) -> None:
        _set_inbound_sender_context(
            sender_open_id="ou-sender", sender_union_id="on-sender"
        )

    def tearDown(self) -> None:
        _set_inbound_sender_context(sender_open_id=None, sender_union_id=None)

    async def test_bind_code_requires_arg(self) -> None:
        service = CommandService()
        responses = await service.handle_text(
            db=MagicMock(),
            channel=_channel(),
            text="/bind",
            backend=_backend(),
        )
        self.assertIn("绑定码", responses[0])

    async def test_bind_code_rejects_missing_code(self) -> None:
        service = CommandService()
        with patch.object(ImBindingCodeRepository, "get_active", return_value=None):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text="/bind BADC0DE",
                backend=_backend(),
            )
        self.assertIn("无效", responses[0])

    async def test_bind_code_rejects_provider_mismatch(self) -> None:
        service = CommandService()
        row = MagicMock()
        row.user_id = "u-target"
        row.provider = "feishu"
        with (
            patch.object(ImBindingCodeRepository, "get_active", return_value=row),
            patch.object(ImBindingCodeRepository, "consume", return_value=True),
            patch.object(
                ImBindingRepository,
                "get_by_provider_im_user_id",
                return_value=None,
            ),
        ):
            channel = _channel(provider="dingtalk")
            responses = await service.handle_text(
                db=MagicMock(),
                channel=channel,
                text="/bind BADC0DE",
                backend=_backend(),
            )
        self.assertIn("feishu", responses[0])

    async def test_bind_code_creates_binding_for_unbound_identity(self) -> None:
        service = CommandService()
        row = MagicMock()
        row.user_id = "u-target"
        row.provider = None
        with (
            patch.object(ImBindingCodeRepository, "get_active", return_value=row),
            patch.object(ImBindingCodeRepository, "consume", return_value=True),
            patch.object(
                ImBindingRepository,
                "get_by_provider_im_user_id",
                return_value=None,
            ),
            patch.object(
                ImBindingRepository, "create", return_value=MagicMock()
            ) as create_mock,
        ):
            db = MagicMock()
            responses = await service.handle_text(
                db=db,
                channel=_channel(),
                text="/bind BADC0DE",
                backend=_backend(),
            )
        self.assertIn("绑定成功", responses[0])
        create_mock.assert_called_once()

    async def test_bind_code_idempotent_when_already_bound_to_same_user(self) -> None:
        service = CommandService()
        row = MagicMock()
        row.user_id = "u-sender"
        row.provider = None
        with (
            patch.object(ImBindingCodeRepository, "get_active", return_value=row),
            patch.object(ImBindingCodeRepository, "consume", return_value=True),
            patch.object(
                ImBindingRepository,
                "get_by_provider_im_user_id",
                return_value=_binding(user_id="u-sender"),
            ),
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text="/bind BADC0DE",
                backend=_backend(),
            )
        self.assertIn("已绑定", responses[0])

    async def test_bind_code_refuses_to_silently_rebind(self) -> None:
        service = CommandService()
        row = MagicMock()
        row.user_id = "u-target"
        row.provider = None
        with (
            patch.object(ImBindingCodeRepository, "get_active", return_value=row),
            patch.object(ImBindingCodeRepository, "consume", return_value=True),
            patch.object(
                ImBindingRepository,
                "get_by_provider_im_user_id",
                return_value=_binding(user_id="u-other"),
            ),
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text="/bind BADC0DE",
                backend=_backend(),
            )
        self.assertIn("其他 Poco 账号", responses[0])

    async def test_unbind_removes_only_own_binding(self) -> None:
        service = CommandService()
        with (
            patch.object(
                ImBindingRepository,
                "get_by_provider_im_user_id",
                return_value=_binding(user_id="u-sender"),
            ) as get_mock,
            patch.object(ImBindingRepository, "delete") as delete_mock,
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text="/unbind",
                backend=_backend(),
            )
        self.assertIn("已解除", responses[0])
        get_mock.assert_called_once()
        delete_mock.assert_called_once()

    async def test_unbind_refuses_for_other_users_binding(self) -> None:
        service = CommandService()
        with patch.object(
            ImBindingRepository,
            "get_by_provider_im_user_id",
            return_value=_binding(user_id="u-other"),
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text="/unbind",
                backend=_backend(),
            )
        self.assertIn("另一个 Poco 账号", responses[0])

    async def test_unbind_when_no_binding(self) -> None:
        service = CommandService()
        with patch.object(
            ImBindingRepository,
            "get_by_provider_im_user_id",
            return_value=None,
        ):
            responses = await service.handle_text(
                db=MagicMock(),
                channel=_channel(),
                text="/unbind",
                backend=_backend(),
            )
        self.assertIn("未绑定", responses[0])


class WhoAmICommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_whoami_reports_state(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(server_id=server_id, chat_type="group")
        service = CommandService()

        responses = await service.handle_text(
            db=MagicMock(),
            channel=channel,
            text="/whoami",
            backend=_backend(user_id="u-mine"),
        )

        text = responses[0]
        self.assertIn("u-mine", text)
        self.assertIn("group", text)
        self.assertIn(str(server_id), text)


class StartCommandTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_in_p2p_uses_backend_user(self) -> None:
        channel = _channel(chat_type="p2p", owner_user_id="u-p2p")
        service = CommandService()

        responses = await service.handle_text(
            db=MagicMock(),
            channel=channel,
            text="/start",
            backend=_backend(user_id="u-p2p"),
        )

        self.assertIn("u-p2p", responses[0])

    async def test_start_in_group_renders(self) -> None:
        channel = _channel(chat_type="group", owner_user_id="u-anchor")
        service = CommandService()

        responses = await service.handle_text(
            db=MagicMock(),
            channel=channel,
            text="/start",
            backend=_backend(user_id="u-sender"),
        )

        self.assertIn("Poco", responses[0])


if __name__ == "__main__":
    unittest.main()
