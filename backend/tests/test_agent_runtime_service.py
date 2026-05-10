import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.agent_persistent_state import AgentPersistentState
from app.services.agent_runtime_service import AgentRuntimeService


class AgentRuntimeServiceTests(unittest.TestCase):
    def test_reserve_persistent_runtime_rejects_busy_other_session(self) -> None:
        db = MagicMock()
        service = AgentRuntimeService()
        state = AgentPersistentState(
            id=uuid.uuid4(),
            agent_identity_id=uuid.uuid4(),
            state_root_path="agents/demo",
            profile_path="agents/demo/profile.json",
            memory_path="agents/demo/MEMORY.md",
            notes_dir_path="agents/demo/notes",
            state_dir_path="agents/demo/state",
            artifacts_dir_path="agents/demo/artifacts",
            state_version=1,
            runtime_status="busy",
            active_task_id=None,
            active_session_id=uuid.uuid4(),
            last_synced_at=None,
            last_written_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with patch.object(service, "get_persistent_state", return_value=state):
            with self.assertRaisesRegex(Exception, "busy"):
                service.reserve_persistent_runtime(
                    db,
                    agent_identity_id=state.agent_identity_id,
                    session_id=uuid.uuid4(),
                    channel_task_id=None,
                )

    def test_release_runtime_for_session_resets_to_idle(self) -> None:
        db = MagicMock()
        session_id = uuid.uuid4()
        state = AgentPersistentState(
            id=uuid.uuid4(),
            agent_identity_id=uuid.uuid4(),
            state_root_path="agents/demo",
            profile_path="agents/demo/profile.json",
            memory_path="agents/demo/MEMORY.md",
            notes_dir_path="agents/demo/notes",
            state_dir_path="agents/demo/state",
            artifacts_dir_path="agents/demo/artifacts",
            state_version=1,
            runtime_status="busy",
            active_task_id=uuid.uuid4(),
            active_session_id=session_id,
            last_synced_at=None,
            last_written_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.query.return_value.filter.return_value.first.return_value = state

        result = AgentRuntimeService().release_runtime_for_session(
            db,
            session_id=session_id,
            callback_status="completed",
        )

        self.assertIs(result, state)
        self.assertEqual(state.runtime_status, "idle")
        self.assertIsNone(state.active_session_id)
        self.assertIsNone(state.active_task_id)


if __name__ == "__main__":
    unittest.main()
