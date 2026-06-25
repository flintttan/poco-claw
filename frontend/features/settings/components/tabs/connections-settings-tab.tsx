"use client";

import { useState } from "react";
import { Copy, Link2, RefreshCw, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useT } from "@/lib/i18n/client";
import { useImBindings } from "@/features/settings/hooks/use-im-bindings";
import type { ImBindingProvider } from "@/features/settings/api/im-bindings-api";

const PROVIDERS: { id: ImBindingProvider | "any"; label: string }[] = [
  { id: "any", label: "Any" },
  { id: "feishu", label: "Feishu" },
  { id: "dingtalk", label: "DingTalk" },
  { id: "telegram", label: "Telegram" },
];

const BIND_INSTRUCTIONS: Record<string, string> = {
  feishu: "In your Feishu chat with the bot, send: /bind <code>",
  dingtalk: "In your DingTalk chat with the bot, send: /bind <code>",
  telegram: "In your Telegram chat with the bot, send: /bind <code>",
  any: "Open any IM chat with the Poco bot and send: /bind <code>",
};

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
          {t("settings.connections.title", "Connected Accounts")}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {t(
            "settings.connections.subtitle",
            "Link your Poco account with IM (Feishu, DingTalk, Telegram) so the bot knows who is chatting with it.",
          )}
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-sm">
            {t("settings.connections.linkNew", "Link a new IM account")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {t("settings.connections.provider", "Provider")}
            </span>
            <div className="flex gap-1 rounded-md border border-border bg-muted/30 p-0.5">
              {PROVIDERS.map((p) => (
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
                ? t("settings.connections.generating", "Generating…")
                : t(
                    "settings.connections.generateCode",
                    "Generate binding code",
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
                  title="Copy"
                >
                  <Copy className="size-4" />
                </Button>
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                {copied
                  ? t("settings.connections.copied", "Copied to clipboard.")
                  : t(
                      "settings.connections.codeInstructions",
                      BIND_INSTRUCTIONS[activeCode.provider ?? "any"] ??
                        BIND_INSTRUCTIONS.any,
                    )}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t("settings.connections.codeExpires", "Expires at")}{" "}
                {new Date(activeCode.expiresAt).toLocaleTimeString()}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm">
            {t("settings.connections.linkedAccounts", "Linked accounts")}
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void refresh()}
            title="Refresh"
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
              {t(
                "settings.connections.empty",
                "No IM accounts linked yet. Generate a code above to link one.",
              )}
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
                      {t("settings.connections.boundAt", "linked")}{" "}
                      {new Date(b.bound_at).toLocaleString()}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    title={t("settings.connections.unbind", "Unbind")}
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
