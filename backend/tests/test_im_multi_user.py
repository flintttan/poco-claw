"""Unit tests for the multi-user IM message flow.

The flow tested here is the InboundMessageService path:
1. Identity resolution produces a Poco user_id (or refuses with
   "needs bind")
2. The channel is created/fetched with that user as the owner
3. Channel membership is auto-registered
4. Server ACL is enforced
5. CommandService is dispatched with a per-request BackendClient
"""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.im import Channel
from app.repositories.im import (
    ActiveSessionRepository,
    ChannelMemberRepository,
    ChannelRepository,
    WatchRepository,
)
from app.repositories.server_member_repository import ServerMemberRepository
from app.schemas.im import InboundMessage
from app.services.im import (
    BackendClient,
    BackendEventService,
    CommandService,
    InboundMessageService,
)
from app.services.identity_resolver import IdentityResolution


def _channel(channel_id: int = 1, **overrides) -> Channel:
    channel = MagicMock(spec=Channel)
    channel.id = channel_id
    channel.provider = overrides.get("provider", "feishu")
    channel.destination = overrides.get("destination", "chat-1")
    channel.enabled = True
    channel.subscribe_all = overrides.get("subscribe_all", False)
    channel.chat_type = overrides.get("chat_type", "group")
    channel.owner_user_id = overrides.get("owner_user_id", "u-sender")
    channel.server_id = overrides.get("server_id")
    return channel


def _resolution(
    user_id: str | None,
    *,
    bound: bool | None = None,
    auto_bound: bool = False,
    reason: str = "binding_open_id",
):
    """Build an IdentityResolution with the right ``bound`` flag."""
    return IdentityResolution(
        user_id=user_id,
        bound=bound if bound is not None else bool(user_id),
        auto_bound=auto_bound,
        reason=reason,
    )


def _db_session() -> MagicMock:
    db = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.close = MagicMock()
    db.begin_nested = MagicMock(
        return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    )
    return db


class InboundMessageServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_p2p_routes_to_resolved_user(self) -> None:
        msg = InboundMessage(
            provider="feishu",
            destination="oc-p2p",
            message_id="m-1",
            text="/help",
            sender_id="sender-1",
            sender_open_id="open-1",
            sender_union_id="union-1",
            chat_type="p2p",
        )
        channel = _channel(chat_type="p2p", owner_user_id="u-new")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            return_value=_resolution("u-new", auto_bound=True, reason="oauth_auto_bind")
        )
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=None
            ),
            patch.object(ChannelRepository, "create", return_value=channel),
            patch.object(
                ChannelMemberRepository, "get_by_channel_and_user", return_value=None
            ),
            patch.object(ChannelMemberRepository, "create", return_value=MagicMock()),
            patch.object(
                CommandService, "handle_text", new=AsyncMock(return_value=["ok"])
            ) as handle,
            patch.object(
                InboundMessageService, "_send_reply", new=AsyncMock()
            ) as send_reply,
        ):
            await service.handle_message(message=msg)

        resolver.resolve.assert_awaited_once()
        resolve_args = resolver.resolve.await_args
        self.assertIsNotNone(resolve_args)
        kwargs = resolve_args.kwargs
        self.assertEqual(kwargs["sender_open_id"], "open-1")
        self.assertEqual(kwargs["sender_union_id"], "union-1")
        self.assertEqual(kwargs["provider"], "feishu")
        handle.assert_awaited_once()
        handle_args = handle.await_args
        self.assertIsNotNone(handle_args)
        backend = handle_args.kwargs["backend"]
        self.assertIsInstance(backend, BackendClient)
        self.assertEqual(backend.user_id, "u-new")
        send_reply.assert_awaited_once()

    async def test_unbound_identity_prompts_bind(self) -> None:
        msg = InboundMessage(
            provider="feishu",
            destination="oc-group",
            message_id="m-2",
            text="hello",
            sender_id="sender-2",
            sender_open_id="open-2",
            chat_type="group",
        )
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            return_value=_resolution(None, bound=False, reason="needs_bind")
        )
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                InboundMessageService, "_send_reply", new=AsyncMock()
            ) as send_reply,
        ):
            await service.handle_message(message=msg)

        send_reply.assert_awaited_once()
        send_reply_args = send_reply.await_args
        self.assertIsNotNone(send_reply_args)
        self.assertIn("Poco", send_reply_args.kwargs["responses"][0])
        self.assertIn("绑定", send_reply_args.kwargs["responses"][0])

    async def test_server_acl_enforced_for_bound_channel(self) -> None:
        server_id = uuid.uuid4()
        msg = InboundMessage(
            provider="feishu",
            destination="oc-bound",
            message_id="m-3",
            text="/help",
            sender_open_id="open-3",
            sender_union_id="union-3",
            chat_type="group",
        )
        channel = _channel(server_id=server_id, owner_user_id="u-owner")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=_resolution("u-stranger"))
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=channel
            ),
            patch.object(
                ChannelMemberRepository,
                "get_by_channel_and_user",
                return_value=MagicMock(),
            ),
            patch.object(
                ServerMemberRepository, "get_by_server_and_user", return_value=None
            ),
            patch.object(
                InboundMessageService, "_send_reply", new=AsyncMock()
            ) as send_reply,
            patch.object(CommandService, "handle_text", new=AsyncMock()) as handle,
        ):
            await service.handle_message(message=msg)

        send_reply.assert_awaited_once()
        send_reply_args = send_reply.await_args
        self.assertIsNotNone(send_reply_args)
        self.assertIn("Server", send_reply_args.kwargs["responses"][0])
        handle.assert_not_awaited()

    async def test_server_member_passes_acl(self) -> None:
        server_id = uuid.uuid4()
        msg = InboundMessage(
            provider="feishu",
            destination="oc-bound2",
            message_id="m-4",
            text="/help",
            sender_open_id="open-4",
            sender_union_id="union-4",
            chat_type="group",
        )
        channel = _channel(server_id=server_id, owner_user_id="u-owner")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=_resolution("u-member"))
        service = InboundMessageService(identity_resolver=resolver)
        membership = MagicMock()
        membership.status = "active"

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=channel
            ),
            patch.object(
                ChannelMemberRepository,
                "get_by_channel_and_user",
                return_value=MagicMock(),
            ),
            patch.object(
                ServerMemberRepository,
                "get_by_server_and_user",
                return_value=membership,
            ),
            patch.object(
                CommandService, "handle_text", new=AsyncMock(return_value=["ok"])
            ) as handle,
            patch.object(InboundMessageService, "_send_reply", new=AsyncMock()),
        ):
            await service.handle_message(message=msg)

        handle.assert_awaited_once()

    async def test_existing_channel_disabled_skips_command(self) -> None:
        msg = InboundMessage(
            provider="feishu",
            destination="oc-disabled",
            message_id="m-5",
            text="hello",
            sender_open_id="open-5",
            chat_type="p2p",
        )
        channel = _channel(chat_type="p2p", owner_user_id="u-a")
        channel.enabled = False
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=_resolution("u-a"))
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=channel
            ),
            patch.object(CommandService, "handle_text", new=AsyncMock()) as handle,
        ):
            await service.handle_message(message=msg)

        handle.assert_not_awaited()

    async def test_server_acl_blocks_channel_member_write(self) -> None:
        """B2 fix: when an inbound sender fails the server ACL, they
        must NOT be recorded in ``channel_members`` (otherwise the
        membership row could be used to bypass future ACL checks that
        consult channel_members)."""
        server_id = uuid.uuid4()
        msg = InboundMessage(
            provider="feishu",
            destination="oc-bound-blocked",
            message_id="m-b2",
            text="/help",
            sender_open_id="open-blocked",
            sender_union_id="union-blocked",
            chat_type="group",
        )
        channel = _channel(server_id=server_id, owner_user_id="u-owner")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=_resolution("u-stranger"))
        service = InboundMessageService(identity_resolver=resolver)

        create_member = MagicMock()
        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=channel
            ),
            patch.object(
                ServerMemberRepository, "get_by_server_and_user", return_value=None
            ),
            patch.object(
                ChannelMemberRepository,
                "get_by_channel_and_user",
                return_value=None,
            ),
            patch.object(ChannelMemberRepository, "create", create_member),
            patch.object(
                InboundMessageService, "_send_reply", new=AsyncMock()
            ) as send_reply,
            patch.object(CommandService, "handle_text", new=AsyncMock()) as handle,
        ):
            await service.handle_message(message=msg)

        send_reply.assert_awaited_once()
        handle.assert_not_awaited()
        # Critical: ACL rejection must not write a member row.
        create_member.assert_not_called()

    async def test_server_acl_runs_before_channel_member(self) -> None:
        """B2 fix: ordering assertion. ACL is checked first, so we
        should never get to create_member when ACL denies."""
        server_id = uuid.uuid4()
        msg = InboundMessage(
            provider="feishu",
            destination="oc-order",
            message_id="m-b2-order",
            text="/help",
            sender_open_id="open-order",
            sender_union_id="union-order",
            chat_type="group",
        )
        channel = _channel(server_id=server_id, owner_user_id="u-owner")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=_resolution("u-stranger"))
        service = InboundMessageService(identity_resolver=resolver)

        membership_calls: list[str] = []
        member_calls: list[str] = []

        def get_by_server_and_user(_db, sid, uid):
            membership_calls.append(uid)
            return None  # deny

        def create_member(*args, **kwargs):
            member_calls.append("called")
            return MagicMock()

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=channel
            ),
            patch.object(
                ServerMemberRepository,
                "get_by_server_and_user",
                side_effect=get_by_server_and_user,
            ),
            patch.object(
                ChannelMemberRepository,
                "get_by_channel_and_user",
                return_value=None,
            ),
            patch.object(ChannelMemberRepository, "create", side_effect=create_member),
            patch.object(InboundMessageService, "_send_reply", new=AsyncMock()),
            patch.object(CommandService, "handle_text", new=AsyncMock()) as handle,
        ):
            await service.handle_message(message=msg)

        self.assertEqual(membership_calls, ["u-stranger"])
        self.assertEqual(member_calls, [])
        handle.assert_not_awaited()

    async def test_auto_bound_notice_prepended_once(self) -> None:
        """When the resolver auto-binds an OAuth identity, the user
        gets a one-time FYI notice in addition to the command reply."""
        msg = InboundMessage(
            provider="feishu",
            destination="oc-prepend",
            message_id="m-prepend",
            text="/help",
            sender_open_id="open-prepend",
            chat_type="p2p",
        )
        channel = _channel(chat_type="p2p", owner_user_id="u-prepend")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            return_value=_resolution(
                "u-prepend", auto_bound=True, reason="oauth_auto_bind"
            )
        )
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=None
            ),
            patch.object(ChannelRepository, "create", return_value=channel),
            patch.object(
                ChannelMemberRepository,
                "get_by_channel_and_user",
                return_value=None,
            ),
            patch.object(ChannelMemberRepository, "create", return_value=MagicMock()),
            patch.object(
                CommandService,
                "handle_text",
                new=AsyncMock(return_value=["command reply"]),
            ),
            patch.object(
                InboundMessageService, "_send_reply", new=AsyncMock()
            ) as send_reply,
        ):
            await service.handle_message(message=msg)

        send_reply.assert_awaited_once()
        send_reply_args = send_reply.await_args
        assert send_reply_args is not None
        responses = send_reply_args.kwargs["responses"]
        self.assertEqual(len(responses), 2)
        self.assertIn("自动绑定", responses[0])
        self.assertEqual(responses[1], "command reply")

    async def test_no_notice_when_not_auto_bound(self) -> None:
        msg = InboundMessage(
            provider="feishu",
            destination="oc-existing",
            message_id="m-existing",
            text="/help",
            sender_open_id="open-existing",
            chat_type="p2p",
        )
        channel = _channel(chat_type="p2p", owner_user_id="u-existing")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(return_value=_resolution("u-existing"))
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository, "get_by_provider_destination", return_value=None
            ),
            patch.object(ChannelRepository, "create", return_value=channel),
            patch.object(
                ChannelMemberRepository,
                "get_by_channel_and_user",
                return_value=None,
            ),
            patch.object(ChannelMemberRepository, "create", return_value=MagicMock()),
            patch.object(
                CommandService,
                "handle_text",
                new=AsyncMock(return_value=["command reply"]),
            ),
            patch.object(
                InboundMessageService, "_send_reply", new=AsyncMock()
            ) as send_reply,
        ):
            await service.handle_message(message=msg)

        send_reply.assert_awaited_once()
        send_reply_args = send_reply.await_args
        assert send_reply_args is not None
        responses = send_reply_args.kwargs["responses"]
        self.assertEqual(responses, ["command reply"])


