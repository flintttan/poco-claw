import type { ServerConversationMessage } from "@/features/servers/model/types";

export function getServerMessageText(
  message: ServerConversationMessage,
): string {
  const text = message.content.text;
  if (typeof text === "string" && text.trim()) {
    return text.trim();
  }
  if (message.textPreview?.trim()) {
    return message.textPreview.trim();
  }
  const title = message.content.title;
  if (typeof title === "string" && title.trim()) {
    return title.trim();
  }
  return "";
}
