"use client";

import * as React from "react";
import { Bookmark, Inbox, MailOpen, Search } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { FeedItem } from "@/features/servers/ui/server-workspace-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

import { MessageRow } from "./conversation-message-row";

export function SearchPanel({
  search,
  onSearchChange,
  items,
  savedMessageIds,
  currentUserId,
  onOpenThread,
  onOpenExecution,
  onToggleSaved,
  onToggleReaction,
}: {
  search: string;
  onSearchChange: (value: string) => void;
  items: FeedItem[];
  savedMessageIds: Set<string>;
  currentUserId?: string | null;
  onOpenThread: (item: FeedItem) => void;
  onOpenExecution?: (sessionId: string) => void;
  onToggleSaved: (messageId: string) => void;
  onToggleReaction?: (item: FeedItem, emoji: string) => void;
}) {
  const { t } = useT("translation");
  const [mineOnly, setMineOnly] = React.useState(false);
  const [timeFilter, setTimeFilter] = React.useState<"any" | "today">("any");

  const visibleItems = React.useMemo(() => {
    const now = new Date();
    return items.filter((item) => {
      if (mineOnly && item.message.authorUserId !== currentUserId) {
        return false;
      }
      if (timeFilter === "today") {
        const createdAt = new Date(item.message.createdAt);
        return (
          createdAt.getFullYear() === now.getFullYear() &&
          createdAt.getMonth() === now.getMonth() &&
          createdAt.getDate() === now.getDate()
        );
      }
      return true;
    });
  }, [currentUserId, items, mineOnly, timeFilter]);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background">
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-md border border-border bg-muted text-foreground">
            <Search className="size-4" />
          </div>
          <div className="flex-1 rounded-md border border-border bg-background px-3 py-2.5">
            <input
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder={t("conversationView.searchPlaceholder")}
              className="w-full border-none bg-transparent text-base text-foreground outline-none placeholder:text-muted-foreground"
            />
          </div>
        </div>
      </div>
      <div className="border-b border-border px-6 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={timeFilter}
            onValueChange={(value) =>
              setTimeFilter(value === "today" ? "today" : "any")
            }
          >
            <SelectTrigger className="h-9 w-fit min-w-32 border-border bg-card text-xs font-medium uppercase tracking-wide text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="start">
              <SelectItem value="any">
                {t("conversationView.anyTime")}
              </SelectItem>
              <SelectItem value="today">
                {t("conversationView.today")}
              </SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center gap-1 rounded-md border border-border bg-card p-1">
            <button
              type="button"
              onClick={() => setMineOnly(false)}
              className={cn(
                "rounded-sm px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-foreground transition-colors",
                !mineOnly
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted/30",
              )}
            >
              {t("conversationView.all")}
            </button>
            <button
              type="button"
              onClick={() => setMineOnly(true)}
              className={cn(
                "rounded-sm px-3 py-1.5 text-xs font-medium uppercase tracking-wide text-foreground transition-colors",
                mineOnly
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted/30",
              )}
            >
              {t("conversationView.myMessages")}
            </button>
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto bg-background">
        {visibleItems.length > 0 ? (
          visibleItems.map((item) => (
            <MessageRow
              key={item.message.id}
              message={item.message}
              channelLabel={item.channel.name}
              isSaved={savedMessageIds.has(item.message.id)}
              compact
              onOpenThread={() => onOpenThread(item)}
              onOpenExecution={onOpenExecution}
              onToggleSaved={() => onToggleSaved(item.message.id)}
              onToggleReaction={(emoji) => onToggleReaction?.(item, emoji)}
            />
          ))
        ) : (
          <div className="flex h-full min-h-[20rem] items-center justify-center px-8 text-center">
            <div className="space-y-3">
              <Search className="mx-auto size-10 text-muted-foreground/40" />
              <p className="text-xl font-semibold text-foreground">
                {t("conversationView.searchEverything")}
              </p>
              <p className="max-w-md text-sm text-muted-foreground">
                {t("conversationView.searchEverythingDescription")}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function FeedPanel({
  inboxItems,
  savedItems,
  savedMessageIds,
  readMessageIds,
  currentUserId,
  onOpenThread,
  onOpenExecution,
  onToggleSaved,
  onToggleReaction,
}: {
  inboxItems: FeedItem[];
  savedItems: FeedItem[];
  savedMessageIds: Set<string>;
  readMessageIds: Set<string>;
  currentUserId?: string | null;
  onOpenThread: (item: FeedItem) => void;
  onOpenExecution?: (sessionId: string) => void;
  onToggleSaved: (messageId: string) => void;
  onToggleReaction?: (item: FeedItem, emoji: string) => void;
}) {
  const { t } = useT("translation");
  const [filter, setFilter] = React.useState<"all" | "unread" | "saved">("all");
  const unreadItems = React.useMemo(
    () =>
      inboxItems.filter(
        (item) =>
          !readMessageIds.has(item.message.id) &&
          (item.message.messageType !== "user" ||
            item.message.authorUserId !== currentUserId),
      ),
    [currentUserId, inboxItems, readMessageIds],
  );
  const items =
    filter === "saved"
      ? savedItems
      : filter === "unread"
        ? unreadItems
        : inboxItems;

  const filters = [
    ["all", Inbox, t("conversationView.all"), inboxItems.length],
    ["unread", MailOpen, t("conversationView.unread"), unreadItems.length],
    ["saved", Bookmark, t("conversationView.saved"), savedItems.length],
  ] as const;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background">
      <div className="border-b border-border px-6 py-4">
        <div className="flex gap-2">
          {filters.map(([value, Icon, label, count]) => {
            const isActive = filter === value;
            return (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium text-foreground transition-colors",
                  isActive
                    ? "border-primary/40 bg-primary/15"
                    : "border-border bg-card hover:bg-muted/20",
                )}
              >
                <Icon className="size-4" />
                <span>{label}</span>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto bg-background">
        {items.length > 0 ? (
          items.map((item) => (
            <MessageRow
              key={item.message.id}
              message={item.message}
              channelLabel={item.channel.name}
              isSaved={savedMessageIds.has(item.message.id)}
              compact
              onOpenThread={() => onOpenThread(item)}
              onOpenExecution={onOpenExecution}
              onToggleSaved={() => onToggleSaved(item.message.id)}
              onToggleReaction={(emoji) => onToggleReaction?.(item, emoji)}
            />
          ))
        ) : (
          <div className="flex h-full items-center justify-center px-8 text-center">
            <p className="text-lg text-muted-foreground">
              {filter === "saved"
                ? t("conversationView.noSaved")
                : t("conversationView.noInbox")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
