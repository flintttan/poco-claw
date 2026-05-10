import test from "node:test";
import assert from "node:assert/strict";

import { parseMessages } from "./message-parser.ts";

test("parseMessages maps trigger_context metadata onto user messages", () => {
  const triggerContext = {
    version: 1,
    trigger_type: "channel_mention",
    server_id: "server-1",
    channel_id: "channel-1",
    trigger_message_id: "message-1",
    thread_root_message_id: "thread-1",
    target_agent_identity_id: "agent-1",
    target_agent_handle: "reviewer",
    source_actor: {
      actor_type: "user",
      user_id: "user-1",
      display_name: "Alice",
    },
  };

  const parsed = parseMessages([
    {
      id: 42,
      role: "user",
      created_at: "2026-05-08T00:00:00Z",
      updated_at: "2026-05-08T00:00:00Z",
      content: {
        _type: "UserMessage",
        content: [{ _type: "TextBlock", text: "Please review this" }],
        metadata: {
          trigger_context: triggerContext,
        },
      },
    },
  ]);

  assert.equal(parsed.messages.length, 1);
  assert.equal(parsed.messages[0].content, "Please review this");
  assert.deepEqual(parsed.messages[0].metadata?.triggerContext, triggerContext);
});

test("parseMessages leaves plain user messages without triggerContext", () => {
  const parsed = parseMessages([
    {
      id: 43,
      role: "user",
      created_at: "2026-05-08T00:00:00Z",
      updated_at: "2026-05-08T00:00:00Z",
      content: {
        _type: "UserMessage",
        content: [{ _type: "TextBlock", text: "Plain prompt" }],
      },
    },
  ]);

  assert.equal(parsed.messages.length, 1);
  assert.equal(parsed.messages[0].metadata?.triggerContext, undefined);
});
