"""Tests for the batch-fetched ``_get_target_channel_ids`` implementation.

N6 was an N+1 query problem: every candidate ``channel_id`` from the
watch/active lists triggered its own ``ChannelRepository.get_by_id``,
plus a ``ServerRepository.get_by_id`` and a
``ServerMemberRepository.get_by_server_and_user`` for every
server-bound channel. With a busy session that fan-out was visible
in slow-log traces.

The fix consolidates those into one query each:

- ``ChannelRepository.list_by_ids``
- ``ServerRepository.list_by_ids``
- ``ServerMemberRepository.list_active_by_user_and_servers``

These tests assert that the batch methods are used (not the per-id
ones) so a future regression that re-introduces a per-id loop
fails loudly.
"""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import MagicMock, patch

from app.repositories.im import (
    ActiveSessionRepository,
    ChannelRepository,
    WatchRepository,
)
from app.repositories.server_member_repository import ServerMemberRepository


def _channel(*, channel_id: int, owner_user_id: str, server_id=None):
    channel = MagicMock()
    channel.id = channel_id
    channel.owner_user_id = owner_user_id
    channel.server_id = server_id
    channel.enabled = True
    channel.subscribe_all = False
    return channel


def _service() -> MagicMock:
    # The class under test is constructed by ``_service`` indirectly;
    # we just need the method binding.
    from app.services.im import BackendEventService

    return BackendEventService()


class NPlusOneRegressionTests(unittest.TestCase):
    """Assert the batch methods are called instead of per-id methods."""

    def test_uses_batch_channel_lookup(self) -> None:
        watch = MagicMock()
        watch.channel_id = 100
        owner_channel = _channel(channel_id=100, owner_user_id="u-owner")

        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[watch]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(
                ChannelRepository, "list_by_ids", return_value=[owner_channel]
            ) as list_by_ids,
            patch.object(ChannelRepository, "get_by_id") as get_by_id,
            patch(
                "app.repositories.server_repository.ServerRepository"
            ) as server_repo_mock,
            patch.object(
                ServerMemberRepository,
                "list_active_by_user_and_servers",
                return_value=[],
            ),
        ):
            server_repo_mock.list_by_ids = MagicMock(return_value=[])
            target = _service()._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-owner"
            )

        self.assertIn(100, target)
        # The batch lookup was used; the per-id one was not.
        list_by_ids.assert_called_once()
        get_by_id.assert_not_called()

    def test_server_bound_uses_batch_server_lookup(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(channel_id=200, owner_user_id="u-owner", server_id=server_id)
        watch = MagicMock()
        watch.channel_id = 200
        membership = MagicMock()
        membership.server_id = server_id
        membership.status = "active"
        server = MagicMock()
        server.id = server_id
        server.is_deleted = False

        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[watch]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(ChannelRepository, "list_by_ids", return_value=[channel]),
            patch(
                "app.repositories.server_repository.ServerRepository"
            ) as server_repo_mock,
            patch.object(
                ServerMemberRepository,
                "list_active_by_user_and_servers",
                return_value=[membership],
            ),
        ):
            server_repo_mock.list_by_ids = MagicMock(return_value=[server])
            server_repo_mock.get_by_id = MagicMock(return_value=server)
            target = _service()._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-member"
            )

        self.assertIn(200, target)
        # Batch server lookup is the only path.
        server_repo_mock.list_by_ids.assert_called_once()
        # ``get_by_id`` must NOT be called in the batch implementation.
        server_repo_mock.get_by_id.assert_not_called()

    def test_membership_query_uses_batch_method(self) -> None:
        server_id = uuid.uuid4()
        channel = _channel(channel_id=300, owner_user_id="u-owner", server_id=server_id)
        watch = MagicMock()
        watch.channel_id = 300
        membership = MagicMock()
        membership.server_id = server_id
        server = MagicMock()
        server.id = server_id
        server.is_deleted = False

        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[watch]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(ChannelRepository, "list_by_ids", return_value=[channel]),
            patch(
                "app.repositories.server_repository.ServerRepository"
            ) as server_repo_mock,
            patch.object(
                ServerMemberRepository,
                "list_active_by_user_and_servers",
                return_value=[membership],
            ) as memberships_call,
            patch.object(
                ServerMemberRepository, "get_by_server_and_user"
            ) as per_id_call,
        ):
            server_repo_mock.list_by_ids = MagicMock(return_value=[server])
            _service()._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-member"
            )

        memberships_call.assert_called_once()
        per_id_call.assert_not_called()


class EdgeCaseTests(unittest.TestCase):
    """Cover the boundary conditions the new code path introduces."""

    def test_empty_candidates_returns_empty(self) -> None:
        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(ChannelRepository, "list_by_ids", return_value=[]) as batch,
        ):
            target = _service()._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-x"
            )
        # Short-circuit: no batch query needed when the candidate set
        # is empty.
        batch.assert_not_called()
        self.assertEqual(target, set())

    def test_disabled_channel_filtered(self) -> None:
        watch = MagicMock()
        watch.channel_id = 400
        disabled = _channel(channel_id=400, owner_user_id="u-owner")
        disabled.enabled = False

        with (
            patch.object(ChannelRepository, "list_enabled", return_value=[]),
            patch.object(WatchRepository, "list_by_session", return_value=[watch]),
            patch.object(ActiveSessionRepository, "list_by_session", return_value=[]),
            patch.object(ChannelRepository, "list_by_ids", return_value=[disabled]),
        ):
            target = _service()._get_target_channel_ids(
                MagicMock(), session_id="s-1", event_user_id="u-owner"
            )

        self.assertNotIn(400, target)


if __name__ == "__main__":
    unittest.main()
