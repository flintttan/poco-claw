import type { ServerConversationMessage } from "@/features/servers/model/types";

export function getMessageSessionId(
  message: ServerConversationMessage,
): string | null {
  if (message.messageType !== "system") {
    return null;
  }
  const rawSessionId = message.content.session_id;
  if (typeof rawSessionId !== "string") {
    return null;
  }
  const sessionId = rawSessionId.trim();
  return sessionId ? sessionId : null;
}

export function isExecutionDrilldownMessage(
  message: ServerConversationMessage,
): boolean {
  if (message.messageType !== "system") {
    return false;
  }
  const source =
    typeof message.content.source === "string"
      ? message.content.source.trim().toLowerCase()
      : "";
  if (source !== "agent_execution" && source !== "agent_session") {
    return false;
  }
  return getMessageSessionId(message) !== null;
}
