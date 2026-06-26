"use client";

/**
 * "Linked IM chats" panel for the server detail page.
 *
 * Surfaces the IM chats that are currently bound to the server so
 * members can see which external chats will deliver their messages
 * to Poco. Fetches from ``GET /api/v1/servers/{serverId}/im-channels``
 * via the server IM channels API client. Server admins/owners can
 * also pause delivery or remove the binding from the web UI.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2,
  MessageCircle,
  MessageSquare,
  Pause,
  Play,
  RefreshCw,
  Unlink2,
} from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useT } from "@/lib/i18n/client";
import {
  listServerImChannels,
  type ServerImChannel,
  unbindServerImChannel,
  updateServerImChannel,
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
  refresh: "Refresh",
  enabled: "active",
  disabled: "paused",
  group: "group",
  p2p: "1:1",
  manageHint:
    "Admins can pause delivery to a chat or remove the server binding entirely.",
  emptyHint:
    "Link an IM chat from the chat itself with /server <server_id> after a server admin joins it.",
  boundAt: "bound",
  boundBy: "bound by",
  providerFeishu: "Feishu",
  providerDingtalk: "DingTalk",
  providerTelegram: "Telegram",
  pause: "Pause",
  resume: "Resume",
  unbind: "Unbind",
  pauseSuccess: "IM chat paused.",
  resumeSuccess: "IM chat resumed.",
  unbindSuccess: "IM chat unbound from the server.",
  unbindTitle: "Remove linked IM chat?",
  unbindDescription:
    "This removes the server binding for the selected IM chat. Members in that chat will stop using this server until it is linked again from IM.",
  confirmUnbind: "Remove binding",
  actionError: "Failed to update linked IM chat.",
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
  canManage?: boolean;
}

export function ServerImChannelsPanel({
  serverId,
  canManage = false,
}: ServerImChannelsPanelProps) {
  const { t } = useT("translation");
  const [channels, setChannels] = useState<ServerImChannel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingChannelId, setPendingChannelId] = useState<number | null>(null);
  const [unbindTarget, setUnbindTarget] = useState<ServerImChannel | null>(
    null,
  );

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

  const isMutating = useCallback(
    (channelId: number) => pendingChannelId === channelId,
    [pendingChannelId],
  );

  const updateLocalChannel = useCallback((next: ServerImChannel) => {
    setChannels((current) =>
      current.map((channel) => (channel.id === next.id ? next : channel)),
    );
  }, []);

  const onToggleEnabled = useCallback(
    async (channel: ServerImChannel) => {
      setPendingChannelId(channel.id);
      try {
        const next = await updateServerImChannel(
          serverId,
          channel.id,
          !channel.enabled,
        );
        updateLocalChannel(next);
        toast.success(
          channel.enabled
            ? t("server.imChannels.pauseSuccess", FALLBACK_STRINGS.pauseSuccess)
            : t(
                "server.imChannels.resumeSuccess",
                FALLBACK_STRINGS.resumeSuccess,
              ),
        );
      } catch (err) {
        toast.error(
          err instanceof Error
            ? err.message
            : t("server.imChannels.actionError", FALLBACK_STRINGS.actionError),
        );
      } finally {
        setPendingChannelId(null);
      }
    },
    [serverId, t, updateLocalChannel],
  );

  const onConfirmUnbind = useCallback(async () => {
    if (!unbindTarget) {
      return;
    }
    setPendingChannelId(unbindTarget.id);
    try {
      await unbindServerImChannel(serverId, unbindTarget.id);
      setChannels((current) =>
        current.filter((channel) => channel.id !== unbindTarget.id),
      );
      toast.success(
        t("server.imChannels.unbindSuccess", FALLBACK_STRINGS.unbindSuccess),
      );
      setUnbindTarget(null);
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : t("server.imChannels.actionError", FALLBACK_STRINGS.actionError),
      );
    } finally {
      setPendingChannelId(null);
    }
  }, [serverId, t, unbindTarget]);

  const showManagementHint = useMemo(() => canManage, [canManage]);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm">
              {t("server.imChannels.title", FALLBACK_STRINGS.title)}
            </CardTitle>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-8"
              onClick={() => void load()}
              disabled={isLoading || pendingChannelId !== null}
              title={t("server.imChannels.refresh", FALLBACK_STRINGS.refresh)}
              aria-label={t(
                "server.imChannels.refresh",
                FALLBACK_STRINGS.refresh,
              )}
            >
              <RefreshCw
                className={`size-4 ${isLoading ? "animate-spin" : ""}`}
              />
            </Button>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {t("server.imChannels.subtitle", FALLBACK_STRINGS.subtitle)}
          </p>
          {showManagementHint ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {t("server.imChannels.manageHint", FALLBACK_STRINGS.manageHint)}
            </p>
          ) : null}
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
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">
                {t("server.imChannels.empty", FALLBACK_STRINGS.empty)}
              </p>
              {canManage ? (
                <p className="text-xs text-muted-foreground">
                  {t("server.imChannels.emptyHint", FALLBACK_STRINGS.emptyHint)}
                </p>
              ) : null}
            </div>
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
                      {channel.last_bound_by_user_id ? (
                        <div className="text-xs text-muted-foreground">
                          {t(
                            "server.imChannels.boundBy",
                            FALLBACK_STRINGS.boundBy,
                          )}{" "}
                          {channel.last_bound_by_user?.display_name ||
                            channel.last_bound_by_user_id}
                        </div>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right text-xs text-muted-foreground">
                      <div
                        className={
                          channel.enabled
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-amber-600 dark:text-amber-400"
                        }
                      >
                        {channel.enabled
                          ? t(
                              "server.imChannels.enabled",
                              FALLBACK_STRINGS.enabled,
                            )
                          : t(
                              "server.imChannels.disabled",
                              FALLBACK_STRINGS.disabled,
                            )}
                      </div>
                      {channel.last_bound_at ? (
                        <div>
                          {t(
                            "server.imChannels.boundAt",
                            FALLBACK_STRINGS.boundAt,
                          )}{" "}
                          {formatTimestamp(channel.last_bound_at)}
                        </div>
                      ) : null}
                    </div>
                    {canManage ? (
                      <div className="flex shrink-0 items-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          disabled={isMutating(channel.id)}
                          onClick={() => void onToggleEnabled(channel)}
                          aria-label={
                            channel.enabled
                              ? t(
                                  "server.imChannels.pause",
                                  FALLBACK_STRINGS.pause,
                                )
                              : t(
                                  "server.imChannels.resume",
                                  FALLBACK_STRINGS.resume,
                                )
                          }
                        >
                          {isMutating(channel.id) ? (
                            <Loader2 className="mr-2 size-4 animate-spin" />
                          ) : channel.enabled ? (
                            <Pause className="mr-2 size-4" />
                          ) : (
                            <Play className="mr-2 size-4" />
                          )}
                          {channel.enabled
                            ? t(
                                "server.imChannels.pause",
                                FALLBACK_STRINGS.pause,
                              )
                            : t(
                                "server.imChannels.resume",
                                FALLBACK_STRINGS.resume,
                              )}
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={isMutating(channel.id)}
                          onClick={() => setUnbindTarget(channel)}
                          aria-label={t(
                            "server.imChannels.unbind",
                            FALLBACK_STRINGS.unbind,
                          )}
                        >
                          <Unlink2 className="mr-2 size-4" />
                          {t(
                            "server.imChannels.unbind",
                            FALLBACK_STRINGS.unbind,
                          )}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <AlertDialog
        open={unbindTarget !== null}
        onOpenChange={(open) => {
          if (!open && pendingChannelId === null) {
            setUnbindTarget(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("server.imChannels.unbindTitle", FALLBACK_STRINGS.unbindTitle)}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t(
                "server.imChannels.unbindDescription",
                FALLBACK_STRINGS.unbindDescription,
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={pendingChannelId !== null}>
              {t("common.cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={pendingChannelId !== null}
              onClick={(event) => {
                event.preventDefault();
                void onConfirmUnbind();
              }}
            >
              {pendingChannelId !== null ? (
                <Loader2 className="mr-2 size-4 animate-spin" />
              ) : null}
              {t(
                "server.imChannels.confirmUnbind",
                FALLBACK_STRINGS.confirmUnbind,
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
