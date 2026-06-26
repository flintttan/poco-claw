"use client";

import { useState } from "react";
import { Copy, Link2, RefreshCw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useT } from "@/lib/i18n/client";
import { useImBindings } from "@/features/settings/hooks/use-im-bindings";
import type { ImBindingProvider } from "@/features/settings/api/im-bindings-api";

/**
 * Centralised default strings for the Settings Connected Accounts
 * tab. These double as the i18n `t()` fallbacks, so a missing
 * translation falls back to a known-good English string. The keys
 * mirror the `settings.connections` block in the per-locale
 * translation.json files under `frontend/lib/i18n/locales/`;
 * keep them in sync when adding new copy.
 */
const FALLBACK_STRINGS = {
  title: "Connected Accounts",
  subtitle:
    "Link your Poco account with IM (Feishu, DingTalk, Telegram) so the bot knows who is chatting with it.",
  linkNew: "Link a new IM account",
  provider: "Provider",
  generating: "Generating…",
  generateCode: "Generate binding code",
  copied: "Copied to clipboard.",
  codeExpires: "Expires at",
  linkedAccounts: "Linked accounts",
  empty: "No IM accounts linked yet. Generate a code above to link one.",
  boundAt: "linked",
  unbind: "Unbind",
  copy: "Copy",
  refresh: "Refresh",
  providerAny: "Any",
  providerFeishu: "Feishu",
  providerDingtalk: "DingTalk",
  providerTelegram: "Telegram",
  codeInstructionsAny:
    "Open any IM chat with the Poco bot and send: /bind <code>",
  codeInstructionsFeishu:
    "In your Feishu chat with the bot, send: /bind <code>",
  codeInstructionsDingtalk:
    "In your DingTalk chat with the bot, send: /bind <code>",
  codeInstructionsTelegram:
    "In your Telegram chat with the bot, send: /bind <code>",
} as const;

function getProviderLabel(
  provider: ImBindingProvider | "any",
  t: (key: string, fallback: string) => string,
): string {
  if (provider === "any") {
    return t(
      "settings.connections.providers.any",
      FALLBACK_STRINGS.providerAny,
    );
  }
  if (provider === "feishu") {
    return t(
      "settings.connections.providers.feishu",
      FALLBACK_STRINGS.providerFeishu,
    );
  }
  if (provider === "dingtalk") {
    return t(
      "settings.connections.providers.dingtalk",
      FALLBACK_STRINGS.providerDingtalk,
    );
  }
  return t(
    "settings.connections.providers.telegram",
    FALLBACK_STRINGS.providerTelegram,
  );
}

function getBindInstruction(
  provider: string | null,
  t: (key: string, fallback: string) => string,
): string {
  if (provider === "feishu") {
    return t(
      "settings.connections.codeInstructionsByProvider.feishu",
      FALLBACK_STRINGS.codeInstructionsFeishu,
    );
  }
  if (provider === "dingtalk") {
    return t(
      "settings.connections.codeInstructionsByProvider.dingtalk",
      FALLBACK_STRINGS.codeInstructionsDingtalk,
    );
  }
  if (provider === "telegram") {
    return t(
      "settings.connections.codeInstructionsByProvider.telegram",
      FALLBACK_STRINGS.codeInstructionsTelegram,
    );
  }
  return t(
    "settings.connections.codeInstructionsByProvider.any",
    FALLBACK_STRINGS.codeInstructionsAny,
  );
}

