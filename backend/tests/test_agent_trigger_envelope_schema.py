import unittest
import uuid
from typing import Any, cast

from pydantic import ValidationError

from app.schemas.agent_trigger import AgentTriggerEnvelope


class AgentTriggerEnvelopeSchemaTests(unittest.TestCase):
    def test_valid_channel_mention_envelope_serializes_to_json(self) -> None:
        server_id = uuid.uuid4()
        channel_id = uuid.uuid4()
        message_id = uuid.uuid4()
        agent_id = uuid.uuid4()

        envelope = AgentTriggerEnvelope(
            trigger_type="channel_mention",
            server_id=server_id,
            channel_id=channel_id,
            trigger_message_id=message_id,
            thread_root_message_id=message_id,
            target_agent_identity_id=agent_id,
            target_agent_handle="reviewer",
            source_actor={
                "actor_type": "user",
                "user_id": "user-1",
                "display_name": "Alice",
            },
            references={"message_ids": [message_id]},
            handoff={
                "dedupe_key": f"channel-trigger:{message_id}:{agent_id}",
            },
        )

        payload = envelope.model_dump(mode="json")

        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["server_id"], str(server_id))
        self.assertEqual(payload["references"]["message_ids"], [str(message_id)])
        self.assertEqual(
            payload["handoff"]["dedupe_key"],
            f"channel-trigger:{message_id}:{agent_id}",
        )

    def test_invalid_trigger_type_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            AgentTriggerEnvelope(
                trigger_type=cast(Any, "plain_text"),
                server_id=uuid.uuid4(),
                channel_id=uuid.uuid4(),
                trigger_message_id=uuid.uuid4(),
                target_agent_identity_id=uuid.uuid4(),
                target_agent_handle="reviewer",
                source_actor={"actor_type": "user"},
            )


if __name__ == "__main__":
    unittest.main()
