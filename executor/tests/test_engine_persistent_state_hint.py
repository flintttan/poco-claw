import unittest

from app.core.engine import AgentExecutor
from app.schemas.request import TaskConfig


class AgentExecutorPersistentStateHintTests(unittest.TestCase):
    def test_compose_prompt_includes_persistent_state_contract(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Review the issue",
            TaskConfig(agent_runtime_mode="persistent"),
            cwd="/workspace/demo",
        )

        self.assertIn("/agent_state", prompt)
        self.assertIn("MEMORY.md", prompt)
        self.assertIn("profile.json", prompt)
        self.assertIn("published artifacts", prompt)

    def test_compose_prompt_omits_write_contract_for_temporary_runtime(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Review the issue",
            TaskConfig(agent_runtime_mode="temporary"),
            cwd="/workspace/demo",
        )

        self.assertNotIn("MEMORY.md", prompt)
        self.assertNotIn("profile.json", prompt)
        self.assertIn("Current working directory", prompt)


if __name__ == "__main__":
    unittest.main()