export function ConnectionsSettingsTab() {
  const { t } = useT("translation");
  const { bindings, isLoading, error, refresh, generateCode, remove } =
    useImBindings();
  const [activeCode, setActiveCode] = useState<{
    code: string;
    provider: string | null;
    expiresAt: string;
  } | null>(null);
  const [generating, setGenerating] = useState(false);
  const [provider, setProvider] = useState<ImBindingProvider | "any">("any");
  const [copied, setCopied] = useState(false);
  const providers: { id: ImBindingProvider | "any"; label: string }[] = [
    { id: "any", label: getProviderLabel("any", t) },
    { id: "feishu", label: getProviderLabel("feishu", t) },
    { id: "dingtalk", label: getProviderLabel("dingtalk", t) },
    { id: "telegram", label: getProviderLabel("telegram", t) },
  ];

  const onGenerate = async () => {
    setGenerating(true);
    const result = await generateCode(provider === "any" ? null : provider);
    setGenerating(false);
    if (result) {
      setActiveCode({
        code: result.code,
        provider: result.provider,
        expiresAt: result.expires_at,
      });
      setCopied(false);
    }
  };

  const onCopy = async () => {
    if (!activeCode) return;
    try {
      await navigator.clipboard.writeText(activeCode.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard may be unavailable in non-secure contexts — show the
      // code in the UI so the user can copy it manually.
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-5">
      <div className="mb-6">
        <h2 className="text-base font-medium">
          {t("settings.connections.title", FALLBACK_STRINGS.title)}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("settings.connections.subtitle", FALLBACK_STRINGS.subtitle)}
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-sm">
            {t("settings.connections.linkNew", FALLBACK_STRINGS.linkNew)}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {t("settings.connections.provider", FALLBACK_STRINGS.provider)}
            </span>
            <div className="flex gap-1 rounded-md border border-border bg-muted/30 p-0.5">
              {providers.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`rounded px-3 py-1 text-xs transition-colors ${
                    provider === p.id
                      ? "bg-background text-foreground shadow"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => setProvider(p.id)}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <Button
              size="sm"
              onClick={onGenerate}
              disabled={generating}
              className="ml-auto"
            >
              <Link2 className="mr-2 size-4" />
              {generating
                ? t(
                    "settings.connections.generating",
                    FALLBACK_STRINGS.generating,
                  )
                : t(
                    "settings.connections.generateCode",
                    FALLBACK_STRINGS.generateCode,
                  )}
            </Button>
          </div>

          {activeCode ? (
            <div className="rounded-md border border-dashed border-primary/40 bg-primary/5 p-4">
              <div className="flex items-center gap-3">
                <code className="rounded bg-background px-3 py-2 font-mono text-lg tracking-widest">
                  {activeCode.code}
                </code>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={onCopy}
                  title={t("settings.connections.copy", FALLBACK_STRINGS.copy)}
                >
                  <Copy className="size-4" />
                </Button>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                {copied
                  ? t("settings.connections.copied", FALLBACK_STRINGS.copied)
                  : getBindInstruction(activeCode.provider, t)}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t(
                  "settings.connections.codeExpires",
                  FALLBACK_STRINGS.codeExpires,
                )}{" "}
                {new Date(activeCode.expiresAt).toLocaleTimeString()}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm">
            {t(
              "settings.connections.linkedAccounts",
              FALLBACK_STRINGS.linkedAccounts,
            )}
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void refresh()}
            title={t("settings.connections.refresh", FALLBACK_STRINGS.refresh)}
          >
            <RefreshCw className="size-4" />
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-12 animate-pulse rounded bg-muted" />
              <div className="h-12 animate-pulse rounded bg-muted" />
            </div>
          ) : error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : bindings.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("settings.connections.empty", FALLBACK_STRINGS.empty)}
            </p>
          ) : (
            <ul className="space-y-2">
              {bindings.map((b) => (
                <li
                  key={b.id}
                  className="flex items-center justify-between rounded-md border border-border bg-card p-3"
                >
                  <div className="min-w-0">
                    <div className="font-medium">
                      {b.im_display_name || b.im_user_id}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {b.provider}
                      {" · "}
                      {t(
                        "settings.connections.boundAt",
                        FALLBACK_STRINGS.boundAt,
                      )}{" "}
                      {new Date(b.bound_at).toLocaleString()}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    title={t(
                      "settings.connections.unbind",
                      FALLBACK_STRINGS.unbind,
                    )}
                    onClick={() => void remove(b.id)}
                  >
                    <Trash2 className="size-4 text-destructive" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
