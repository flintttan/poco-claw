import unittest

from app.core.engine import AgentExecutor
from app.schemas.request import TaskConfig


class AgentExecutorChannelTaskHintTests(unittest.TestCase):
    def test_compose_prompt_includes_channel_task_hint_for_channel_scoped_agent(
        self,
    ) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Review the issue",
            TaskConfig(
                server_id="00000000-0000-0000-0000-000000000001",
                channel_id="00000000-0000-0000-0000-000000000002",
                agent_identity_id="00000000-0000-0000-0000-000000000003",
                agent_runtime_mode="persistent",
            ),
            cwd="/workspace/demo",
        )

        self.assertIn("create_channel_task", prompt)
        self.assertIn("update_channel_task_status", prompt)
        self.assertIn("claim_channel_task", prompt)
        self.assertIn("comment_on_channel_task", prompt)

    def test_compose_prompt_omits_channel_task_hint_without_channel_scope(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Review the issue",
            TaskConfig(agent_runtime_mode="persistent"),
            cwd="/workspace/demo",
        )

        self.assertNotIn("create_channel_task", prompt)
        self.assertNotIn("comment_on_channel_task", prompt)


if __name__ == "__main__":
    unittest.main()
