import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.errors.exceptions import AppException
from app.services.channel_runtime_scope_service import ChannelRuntimeScopeService


class ChannelRuntimeScopeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = MagicMock()
        self.session_id = uuid.uuid4()
        self.server_id = uuid.uuid4()
        self.channel_id = uuid.uuid4()
        self.agent_identity_id = uuid.uuid4()
        self.trigger_message_id = uuid.uuid4()
        self.thread_root_message_id = uuid.uuid4()
        self.service = ChannelRuntimeScopeService()

    def test_resolve_scope_reads_channel_identity_from_session_snapshot(self) -> None:
        session = SimpleNamespace(
            id=self.session_id,
            user_id="agent-owner",
            config_snapshot={
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_identity_id),
                "trigger_message_id": str(self.trigger_message_id),
                "thread_root_message_id": str(self.thread_root_message_id),
                "trigger_context": {
                    "handoff": {"depth": 1, "dedupe_key": "existing-key"}
                },
            },
        )
        agent = SimpleNamespace(
            id=self.agent_identity_id,
            server_id=self.server_id,
            handle="reviewer",
            display_name="Reviewer",
            preset_id=9,
            lifecycle_state="active",
        )
        membership = SimpleNamespace(status="active")

        with (
            patch(
                "app.services.channel_runtime_scope_service.SessionRepository.get_by_id",
                return_value=session,
            ),
            patch(
                "app.services.channel_runtime_scope_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
            patch(
                "app.services.channel_runtime_scope_service.ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=membership,
            ),
        ):
            scope = self.service.resolve_scope(self.db, session_id=self.session_id)

        self.assertEqual(scope.session_id, self.session_id)
        self.assertEqual(scope.user_id, "agent-owner")
        self.assertEqual(scope.server_id, self.server_id)
        self.assertEqual(scope.channel_id, self.channel_id)
        self.assertEqual(scope.agent_identity_id, self.agent_identity_id)
        self.assertEqual(scope.trigger_message_id, self.trigger_message_id)
        self.assertEqual(scope.thread_root_message_id, self.thread_root_message_id)
        self.assertEqual(scope.handoff_depth, 1)
        self.assertEqual(scope.agent_handle, "reviewer")

    def test_resolve_scope_rejects_inactive_channel_membership(self) -> None:
        session = SimpleNamespace(
            id=self.session_id,
            user_id="agent-owner",
            config_snapshot={
                "server_id": str(self.server_id),
                "channel_id": str(self.channel_id),
                "agent_identity_id": str(self.agent_identity_id),
            },
        )
        agent = SimpleNamespace(
            id=self.agent_identity_id,
            server_id=self.server_id,
            handle="reviewer",
            display_name="Reviewer",
            preset_id=9,
            lifecycle_state="active",
        )
        membership = SimpleNamespace(status="removed")

        with (
            patch(
                "app.services.channel_runtime_scope_service.SessionRepository.get_by_id",
                return_value=session,
            ),
            patch(
                "app.services.channel_runtime_scope_service.AgentIdentityRepository.get_by_id",
                return_value=agent,
            ),
            patch(
                "app.services.channel_runtime_scope_service.ServerChannelAgentMemberRepository.get_by_channel_and_agent",
                return_value=membership,
            ),
        ):
            with self.assertRaises(AppException) as context:
                self.service.resolve_scope(self.db, session_id=self.session_id)

        self.assertIn("active member", str(context.exception))


if __name__ == "__main__":
    unittest.main()
