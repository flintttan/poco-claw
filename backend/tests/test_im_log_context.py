"""Tests for the structured-log ``extra`` field helpers.

The helpers centralise the field set so every log site emits a
consistent shape — without them, some sites include ``user_id``,
some include ``sender_open_id``, and operators end up with a
schemaless mess in the log pipeline.
"""

from __future__ import annotations

import unittest

from app.schemas.im import (
    EventStateSnapshot,
    ImBackendEvent,
    InboundMessage,
    SessionSnapshot,
)
from app.services.im_log_context import (
    event_log_context,
    inbound_message_log_context,
)


def _inbound(**overrides) -> InboundMessage:
    base = dict(
        provider="feishu",
        destination="oc-abc",
        message_id="m-1",
        text="hello",
        chat_type="group",
        sender_open_id="ou-1",
        sender_union_id="on-1",
    )
    base.update(overrides)
    return InboundMessage(**base)


def _event(**overrides) -> ImBackendEvent:
    payload = {
        "id": "evt-1",
        "type": "assistant_message.created",
        "occurred_at": "2026-01-01T00:00:00Z",
        "user_id": "u-1",
        "session": SessionSnapshot(id="s-1", title="t", status="running"),
        "state": EventStateSnapshot(),
    }
    payload.update(overrides)
    return ImBackendEvent.model_validate(payload)


class InboundMessageLogContextTests(unittest.TestCase):
    def test_includes_canonical_fields(self) -> None:
        ctx = inbound_message_log_context(_inbound())
        self.assertEqual(ctx["provider"], "feishu")
        self.assertEqual(ctx["destination"], "oc-abc")
        self.assertEqual(ctx["message_id"], "m-1")
        self.assertEqual(ctx["chat_type"], "group")

    def test_includes_sender_ids_when_present(self) -> None:
        ctx = inbound_message_log_context(_inbound())
        self.assertEqual(ctx["sender_open_id"], "ou-1")
        self.assertEqual(ctx["sender_union_id"], "on-1")

    def test_omits_missing_sender_ids(self) -> None:
        # p2p messages from a provider that does not surface union_id
        # must not emit a None key — that would force every log
        # consumer to handle the null case.
        msg = _inbound(sender_union_id=None)
        ctx = inbound_message_log_context(msg)
        self.assertIn("sender_open_id", ctx)
        self.assertNotIn("sender_union_id", ctx)

    def test_includes_user_id_when_provided(self) -> None:
        ctx = inbound_message_log_context(_inbound(), user_id="u-1")
        self.assertEqual(ctx["user_id"], "u-1")

    def test_omits_user_id_when_not_resolved(self) -> None:
        ctx = inbound_message_log_context(_inbound())
        self.assertNotIn("user_id", ctx)

    def test_includes_channel_id_when_provided(self) -> None:
        ctx = inbound_message_log_context(_inbound(), channel_id=42)
        self.assertEqual(ctx["channel_id"], 42)

    def test_omits_channel_id_when_not_provided(self) -> None:
        ctx = inbound_message_log_context(_inbound())
        self.assertNotIn("channel_id", ctx)

    def test_extras_override_base(self) -> None:
        # ``extras`` win over base fields so a log site can pin a
        # destination override (e.g. for reply failure) without
        # worrying about key collisions.
        ctx = inbound_message_log_context(_inbound(), destination="oc-reply")
        self.assertEqual(ctx["destination"], "oc-reply")

    def test_extras_arbitrary_keys(self) -> None:
        ctx = inbound_message_log_context(_inbound(), reason="acl_fail", attempt=3)
        self.assertEqual(ctx["reason"], "acl_fail")
        self.assertEqual(ctx["attempt"], 3)


class EventLogContextTests(unittest.TestCase):
    def test_includes_canonical_fields(self) -> None:
        ctx = event_log_context(_event())
        self.assertEqual(ctx["event_id"], "evt-1")
        self.assertEqual(ctx["event_type"], "assistant_message.created")
        self.assertEqual(ctx["session_id"], "s-1")
        self.assertEqual(ctx["user_id"], "u-1")

    def test_extras_merged(self) -> None:
        ctx = event_log_context(_event(), reason="empty_user_id")
        self.assertEqual(ctx["reason"], "empty_user_id")
        # Base fields still present.
        self.assertEqual(ctx["event_id"], "evt-1")


if __name__ == "__main__":
    unittest.main()