class BindPromptTests(unittest.IsolatedAsyncioTestCase):
    async def test_bind_prompt_includes_settings_url_when_configured(self) -> None:
        with patch(
            "app.services.im._format_settings_url",
            return_value="https://poco.example.com/zh/settings/connected-accounts",
        ):
            text = InboundMessageService()._bind_prompt_text(provider="feishu")

        self.assertIn("Poco", text)
        self.assertIn("settings/connected-accounts", text)
        self.assertIn("feishu", text)

    async def test_bind_prompt_falls_back_to_admin_warning(self) -> None:
        with patch("app.services.im._format_settings_url", return_value=None):
            text = InboundMessageService()._bind_prompt_text(provider="feishu")

        self.assertIn("FRONTEND_PUBLIC_URL", text)
        self.assertIn("管理员", text)


class MemoryScopeConfigTests(unittest.TestCase):
    def test_unbound_channel_uses_user_scope(self) -> None:
        from app.services.im import _build_memory_config

        channel = _channel(server_id=None)
        self.assertEqual(_build_memory_config(channel), {})

    def test_bound_channel_uses_both_scope(self) -> None:
        from app.services.im import _build_memory_config

        server_id = uuid.uuid4()
        channel = _channel(server_id=server_id)
        config = _build_memory_config(channel)
        self.assertEqual(config["memory_scope"], "both")
        self.assertEqual(config["memory_server_id"], str(server_id))


