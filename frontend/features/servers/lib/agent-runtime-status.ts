import type { ServerAgentItem } from "@/features/servers/model/types";

export type AgentRuntimeTone = "success" | "warning" | "danger" | "muted";

export function getAgentRuntimeStatus(agent: ServerAgentItem): {
  labelKey:
    | "conversationView.colleagues.runtimeStates.active"
    | "conversationView.colleagues.runtimeStates.idle"
    | "conversationView.colleagues.runtimeStates.stopped"
    | "conversationView.colleagues.runtimeStates.removed"
    | "conversationView.colleagues.runtimeStates.failed"
    | "conversationView.colleagues.runtimeStates.unknown";
  tone: AgentRuntimeTone;
} {
  const lifecycleState = (agent.lifecycleState || "").trim().toLowerCase();
  const runtimeStatus = (agent.persistentState?.runtimeStatus || "")
    .trim()
    .toLowerCase();

  if (agent.removedAt) {
    return {
      labelKey: "conversationView.colleagues.runtimeStates.removed",
      tone: "muted",
    };
  }

  if (lifecycleState === "inactive") {
    return {
      labelKey: "conversationView.colleagues.runtimeStates.stopped",
      tone: "muted",
    };
  }

  if (
    runtimeStatus === "busy" ||
    agent.persistentState?.activeSessionId ||
    agent.persistentState?.activeTaskId
  ) {
    return {
      labelKey: "conversationView.colleagues.runtimeStates.active",
      tone: "warning",
    };
  }

  if (runtimeStatus === "failed") {
    return {
      labelKey: "conversationView.colleagues.runtimeStates.failed",
      tone: "danger",
    };
  }

  if (runtimeStatus === "idle" || runtimeStatus === "active") {
    return {
      labelKey: "conversationView.colleagues.runtimeStates.idle",
      tone: "success",
    };
  }

  return {
    labelKey: "conversationView.colleagues.runtimeStates.unknown",
    tone: "muted",
  };
}

export function getAgentRuntimeDotClassName(tone: AgentRuntimeTone): string {
  switch (tone) {
    case "success":
      return "bg-emerald-500";
    case "warning":
      return "bg-amber-500";
    case "danger":
      return "bg-rose-500";
    default:
      return "bg-muted-foreground/50";
  }
}
