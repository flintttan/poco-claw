"""Tests for the IM_MULTIUSER_ENABLED gray-scale feature flag.

The flag lets operators roll forward / roll back the multi-user
integration without a code change. When ``False``, every inbound
message is attributed to ``settings.backend_user_id`` and the
identity resolver is skipped — the legacy single-user behaviour.
When ``True`` (the default), the resolver runs and per-user ACLs
are enforced.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.im import InboundMessage
from app.services.identity_resolver import IdentityResolution
from app.services.im import InboundMessageService
from tests._im_test_utils import _InboundSenderContextResetMixin


def _msg(**overrides) -> InboundMessage:
    base = dict(
        provider="feishu",
        destination="oc-flag",
        message_id="m-flag",
        text="/help",
        sender_open_id="ou-flag",
        chat_type="p2p",
    )
    base.update(overrides)
    return InboundMessage(**base)


class FeatureFlagTests(
    _InboundSenderContextResetMixin, unittest.IsolatedAsyncioTestCase
):
    """Cover the gray-scale switch."""

    async def test_disabled_routes_to_legacy_user(self) -> None:
        """When the flag is False, every inbound message is attributed
        to ``backend_user_id`` and the resolver is never called."""
        msg = _msg()
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            side_effect=AssertionError("resolver should not run")
        )
        service = InboundMessageService(identity_resolver=resolver)

        db = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()
        db.close = MagicMock()
        db.begin_nested = MagicMock(
            return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
        )

        fake_settings = MagicMock()
        fake_settings.im_multiuser_enabled = False
        fake_settings.backend_user_id = "default"

        command_mock = MagicMock()
        command_mock.handle_text = AsyncMock(return_value=["ok"])

        with (
            patch("app.services.im.SessionLocal", return_value=db),
            patch("app.services.im.get_settings", return_value=fake_settings),
            patch("app.services.im.CommandService", return_value=command_mock),
            patch.object(
                InboundMessageService,
                "_get_or_create_channel",
                return_value=MagicMock(id=1, enabled=True, server_id=None),
            ),
            patch.object(InboundMessageService, "_ensure_channel_member"),
            patch.object(
                InboundMessageService,
                "_is_active_server_member",
                return_value=True,
            ),
            patch("app.services.im.BackendClient") as backend_cls,
            patch.object(
                InboundMessageService,
                "_resolve_send_address",
                return_value=None,
            ),
            patch.object(InboundMessageService, "_send_reply", new=AsyncMock()),
        ):
            backend_instance = MagicMock()
            backend_instance.user_id = "default"
            backend_cls.return_value = backend_instance

            await service.handle_message(message=msg)

        # The resolver was never called.
        resolver.resolve.assert_not_called()
        # The BackendClient was constructed with the legacy user id.
        backend_cls.assert_called_once()
        kwargs = backend_cls.call_args.kwargs
        self.assertEqual(kwargs["user_id"], "default")

    async def test_enabled_runs_resolver(self) -> None:
        """When the flag is True, the resolver runs and the resolved
        user id is what gets attributed to the message."""
        msg = _msg()
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            return_value=IdentityResolution(
                user_id="u-resolved", bound=True, reason="binding_open_id"
            )
        )
        service = InboundMessageService(identity_resolver=resolver)

        db = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()
        db.close = MagicMock()
        db.begin_nested = MagicMock(
            return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
        )

        fake_settings = MagicMock()
        fake_settings.im_multiuser_enabled = True
        fake_settings.backend_user_id = "default"

        command_mock = MagicMock()
        command_mock.handle_text = AsyncMock(return_value=["ok"])

        with (
            patch("app.services.im.SessionLocal", return_value=db),
            patch("app.services.im.get_settings", return_value=fake_settings),
            patch("app.services.im.CommandService", return_value=command_mock),
            patch.object(
                InboundMessageService,
                "_get_or_create_channel",
                return_value=MagicMock(id=2, enabled=True, server_id=None),
            ),
            patch.object(InboundMessageService, "_ensure_channel_member"),
            patch.object(
                InboundMessageService,
                "_is_active_server_member",
                return_value=True,
            ),
            patch("app.services.im.BackendClient") as backend_cls,
            patch.object(
                InboundMessageService,
                "_resolve_send_address",
                return_value=None,
            ),
            patch.object(InboundMessageService, "_send_reply", new=AsyncMock()),
        ):
            backend_instance = MagicMock()
            backend_instance.user_id = "u-resolved"
            backend_cls.return_value = backend_instance

            await service.handle_message(message=msg)

        resolver.resolve.assert_awaited_once()
        # The BackendClient was constructed with the resolved user.
        backend_cls.assert_called_once()
        kwargs = backend_cls.call_args.kwargs
        self.assertEqual(kwargs["user_id"], "u-resolved")


if __name__ == "__main__":
    unittest.main()
