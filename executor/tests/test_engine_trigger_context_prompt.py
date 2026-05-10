import unittest

from app.core.engine import AgentExecutor
from app.schemas.request import TaskConfig


class AgentExecutorTriggerContextPromptTests(unittest.TestCase):
    def test_compose_prompt_includes_compact_trigger_context(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Please review this API error handling",
            TaskConfig(
                server_id="00000000-0000-0000-0000-000000000001",
                channel_id="00000000-0000-0000-0000-000000000002",
                agent_identity_id="00000000-0000-0000-0000-000000000003",
                agent_runtime_mode="persistent",
                trigger_context={
                    "version": 1,
                    "trigger_type": "channel_mention",
                    "server_id": "00000000-0000-0000-0000-000000000001",
                    "channel_id": "00000000-0000-0000-0000-000000000002",
                    "trigger_message_id": "00000000-0000-0000-0000-000000000004",
                    "thread_root_message_id": "00000000-0000-0000-0000-000000000005",
                    "target_agent_identity_id": "00000000-0000-0000-0000-000000000003",
                    "target_agent_handle": "reviewer",
                    "source_actor": {
                        "actor_type": "user",
                        "user_id": "user-1",
                        "display_name": "Alice",
                    },
                    "references": {
                        "message_ids": ["00000000-0000-0000-0000-000000000004"],
                        "artifact_ids": [],
                        "task_ids": [],
                    },
                    "handoff": {
                        "depth": 0,
                        "dedupe_key": "channel-trigger:msg:agent",
                    },
                },
            ),
            cwd="/workspace/demo",
        )

        self.assertIn("Channel trigger context:", prompt)
        self.assertIn("trigger_type: channel_mention", prompt)
        self.assertIn(
            "trigger_message_id: 00000000-0000-0000-0000-000000000004", prompt
        )
        self.assertIn(
            "thread_root_message_id: 00000000-0000-0000-0000-000000000005", prompt
        )
        self.assertIn("target_agent_handle: reviewer", prompt)
        self.assertIn("source_actor: user Alice (user-1)", prompt)
        self.assertIn("This is a channel collaboration run", prompt)
        self.assertIn("Field meanings:", prompt)
        self.assertIn("trigger_type: how this run was started", prompt)
        self.assertIn("target_agent_handle is your channel handle in this run", prompt)
        self.assertIn("Other named people or agents in the user request", prompt)
        self.assertIn("Use list_channel_agents", prompt)
        self.assertIn("Use read_channel_messages", prompt)
        self.assertIn("list_channel_artifacts", prompt)
        self.assertIn("Please review this API error handling", prompt)

    def test_compose_prompt_omits_trigger_context_for_plain_run(self) -> None:
        executor = AgentExecutor.__new__(AgentExecutor)

        prompt = executor._compose_user_prompt(
            "Review the issue",
            TaskConfig(agent_runtime_mode="persistent"),
            cwd="/workspace/demo",
        )

        self.assertNotIn("Channel trigger context:", prompt)
        self.assertNotIn("read_channel_messages", prompt)


if __name__ == "__main__":
    unittest.main()
