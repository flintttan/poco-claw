import unittest

from app.core.engine import AgentExecutor
from app.schemas.request import TaskConfig


class AgentExecutorChannelRuntimeHintTests(unittest.TestCase):
    def test_compose_prompt_includes_message_and_collaboration_runtime_tools(
        self,
    ) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Coordinate with the API agent",
            TaskConfig(
                server_id="00000000-0000-0000-0000-000000000001",
                channel_id="00000000-0000-0000-0000-000000000002",
                agent_identity_id="00000000-0000-0000-0000-000000000003",
                agent_runtime_mode="persistent",
            ),
            cwd="/workspace/demo",
        )

        self.assertIn("read_channel_messages", prompt)
        self.assertIn("list_channel_agents", prompt)
        self.assertIn("request_agent_collaboration", prompt)
        self.assertIn("list_channel_tasks", prompt)
        self.assertIn("read_channel_task", prompt)
        self.assertIn("Agent output that mentions @handle is visible text only", prompt)


if __name__ == "__main__":
    unittest.main()
