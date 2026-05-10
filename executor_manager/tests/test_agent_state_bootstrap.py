import json
import tempfile
import unittest
from pathlib import Path

from app.core.settings import Settings
from app.services.workspace_manager import WorkspaceManager


class WorkspaceManagerAgentStateBootstrapTests(unittest.TestCase):
    def _build_manager(self, temp_dir: str) -> WorkspaceManager:
        manager = WorkspaceManager.__new__(WorkspaceManager)
        manager.settings = Settings()
        manager.base_dir = Path(temp_dir)
        manager.active_dir = manager.base_dir / "active"
        manager.archive_dir = manager.base_dir / "archive"
        manager.temp_dir = manager.base_dir / "temp"
        manager.ignore_dot_files = manager.settings.workspace_ignore_dot_files
        manager._init_directories()
        manager._ignore_names = set()
        return manager

    def test_get_agent_state_dir_seeds_non_empty_bootstrap_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self._build_manager(temp_dir)

            agent_dir = manager.get_agent_state_dir("agent-123", create=True)

            profile_data = json.loads((agent_dir / "profile.json").read_text())
            self.assertEqual(profile_data["schema_version"], 1)
            self.assertEqual(profile_data["agent"]["id"], "agent-123")
            self.assertEqual(profile_data["runtime"]["mode"], "persistent")

            self.assertTrue((agent_dir / "MEMORY.md").read_text().strip())
            self.assertTrue(
                (agent_dir / "notes" / "active-context.md").read_text().strip()
            )

            task_state = json.loads(
                (agent_dir / "state" / "task-state.json").read_text()
            )
            self.assertEqual(task_state["schema_version"], 1)

    def test_get_agent_state_dir_keeps_non_empty_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self._build_manager(temp_dir)
            agent_dir = Path(temp_dir) / "agents" / "agent-123"
            (agent_dir / "notes").mkdir(parents=True, exist_ok=True)
            (agent_dir / "state").mkdir(parents=True, exist_ok=True)
            (agent_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (agent_dir / "MEMORY.md").write_text("custom memory", encoding="utf-8")
            (agent_dir / "profile.json").write_text(
                json.dumps({"custom": True}), encoding="utf-8"
            )

            resolved = manager.get_agent_state_dir("agent-123", create=True)

            self.assertEqual(resolved, agent_dir)
            self.assertEqual(
                (agent_dir / "MEMORY.md").read_text(encoding="utf-8"), "custom memory"
            )
            self.assertEqual(
                json.loads((agent_dir / "profile.json").read_text(encoding="utf-8")),
                {"custom": True},
            )


if __name__ == "__main__":
    unittest.main()
