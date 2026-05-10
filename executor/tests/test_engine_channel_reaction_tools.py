import unittest
from types import SimpleNamespace
from typing import Any, cast

from app.core.engine import AgentExecutor
from app.schemas.request import TaskConfig


class AgentExecutorChannelReactionTests(unittest.TestCase):
    def test_compose_prompt_includes_channel_reaction_contract(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "React to the update",
            TaskConfig(
                server_id="00000000-0000-0000-0000-000000000001",
                channel_id="00000000-0000-0000-0000-000000000002",
                agent_identity_id="00000000-0000-0000-0000-000000000003",
                agent_runtime_mode="persistent",
            ),
            cwd="/workspace/demo",
        )

        self.assertIn("add_channel_message_reaction", prompt)
        self.assertIn("remove_channel_message_reaction", prompt)
        self.assertIn("do not pass or invent actor identity", prompt)

    def test_compose_prompt_omits_reaction_contract_without_channel_scope(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "React to the update",
            TaskConfig(agent_runtime_mode="persistent"),
            cwd="/workspace/demo",
        )

        self.assertNotIn("add_channel_message_reaction", prompt)
        self.assertNotIn("remove_channel_message_reaction", prompt)

    def test_inject_channel_runtime_mcp_only_when_configured(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)
        executor.channel_runtime_mcp_server = cast(
            Any,
            SimpleNamespace(name="runtime-server"),
        )

        injected = executor._inject_channel_runtime_mcp({})

        self.assertIn("__poco_channel_runtime", injected)

    def test_inject_channel_runtime_mcp_is_noop_without_server(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)
        executor.channel_runtime_mcp_server = None

        injected = executor._inject_channel_runtime_mcp({"custom": {}})

        self.assertEqual(injected, {"custom": {}})

    def test_old_channel_task_mcp_injector_is_removed(self) -> None:
        self.assertFalse(hasattr(AgentExecutor, "_inject_channel_tasks_mcp"))


if __name__ == "__main__":
    unittest.main()
