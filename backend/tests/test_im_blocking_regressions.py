"""Regression tests for the three BLOCKING issues identified during
the multi-user IM review.

B1 — ``ImBindingCodeRepository.consume`` must be race-safe. The old
     implementation read ``row.consumed_at is not None`` in Python,
     which lets two concurrent ``/bind`` requests both succeed. The
     new implementation uses a conditional UPDATE with a rowcount
     check so only one writer can win.

B2 — ``IdentityResolver._auto_bind_from_oauth`` must consult both
     ``(provider, im_user_id)`` AND ``(provider, im_union_id)`` when
     looking for an existing binding. Missing the im_union_id branch
     allows duplicate inserts that the UNIQUE constraint then drops
     silently — so a user who OAuth-logged in via union_id never gets
     auto-bound when the IM event carries a different open_id that
     happens to share the union_id.

B3 — ``InboundMessageService.handle_message`` must commit the
     auto-bind insert immediately. A later step (channel ACL, command
     dispatch, IM gateway send) raising would otherwise roll the
     binding back, forcing the next inbound message to re-resolve.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.exc import IntegrityError

from app.models.im import Channel, ImBinding, ImBindingCode
from app.repositories.im import (
    ChannelMemberRepository,
    ChannelRepository,
    ImBindingCodeRepository,
)
from app.schemas.im import InboundMessage
from app.services.im import CommandService, InboundMessageService
from app.services.identity_resolver import IdentityResolution, IdentityResolver


def _channel(**overrides) -> Channel:
    channel = MagicMock(spec=Channel)
    channel.id = 1
    channel.provider = "feishu"
    channel.destination = "oc-test"
    channel.enabled = True
    channel.subscribe_all = False
    channel.chat_type = overrides.get("chat_type", "group")
    channel.owner_user_id = overrides.get("owner_user_id", "u-sender")
    channel.server_id = overrides.get("server_id")
    return channel


def _db_session() -> MagicMock:
    db = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.close = MagicMock()
    db.begin_nested = MagicMock(
        return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
    )
    return db


def _binding_row(
    *, code: str = "BADC0DE", consumed_at: datetime | None = None
) -> ImBindingCode:
    row = MagicMock(spec=ImBindingCode)
    row.id = 1
    row.code = code
    row.user_id = "u-mine"
    row.provider = "feishu"
    row.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    row.consumed_at = consumed_at
    row.consumed_by = None
    return row


# ---------------------------------------------------------------------------
# B1 — consume is race-safe via conditional UPDATE
# ---------------------------------------------------------------------------


class ConsumeRaceSafetyTests(unittest.TestCase):
    """``consume`` must not rely on a Python-side ``is None`` check.

    The fix is a single ``UPDATE ... WHERE consumed_at IS NULL AND
    expires_at > now``; only the caller whose UPDATE affected 1 row
    wins. Any other rowcount means the code was already consumed or
    expired.
    """

    def test_consume_calls_conditional_update(self) -> None:
        row = _binding_row()
        db = MagicMock()
        result = MagicMock()
        result.rowcount = 1
        # ``consume`` goes through ``db.connection().execute`` so the
        # ORM-level Session.execute wrapper (which would try to
        # synchronize the session) does not interfere.
        db.connection.return_value.execute = MagicMock(return_value=result)
        db.flush = MagicMock()
        db.refresh = MagicMock()

        with patch("app.repositories.im.update") as update_mock:
            ok = ImBindingCodeRepository.consume(db, row=row, consumed_by="ou-winner")

        self.assertTrue(ok)
        # A single execute was issued — the conditional UPDATE.
        db.connection.return_value.execute.assert_called_once()
        update_mock.assert_called_once()
        # The in-memory row is updated so the caller can re-read it
        # without another round trip.
        self.assertIsNotNone(row.consumed_at)
        self.assertEqual(row.consumed_by, "ou-winner")

    def test_consume_returns_false_when_rowcount_is_zero(self) -> None:
        """Two concurrent ``consume`` calls: first wins, second sees
        rowcount=0 and returns False. This is the regression."""
        row = _binding_row()
        db = MagicMock()
        result = MagicMock()
        result.rowcount = 0  # Lost the race.
        db.connection.return_value.execute = MagicMock(return_value=result)
        db.flush = MagicMock()
        db.refresh = MagicMock()

        with patch("app.repositories.im.update"):
            ok = ImBindingCodeRepository.consume(db, row=row, consumed_by="ou-loser")

        self.assertFalse(ok)
        # ``refresh`` is called so the caller sees the row that
        # another transaction already marked consumed.
        db.refresh.assert_called_once_with(row)

    def test_consume_truncates_oversized_consumed_by(self) -> None:
        """``consumed_by`` is bounded by column length (255)."""
        row = _binding_row()
        db = MagicMock()
        result = MagicMock()
        result.rowcount = 1
        db.connection.return_value.execute = MagicMock(return_value=result)
        db.flush = MagicMock()
        db.refresh = MagicMock()

        long_id = "x" * 500
        with patch("app.repositories.im.update"):
            ok = ImBindingCodeRepository.consume(db, row=row, consumed_by=long_id)

        self.assertTrue(ok)
        # Stored value is truncated to 255 characters.
        self.assertEqual(row.consumed_by, "x" * 255)


# ---------------------------------------------------------------------------
# B2 — _auto_bind_from_oauth also looks up by im_union_id
# ---------------------------------------------------------------------------


class AutoBindUnionIdLookupTests(unittest.IsolatedAsyncioTestCase):
    """When a previous binding was created from a Feishu event that
    only had the union_id, the OAuth auto-bind path must recognize
    it instead of inserting a duplicate that the unique constraint
    would discard.
    """

    async def test_existing_binding_via_union_id_returns_owner(self) -> None:
        """If an existing im_bindings row uses the union_id as
        im_user_id (a common shape: Feishu OAuth saves the union
        id into both fields), the resolver must not insert a new
        row when a different open_id arrives."""
        existing = MagicMock(spec=ImBinding)
        existing.user_id = "u-mine"
        existing.im_user_id = "on-existing"
        existing.im_union_id = "on-existing"

        db = _db_session()

        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                side_effect=lambda db, **kw: (
                    existing if kw.get("im_user_id") == "on-existing" else None
                ),
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.create"
            ) as create_mock,
        ):
            user_id = IdentityResolver._auto_bind_from_oauth(
                db,
                identity=MagicMock(user_id="u-mine"),
                provider="feishu",
                im_user_id="ou-new",
                im_union_id="on-existing",
            )

        self.assertEqual(user_id, "u-mine")
        create_mock.assert_not_called()

    async def test_existing_binding_via_union_id_for_different_user_blocks(
        self,
    ) -> None:
        """If a different user already owns the im_union_id binding,
        auto-bind must refuse (return None) — never silently steal
        ownership."""
        existing = MagicMock(spec=ImBinding)
        existing.user_id = "u-other"
        existing.im_user_id = "on-existing"
        existing.im_union_id = "on-existing"

        db = _db_session()

        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=existing,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.create"
            ) as create_mock,
        ):
            user_id = IdentityResolver._auto_bind_from_oauth(
                db,
                identity=MagicMock(user_id="u-mine"),
                provider="feishu",
                im_user_id="ou-new",
                im_union_id="on-existing",
            )

        self.assertIsNone(user_id)
        create_mock.assert_not_called()

    async def test_integrity_error_re_reads_by_both_keys(self) -> None:
        """When the unique constraint catches a race, the resolver
        re-reads by im_user_id AND im_union_id. The old code only
        re-read by im_user_id, missing the case where the winning
        row used the union id."""
        existing = MagicMock(spec=ImBinding)
        existing.user_id = "u-mine"
        existing.im_user_id = "on-existing"
        existing.im_union_id = "on-existing"

        db = _db_session()
        db.flush = MagicMock(
            side_effect=[IntegrityError("INSERT", {}, Exception()), None]
        )

        # First call: im_user_id="ou-new" → None. Second call:
        # im_user_id="on-existing" → existing. (The order depends on
        # the resolver's iteration; we just need it to find the row
        # via at least one of the two lookups.)
        side_effects = [None, existing]
        with (
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_user_id",
                side_effect=side_effects,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.get_by_provider_im_union_id",
                return_value=None,
            ),
            patch(
                "app.services.identity_resolver.ImBindingRepository.create",
                return_value=MagicMock(),
            ),
        ):
            user_id = IdentityResolver._auto_bind_from_oauth(
                db,
                identity=MagicMock(user_id="u-mine"),
                provider="feishu",
                im_user_id="ou-new",
                im_union_id="on-existing",
            )

        self.assertEqual(user_id, "u-mine")


# ---------------------------------------------------------------------------
# B3 — handle_message commits the auto-bind before continuing
# ---------------------------------------------------------------------------


class AutoBindEarlyCommitTests(unittest.IsolatedAsyncioTestCase):
    """After the resolver auto-binds, the binding must be committed
    before subsequent steps run. Otherwise an exception during
    channel ACL / command dispatch would roll the binding back.
    """

    async def test_auto_bound_commits_before_command_dispatch(self) -> None:
        msg = InboundMessage(
            provider="feishu",
            destination="oc-bind",
            message_id="m-bind",
            text="/help",
            sender_open_id="open-bind",
            chat_type="p2p",
        )
        channel = _channel(chat_type="p2p", owner_user_id="u-bind")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            return_value=IdentityResolution(
                user_id="u-bind",
                bound=True,
                auto_bound=True,
                reason="oauth_auto_bind",
            )
        )
        service = InboundMessageService(identity_resolver=resolver)

        db = _db_session()
        # Track call order so we can assert commit happens before
        # the command dispatcher runs.
        call_log: list[str] = []

        def fake_commit() -> None:
            call_log.append("commit")

        db.commit = MagicMock(side_effect=fake_commit)

        async def fake_handle_text(**kwargs):
            call_log.append("command")
            return ["ok"]

        with (
            patch("app.services.im.SessionLocal", return_value=db),
            patch.object(
                ChannelRepository,
                "get_by_provider_destination",
                return_value=None,
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
                new=AsyncMock(side_effect=fake_handle_text),
            ),
            patch.object(InboundMessageService, "_send_reply", new=AsyncMock()),
        ):
            await service.handle_message(message=msg)

        # At least one commit happens (early commit) before the
        # command runs. There may be a second commit at the end of
        # the happy path; what matters is that ``commit`` precedes
        # ``command`` in the log.
        self.assertIn("commit", call_log)
        self.assertIn("command", call_log)
        self.assertLess(call_log.index("commit"), call_log.index("command"))

    async def test_auto_bound_command_failure_preserves_binding(self) -> None:
        """If a later step (here: command dispatch) raises, the
        early commit means the im_bindings row is already on disk.
        A rollback of the outer transaction only undoes the
        channel/member writes."""
        msg = InboundMessage(
            provider="feishu",
            destination="oc-fail",
            message_id="m-fail",
            text="/help",
            sender_open_id="open-fail",
            chat_type="p2p",
        )
        channel = _channel(chat_type="p2p", owner_user_id="u-fail")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            return_value=IdentityResolution(
                user_id="u-fail",
                bound=True,
                auto_bound=True,
                reason="oauth_auto_bind",
            )
        )
        service = InboundMessageService(identity_resolver=resolver)

        db = _db_session()
        commit_called = {"count": 0}

        def fake_commit() -> None:
            commit_called["count"] += 1

        db.commit = MagicMock(side_effect=fake_commit)

        with (
            patch("app.services.im.SessionLocal", return_value=db),
            patch.object(
                ChannelRepository,
                "get_by_provider_destination",
                return_value=None,
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
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(InboundMessageService, "_send_reply", new=AsyncMock()),
        ):
            with self.assertRaises(RuntimeError):
                await service.handle_message(message=msg)

        # The early commit ran before the failure. The trailing
        # rollback in the except block does not undo it.
        self.assertGreaterEqual(commit_called["count"], 1)
        db.rollback.assert_called()

    async def test_sender_context_cleared_after_handle(self) -> None:
        """The ContextVar holding the inbound sender ids is reset
        on every handle_message, even if a step raises."""
        from app.services.im import _current_inbound_sender_open_id

        msg = InboundMessage(
            provider="feishu",
            destination="oc-ctx",
            message_id="m-ctx",
            text="/help",
            sender_open_id="open-ctx",
            sender_union_id="union-ctx",
            chat_type="p2p",
        )
        channel = _channel(chat_type="p2p", owner_user_id="u-ctx")
        resolver = MagicMock()
        resolver.resolve = AsyncMock(
            return_value=IdentityResolution(
                user_id="u-ctx",
                bound=True,
                reason="binding_open_id",
            )
        )
        service = InboundMessageService(identity_resolver=resolver)

        with (
            patch("app.services.im.SessionLocal", return_value=_db_session()),
            patch.object(
                ChannelRepository,
                "get_by_provider_destination",
                return_value=None,
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
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(InboundMessageService, "_send_reply", new=AsyncMock()),
        ):
            with self.assertRaises(RuntimeError):
                await service.handle_message(message=msg)

        # After the (failed) call, the ContextVar must be cleared so
        # the next message on the same task does not see stale ids.
        self.assertIsNone(_current_inbound_sender_open_id())


if __name__ == "__main__":
    unittest.main()