class BackendEventServiceACLTests(unittest.TestCase):
    def _service(self) -> BackendEventService:
        return BackendEventService()

    def test_subscribe_all_routes_only_to_owning_user(self) -> None:
        channel_a = _channel(channel_id=10, owner_user_id="u-a", subscribe_all=True)
        channel_b = _channel(channel_id=11, owner_user_id="u-b", subscribe_all=True)

        with (
            patch.object(
                ChannelRepository,
                "list_enabled",
                return_value=[channel_a, channel_b],
            ),
            patch.object(WatchRepository, "list_by_session", return_value=[]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
        ):
            service = self._service()
            target_a = service._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-a"
            )
            target_b = service._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-b"
            )

        self.assertEqual(target_a, {10})
        self.assertEqual(target_b, {11})

    def test_watch_routes_to_event_user_owner(self) -> None:
        watch_channel = _channel(channel_id=20, owner_user_id="u-owner")
        watch = MagicMock()
        watch.channel_id = 20

        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[watch]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(ChannelRepository, "get_by_id", return_value=watch_channel),
            patch.object(
                ServerMemberRepository, "get_by_server_and_user", return_value=None
            ),
        ):
            service = self._service()
            target = service._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-owner"
            )

        self.assertIn(20, target)

    def test_watch_does_not_route_to_other_user(self) -> None:
        watch_channel = _channel(channel_id=30, owner_user_id="u-owner")
        watch = MagicMock()
        watch.channel_id = 30

        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[watch]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(ChannelRepository, "get_by_id", return_value=watch_channel),
            patch.object(
                ServerMemberRepository, "get_by_server_and_user", return_value=None
            ),
        ):
            service = self._service()
            target = service._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-stranger"
            )

        self.assertNotIn(30, target)

    def test_server_member_routes_to_bound_channel(self) -> None:
        server_id = uuid.uuid4()
        bound_channel = _channel(channel_id=40, owner_user_id="u-owner")
        bound_channel.server_id = server_id
        watch = MagicMock()
        watch.channel_id = 40
        membership = MagicMock()
        membership.status = "active"

        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[watch]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(ChannelRepository, "get_by_id", return_value=bound_channel),
            patch.object(
                ServerMemberRepository,
                "get_by_server_and_user",
                return_value=membership,
            ),
        ):
            service = self._service()
            target = service._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-member"
            )

        self.assertIn(40, target)


if __name__ == "__main__":
    unittest.main()
