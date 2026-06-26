"use client";

/**
 * "Linked IM chats" panel for the server detail page.
 *
 * Surfaces the IM chats that are currently bound to the server so
 * members can see which external chats will deliver their messages
 * to Poco. Fetches from ``GET /api/v1/servers/{serverId}/im-channels``
 * via the :func:`listServerImChannels` API client. The component is
 * intentionally read-only — bindings are created and removed by the
 * ``/server <id>`` and ``/server-off`` commands inside the IM chat
 * itself, not from the web UI.
 */

import { useCallback, useEffect, useState } from "react";
import { Loader2, MessageCircle, MessageSquare } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useT } from "@/lib/i18n/client";
import {
  listServerImChannels,
  type ServerImChannel,
} from "@/features/servers/api/server-im-channels-api";

/**
 * Default strings for the panel. The i18n ``t()`` calls below use
 * these as fallbacks so a missing translation does not blank the
 * section. The keys mirror the ``server.imChannels`` block in
 * the per-locale translation.json files; keep them in sync when
 * adding copy.
 */
const FALLBACK_STRINGS = {
  title: "Linked IM chats",
  subtitle:
    "IM chats currently bound to this server. Messages sent in these chats will reach Poco on behalf of the bound members.",
  empty: "No IM chats are bound to this server yet.",
  loading: "Loading…",
  loadError: "Failed to load bound IM chats.",
  retry: "Retry",
  enabled: "active",
  disabled: "paused",
  group: "group",
  p2p: "1:1",
  boundAt: "bound",
  providerFeishu: "Feishu",
  providerDingtalk: "DingTalk",
  providerTelegram: "Telegram",
} as const;

function formatChatType(
  chatType: string,
  t: (k: string, f: string) => string,
): string {
  if (chatType === "p2p")
    return t("server.imChannels.p2p", FALLBACK_STRINGS.p2p);
  if (chatType === "group")
    return t("server.imChannels.group", FALLBACK_STRINGS.group);
  return chatType;
}

function formatProvider(
  provider: string,
  t: (k: string, f: string) => string,
): string {
  if (provider === "feishu") {
    return t(
      "server.imChannels.providers.feishu",
      FALLBACK_STRINGS.providerFeishu,
    );
  }
  if (provider === "dingtalk") {
    return t(
      "server.imChannels.providers.dingtalk",
      FALLBACK_STRINGS.providerDingtalk,
    );
  }
  if (provider === "telegram") {
    return t(
      "server.imChannels.providers.telegram",
      FALLBACK_STRINGS.providerTelegram,
    );
  }
  return provider;
}

function formatTimestamp(value: string | null): string {
  if (!value) return "";
  // ``last_bound_at`` is an ISO string from the backend; format in
  // the user's locale for the panel. The empty-string branch keeps
  // the row compact when the audit field is null.
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export interface ServerImChannelsPanelProps {
  serverId: string;
}

export function ServerImChannelsPanel({
  serverId,
}: ServerImChannelsPanelProps) {
  const { t } = useT("translation");
  const [channels, setChannels] = useState<ServerImChannel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const rows = await listServerImChannels(serverId);
      setChannels(rows);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("server.imChannels.loadError", FALLBACK_STRINGS.loadError),
      );
    } finally {
      setIsLoading(false);
    }
  }, [serverId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">
          {t("server.imChannels.title", FALLBACK_STRINGS.title)}
        </CardTitle>
        <p className="mt-1 text-xs text-muted-foreground">
          {t("server.imChannels.subtitle", FALLBACK_STRINGS.subtitle)}
        </p>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            <span>
              {t("server.imChannels.loading", FALLBACK_STRINGS.loading)}
            </span>
          </div>
        ) : error ? (
          <div className="space-y-2">
            <p className="text-sm text-destructive">
              {t("server.imChannels.loadError", FALLBACK_STRINGS.loadError)}
            </p>
            <button
              type="button"
              onClick={() => void load()}
              className="text-xs text-primary underline"
            >
              {t("server.imChannels.retry", FALLBACK_STRINGS.retry)}
            </button>
          </div>
        ) : channels.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t("server.imChannels.empty", FALLBACK_STRINGS.empty)}
          </p>
        ) : (
          <ul className="space-y-2">
            {channels.map((channel) => (
              <li
                key={channel.id}
                className="flex items-center justify-between rounded-md border border-border bg-card p-3"
              >
                <div className="flex items-center gap-3">
                  {channel.chat_type === "p2p" ? (
                    <MessageCircle className="size-4 text-muted-foreground" />
                  ) : (
                    <MessageSquare className="size-4 text-muted-foreground" />
                  )}
                  <div className="min-w-0">
                    <div className="font-medium">
                      {formatProvider(channel.provider, t)}
                      <span className="ml-2 text-xs text-muted-foreground">
                        {formatChatType(channel.chat_type, t)}
                      </span>
                    </div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {channel.destination}
                    </div>
                  </div>
                </div>
                <div className="text-right text-xs text-muted-foreground">
                  <div
                    className={
                      channel.enabled
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-amber-600 dark:text-amber-400"
                    }
                  >
                    {channel.enabled
                      ? t("server.imChannels.enabled", FALLBACK_STRINGS.enabled)
                      : t(
                          "server.imChannels.disabled",
                          FALLBACK_STRINGS.disabled,
                        )}
                  </div>
                  {channel.last_bound_at ? (
                    <div>
                      {t("server.imChannels.boundAt", FALLBACK_STRINGS.boundAt)}{" "}
                      {formatTimestamp(channel.last_bound_at)}
                    </div>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
