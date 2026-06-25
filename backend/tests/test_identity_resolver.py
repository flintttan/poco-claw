"""Unit tests for the provider-agnostic IdentityResolver.

The resolver has three resolution paths:

1. ``im_bindings`` by ``(provider, sender_open_id)`` — the fast path
   for users who have already linked their IM identity via ``/bind``.
2. ``im_bindings`` by ``(provider, sender_union_id)`` — covers IM
   events that carry the union id but not the open id.
3. ``auth_identities`` auto-bind (Feishu only) — a logged-in Feishu
   user automatically binds their IM identity on the next message.

The resolver never creates new Poco users. Account creation is the
job of OAuth or admin invitation; IM is only a delivery channel.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.identity_resolver import IdentityResolver


def _db():
    db = MagicMock()
    db.begin_nested = MagicMock(
        return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    )
    db.flush = MagicMock()
    return db


def _binding(*, user_id: str = "u-bound", im_user_id: str = "ou-1"):
    b = MagicMock()
    b.user_id = user_id
    b.im_user_id = im_user_id
    return b


def _identity(*, user_id: str = "u-oauth", provider_user_id: str = "ou-1"):
    i = MagicMock()
    i.user_id = user_id
    i.provider_user_id = provider_user_id
    return i


class PrimaryOpenIdLookupTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_id_hit_returns_bound(self) -> None:
        with patch(
            "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
            return_value=_binding(),
        ):
            res = await IdentityResolver().resolve(
                _db(),
                provider="feishu",
                sender_open_id="ou-1",
                sender_union_id=None,
            )

        self.assertEqual(res.user_id, "u-bound")
        self.assertTrue(res.bound)
        self.assertFalse(res.auto_bound)
        self.assertEqual(res.reason, "binding_open_id")


class SecondaryUnionIdLookupTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_id_miss_union_id_hit(self) -> None:
        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=_binding(),
            ),
        ):
            res = await IdentityResolver().resolve(
                _db(),
                provider="feishu",
                sender_open_id="ou-1",
                sender_union_id="on-1",
            )

        self.assertEqual(res.user_id, "u-bound")
        self.assertTrue(res.bound)
        self.assertEqual(res.reason, "binding_union_id")


class OAuthAutoBindTests(unittest.IsolatedAsyncioTestCase):
    async def test_feishu_oauth_auto_binds(self) -> None:
        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.AuthIdentityRepository.get_by_provider_user_id",
                return_value=_identity(),
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.create"
            ) as create_mock,
        ):
            res = await IdentityResolver().resolve(
                _db(),
                provider="feishu",
                sender_open_id="ou-1",
                sender_union_id=None,
            )

        self.assertEqual(res.user_id, "u-oauth")
        self.assertTrue(res.bound)
        self.assertTrue(res.auto_bound)
        self.assertEqual(res.reason, "oauth_auto_bind")
        create_mock.assert_called_once()

    async def test_dingtalk_oauth_identity_does_not_auto_bind(self) -> None:
        """DingTalk is not in the OAuth↔IM auto-bind allowlist."""
        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.AuthIdentityRepository.get_by_provider_user_id"
            ) as lookup,
        ):
            res = await IdentityResolver().resolve(
                _db(),
                provider="dingtalk",
                sender_open_id="ou-1",
                sender_union_id=None,
            )

        self.assertFalse(res.bound)
        self.assertIsNone(res.user_id)
        self.assertEqual(res.reason, "needs_bind")
        lookup.assert_not_called()

    async def test_telegram_oauth_identity_does_not_auto_bind(self) -> None:
        """Telegram is not in the OAuth↔IM auto-bind allowlist."""
        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.AuthIdentityRepository.get_by_provider_user_id"
            ) as lookup,
        ):
            res = await IdentityResolver().resolve(
                _db(),
                provider="telegram",
                sender_open_id="ou-1",
                sender_union_id=None,
            )

        self.assertFalse(res.bound)
        self.assertEqual(res.reason, "needs_bind")
        lookup.assert_not_called()


class NeedsBindTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_provider(self) -> None:
        res = await IdentityResolver().resolve(
            _db(),
            provider="",
            sender_open_id="ou-1",
            sender_union_id=None,
        )
        self.assertFalse(res.bound)
        self.assertEqual(res.reason, "no_provider")

    async def test_no_sender_id(self) -> None:
        res = await IdentityResolver().resolve(
            _db(),
            provider="feishu",
            sender_open_id=None,
            sender_union_id=None,
        )
        self.assertFalse(res.bound)
        self.assertEqual(res.reason, "no_sender_id")

    async def test_no_binding_no_oauth(self) -> None:
        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.AuthIdentityRepository.get_by_provider_user_id",
                return_value=None,
            ),
        ):
            res = await IdentityResolver().resolve(
                _db(),
                provider="feishu",
                sender_open_id="ou-stranger",
                sender_union_id=None,
            )

        self.assertFalse(res.bound)
        self.assertIsNone(res.user_id)
        self.assertEqual(res.reason, "needs_bind")


class ResolveNormalizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_uppercase_provider_lowercased(self) -> None:
        with patch(
            "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
            return_value=_binding(),
        ) as get_mock:
            await IdentityResolver().resolve(
                _db(),
                provider="FEISHU",
                sender_open_id="ou-1",
                sender_union_id=None,
            )

        self.assertEqual(get_mock.call_args.kwargs["provider"], "feishu")

    async def test_whitespace_stripped_from_sender(self) -> None:
        with patch(
            "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
            return_value=_binding(),
        ) as get_mock:
            await IdentityResolver().resolve(
                _db(),
                provider="feishu",
                sender_open_id="  ou-1  ",
                sender_union_id=" on-1 ",
            )

        self.assertEqual(get_mock.call_args.kwargs["im_user_id"], "ou-1")


if __name__ == "__main__":
    unittest.main()
