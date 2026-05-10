import type {
  ServerConversationMessage,
  ServerConversationMessageReactionActor,
  ServerConversationMessageReactionGroup,
  ServerUserPublicProfile,
} from "@/features/servers/model/types";

function toggleReactionGroups(
  groups: ServerConversationMessageReactionGroup[],
  emoji: string,
  currentUser?: ServerUserPublicProfile | null,
): ServerConversationMessageReactionGroup[] {
  const existing = groups.find((group) => group.emoji === emoji);
  const currentActor: ServerConversationMessageReactionActor | null =
    currentUser
      ? {
          actorType: "user",
          userId: currentUser.userId,
          user: currentUser,
        }
      : null;
  if (!existing) {
    return [
      ...groups,
      {
        emoji,
        count: 1,
        reactedByCurrentUser: true,
        reactedByCurrentAgent: false,
        actors: currentActor ? [currentActor] : [],
      },
    ];
  }
  if (existing.reactedByCurrentUser) {
    return groups
      .map((group) =>
        group.emoji === emoji
          ? {
              ...group,
              count: Math.max(0, group.count - 1),
              reactedByCurrentUser: false,
              actors: currentUser
                ? group.actors.filter(
                    (actor) =>
                      actor.actorType !== "user" ||
                      actor.userId !== currentUser.userId,
                  )
                : group.actors,
            }
          : group,
      )
      .filter((group) => group.count > 0);
  }
  return groups.map((group) =>
    group.emoji === emoji
      ? {
          ...group,
          count: group.count + 1,
          reactedByCurrentUser: true,
          actors:
            currentActor &&
            !group.actors.some(
              (actor) =>
                actor.actorType === "user" &&
                actor.userId === currentUser?.userId,
            )
              ? [...group.actors, currentActor]
              : group.actors,
        }
      : group,
  );
}

export function toggleMessageReaction(
  message: ServerConversationMessage,
  emoji: string,
  currentUser?: ServerUserPublicProfile | null,
): ServerConversationMessage {
  return {
    ...message,
    reactions: toggleReactionGroups(
      message.reactions ?? [],
      emoji,
      currentUser,
    ),
  };
}

export function updateMessageById(
  messages: ServerConversationMessage[],
  messageId: string,
  update: (message: ServerConversationMessage) => ServerConversationMessage,
): ServerConversationMessage[] {
  let changed = false;
  const next = messages.map((message) => {
    if (message.id !== messageId) {
      return message;
    }
    changed = true;
    return update(message);
  });
  return changed ? next : messages;
}
