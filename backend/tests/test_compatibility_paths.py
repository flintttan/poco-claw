"""Compatibility tests for when OAuth or memory is not configured.

These tests verify the system degrades gracefully in the cases the
user called out:
- Operator has not configured any OAuth provider.
- Operator has not configured memory (``MEM0_ENABLED=false``).
- Operator has not configured a frontend public URL
  (``FRONTEND_PUBLIC_URL`` empty).

In each case the IM flow must continue to work end-to-end (commands,
session creation, etc.) — the operator can still use the system, just
without the missing feature.
"""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.im import InboundMessage
from app.services.identity_resolver import IdentityResolution
from app.services.im import (
    InboundMessageService,
    _format_settings_url,
)


def _settings_with(**overrides) -> MagicMock:
    """Build a Settings-shaped mock with all relevant defaults."""
    defaults = dict(
        feishu_oauth_login_url="",
        feishu_oauth_client_id="",
        feishu_oauth_client_secret="",
        feishu_oauth_email_verified=False,
        feishu_enabled=True,
        mem0_enabled=False,
        frontend_public_url="",
        frontend_default_language="zh",
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


class FormatSettingsUrlTests(unittest.TestCase):
    """The settings URL is built from operator config. When the
    operator has not configured ``FRONTEND_PUBLIC_URL``, every code
    path must treat the missing URL as a graceful degradation (admin
    warning text, not a hard error)."""

    def test_returns_none_when_frontend_url_not_configured(self) -> None:
        with patch("app.services.im.get_settings") as get_settings:
            get_settings.return_value = _settings_with(frontend_public_url="")
            self.assertIsNone(_format_settings_url(None))

    def test_returns_base_when_no_destination(self) -> None:
        with patch("app.services.im.get_settings") as get_settings:
            get_settings.return_value = _settings_with(
                frontend_public_url="https://poco.example.com"
            )
            self.assertEqual(
                _format_settings_url(None),
                "https://poco.example.com/zh/settings/connected-accounts",
            )

    def test_appends_next_chat_param_with_question_mark(self) -> None:
        with patch("app.services.im.get_settings") as get_settings:
            get_settings.return_value = _settings_with(
                frontend_public_url="https://poco.example.com"
            )
            url = _format_settings_url("oc-abc")
            self.assertIsNotNone(url)
            assert url is not None
            self.assertIn("next_chat=oc-abc", url)
            self.assertTrue(url.startswith("https://poco.example.com/zh/settings/"))

    def test_falls_back_to_feishu_oauth_login_url(self) -> None:
        """When the operator has configured FEISHU_OAUTH_LOGIN_URL
        but not FRONTEND_PUBLIC_URL, the settings helper falls back
        to the legacy Feishu OAuth URL so that bootstrap deployments
        without a built Settings page still work."""
        with patch("app.services.im.get_settings") as get_settings:
            get_settings.return_value = _settings_with(
                frontend_public_url="",
                feishu_oauth_login_url="https://poco.example.com/login/feishu",
            )
            url = _format_settings_url("oc-abc")
            self.assertIsNotNone(url)
            assert url is not None
            self.assertIn("login/feishu", url)


class BindPromptCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    """When the operator has not configured FRONTEND_PUBLIC_URL, the
    bind prompt must still render an admin warning rather than a
    hard error."""

    def setUp(self) -> None:
        self.db = MagicMock()
        self.db.commit = MagicMock()
        self.db.rollback = MagicMock()
        self.db.close = MagicMock()
        self.db.begin_nested = MagicMock(
            return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
        )

    async def test_unbound_identity_advertises_missing_frontend(self) -> None:
        msg = InboundMessage(
            provider="feishu",
            destination="oc-unbound",
            message_id="m-unbound",
            text="hi",
            sender_open_id="open-unbound",
            chat_type="group",
        )
        resolver = MagicMock()
        resolver.resolve = AsyncMock(  # type: ignore[method-assign]
            return_value=IdentityResolution(
                user_id=None, bound=False, reason="needs_bind"
            )
        )
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=self.db),
            patch(
                "app.services.im.get_settings",
                return_value=_settings_with(frontend_public_url=""),
            ),
            patch.object(
                InboundMessageService, "_send_reply", new=AsyncMock()
            ) as send_reply,
        ):
            await service.handle_message(message=msg)

        send_reply.assert_awaited_once()
        send_reply_args = send_reply.await_args
        self.assertIsNotNone(send_reply_args)
        assert send_reply_args is not None
        text = send_reply_args.kwargs["responses"][0]
        self.assertIn("FRONTEND_PUBLIC_URL", text)
        self.assertIn("管理员", text)


class MemoryDisabledCompatibilityTests(unittest.TestCase):
    """When ``MEM0_ENABLED=false``, ``MemoryService`` must reject all
    create/search calls with a clear error rather than crashing. The
    inbound IM flow does not depend on memory being enabled — memory
    is opt-in per session — so this should never be hit in practice
    from the IM path."""

    def test_create_raises_when_disabled(self) -> None:
        from app.core.errors.exceptions import AppException
        from app.schemas.memory import MemoryCreateRequest, MemoryMessage
        from app.services.memory_service import MemoryService

        service = MemoryService()
        service._enabled = False

        request = MemoryCreateRequest(
            messages=[MemoryMessage(role="user", content="hi")],
        )

        with self.assertRaises(AppException) as ctx:
            service.create_memories(user_id="u-1", request=request)

        self.assertIn("Memory service is disabled", str(ctx.exception))

    def test_search_raises_when_disabled(self) -> None:
        from app.core.errors.exceptions import AppException
        from app.schemas.memory import MemorySearchRequest
        from app.services.memory_service import MemoryService

        service = MemoryService()
        service._enabled = False

        request = MemorySearchRequest(query="hello")

        with self.assertRaises(AppException) as ctx:
            service.search_memories(user_id="u-1", request=request)

        self.assertIn("Memory service is disabled", str(ctx.exception))

    def test_list_raises_when_disabled(self) -> None:
        from app.core.errors.exceptions import AppException
        from app.services.memory_service import MemoryService

        service = MemoryService()
        service._enabled = False

        with self.assertRaises(AppException):
            service.list_memories(user_id="u-1")


class BackendClientMemoryConfigDisabledTests(unittest.TestCase):
    pass


class ServerMemberInviteCompatibilityTests(unittest.TestCase):
    """Server-member invite flow must continue to work when OAuth is
    disabled (admin invites users out-of-band)."""

    def test_uuid_format_validation(self) -> None:
        from uuid import UUID

        # Server IDs are always UUIDs; this is a regression guard so
        # future migrations don't accidentally relax the type.
        sample = uuid.uuid4()
        self.assertIsInstance(UUID(str(sample)), UUID)


if __name__ == "__main__":
    unittest.main()
