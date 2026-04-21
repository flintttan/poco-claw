import * as React from "react";
import { Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type {
  SubAgent,
  SubAgentCreateInput,
  SubAgentMode,
  SubAgentUpdateInput,
} from "@/features/capabilities/sub-agents/types";
import { useT } from "@/lib/i18n/client";

import {
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  SectionCard,
} from "./shared";

interface SubAgentEditState {
  name: string;
  enabled: boolean;
  mode: SubAgentMode;
  description: string;
  prompt: string;
  tools: string;
  rawMarkdown: string;
}

interface AdminSubAgentsSectionProps {
  subAgents: SubAgent[];
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRetry: () => void;
  onCreate: (input: SubAgentCreateInput) => Promise<void>;
  onUpdate: (subAgentId: number, input: SubAgentUpdateInput) => Promise<void>;
  onDelete: (subAgentId: number) => Promise<void>;
}

function summarize(agent: SubAgent, t: (key: string) => string): string {
  if (agent.mode === "raw") {
    return agent.raw_markdown || t("settings.admin.valueEmpty");
  }
  return [agent.description, agent.prompt, agent.tools?.join(", ")]
    .filter(Boolean)
    .join(" · ");
}

export function AdminSubAgentsSection({
  subAgents,
  isLoading,
  hasError,
  isSaving,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminSubAgentsSectionProps) {
  const { t } = useT("translation");
  const [editingId, setEditingId] = React.useState<number | null>(null);
  const [editState, setEditState] = React.useState<SubAgentEditState | null>(
    null,
  );

  const [name, setName] = React.useState("");
  const [enabled, setEnabled] = React.useState(true);
  const [mode, setMode] = React.useState<SubAgentMode>("structured");
  const [description, setDescription] = React.useState("");
  const [prompt, setPrompt] = React.useState("");
  const [tools, setTools] = React.useState("");
  const [rawMarkdown, setRawMarkdown] = React.useState("");

  const resetCreateState = React.useCallback(() => {
    setName("");
    setEnabled(true);
    setMode("structured");
    setDescription("");
    setPrompt("");
    setTools("");
    setRawMarkdown("");
  }, []);

  const resetEditState = React.useCallback(() => {
    setEditingId(null);
    setEditState(null);
  }, []);

  const parseTools = React.useCallback(
    (value: string): string[] | undefined => {
      const result = value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      return result.length > 0 ? result : undefined;
    },
    [],
  );

  return (
    <SectionCard
      title={t("settings.admin.subAgentsTitle")}
      description={t("settings.admin.subAgentsDescription")}
    >
      {isLoading ? <AdminSectionLoading /> : null}
      {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
      <div
        className={
          isLoading || hasError ? "pointer-events-none opacity-60" : undefined
        }
      >
        <div className="grid gap-3 md:grid-cols-2">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("library.subAgents.fields.namePlaceholder")}
          />
          <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
            <Switch checked={enabled} onCheckedChange={setEnabled} />
            <span className="text-sm text-muted-foreground">
              {enabled ? t("common.enabled") : t("common.disabled")}
            </span>
          </div>
          <div className="grid gap-3 md:col-span-2 md:grid-cols-3">
            <Button
              type="button"
              variant={mode === "structured" ? "default" : "outline"}
              onClick={() => setMode("structured")}
              disabled={isSaving}
            >
              {t("library.subAgents.mode.structured")}
            </Button>
            <Button
              type="button"
              variant={mode === "raw" ? "default" : "outline"}
              onClick={() => setMode("raw")}
              disabled={isSaving}
            >
              {t("library.subAgents.mode.raw")}
            </Button>
            <Button
              disabled={isSaving}
              onClick={() =>
                void (async () => {
                  if (!name.trim()) {
                    throw new Error(
                      t("library.subAgents.fields.namePlaceholder"),
                    );
                  }
                  await onCreate({
                    name: name.trim(),
                    enabled,
                    mode,
                    description: description || undefined,
                    prompt: mode === "structured" ? prompt : undefined,
                    tools:
                      mode === "structured" ? parseTools(tools) : undefined,
                    raw_markdown: mode === "raw" ? rawMarkdown : undefined,
                  });
                  resetCreateState();
                })()
              }
            >
              {t("settings.admin.create")}
            </Button>
          </div>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("library.subAgents.fields.descriptionPlaceholder")}
          />
          {mode === "structured" ? (
            <>
              <Input
                value={tools}
                onChange={(e) => setTools(e.target.value)}
                placeholder={t("library.subAgents.fields.toolsPlaceholder")}
              />
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="min-h-28 md:col-span-2"
                placeholder={t("library.subAgents.fields.promptPlaceholder")}
              />
            </>
          ) : (
            <Textarea
              value={rawMarkdown}
              onChange={(e) => setRawMarkdown(e.target.value)}
              className="min-h-28 md:col-span-2"
              placeholder={t("library.subAgents.fields.rawMarkdownPlaceholder")}
            />
          )}
        </div>

        <div className="space-y-2">
          {subAgents.map((item) => (
            <ListItem
              key={item.id}
              title={item.name}
              description={summarize(item, t)}
              badge={
                <>
                  <Badge variant="outline">
                    {item.mode === "structured"
                      ? t("library.subAgents.mode.structured")
                      : t("library.subAgents.mode.raw")}
                  </Badge>
                  <Badge variant={item.enabled ? "secondary" : "outline"}>
                    {item.enabled ? t("common.enabled") : t("common.disabled")}
                  </Badge>
                </>
              }
              danger={
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditingId(item.id);
                      setEditState({
                        name: item.name,
                        enabled: item.enabled,
                        mode: item.mode,
                        description: item.description ?? "",
                        prompt: item.prompt ?? "",
                        tools: item.tools?.join(", ") ?? "",
                        rawMarkdown: item.raw_markdown ?? "",
                      });
                    }}
                    disabled={isSaving}
                  >
                    {t("settings.admin.edit")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => void onDelete(item.id)}
                    disabled={isSaving}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </>
              }
            >
              {editingId === item.id && editState ? (
                <div className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-2">
                    <Input
                      value={editState.name}
                      onChange={(e) =>
                        setEditState((current) =>
                          current
                            ? { ...current, name: e.target.value }
                            : current,
                        )
                      }
                    />
                    <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                      <Switch
                        checked={editState.enabled}
                        onCheckedChange={(checked) =>
                          setEditState((current) =>
                            current
                              ? { ...current, enabled: checked }
                              : current,
                          )
                        }
                      />
                      <span className="text-sm text-muted-foreground">
                        {editState.enabled
                          ? t("common.enabled")
                          : t("common.disabled")}
                      </span>
                    </div>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <Button
                      type="button"
                      variant={
                        editState.mode === "structured" ? "default" : "outline"
                      }
                      onClick={() =>
                        setEditState((current) =>
                          current
                            ? { ...current, mode: "structured" }
                            : current,
                        )
                      }
                    >
                      {t("library.subAgents.mode.structured")}
                    </Button>
                    <Button
                      type="button"
                      variant={editState.mode === "raw" ? "default" : "outline"}
                      onClick={() =>
                        setEditState((current) =>
                          current ? { ...current, mode: "raw" } : current,
                        )
                      }
                    >
                      {t("library.subAgents.mode.raw")}
                    </Button>
                  </div>
                  <Input
                    value={editState.description}
                    onChange={(e) =>
                      setEditState((current) =>
                        current
                          ? { ...current, description: e.target.value }
                          : current,
                      )
                    }
                    placeholder={t(
                      "library.subAgents.fields.descriptionPlaceholder",
                    )}
                  />
                  {editState.mode === "structured" ? (
                    <>
                      <Input
                        value={editState.tools}
                        onChange={(e) =>
                          setEditState((current) =>
                            current
                              ? { ...current, tools: e.target.value }
                              : current,
                          )
                        }
                        placeholder={t(
                          "library.subAgents.fields.toolsPlaceholder",
                        )}
                      />
                      <Textarea
                        value={editState.prompt}
                        onChange={(e) =>
                          setEditState((current) =>
                            current
                              ? { ...current, prompt: e.target.value }
                              : current,
                          )
                        }
                        className="min-h-28"
                        placeholder={t(
                          "library.subAgents.fields.promptPlaceholder",
                        )}
                      />
                    </>
                  ) : (
                    <Textarea
                      value={editState.rawMarkdown}
                      onChange={(e) =>
                        setEditState((current) =>
                          current
                            ? { ...current, rawMarkdown: e.target.value }
                            : current,
                        )
                      }
                      className="min-h-28"
                      placeholder={t(
                        "library.subAgents.fields.rawMarkdownPlaceholder",
                      )}
                    />
                  )}
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={resetEditState}
                      disabled={isSaving}
                    >
                      {t("settings.admin.cancel")}
                    </Button>
                    <Button
                      onClick={() =>
                        void (async () => {
                          await onUpdate(item.id, {
                            name: editState.name,
                            enabled: editState.enabled,
                            mode: editState.mode,
                            description: editState.description || undefined,
                            prompt:
                              editState.mode === "structured"
                                ? editState.prompt
                                : undefined,
                            tools:
                              editState.mode === "structured"
                                ? parseTools(editState.tools)
                                : undefined,
                            raw_markdown:
                              editState.mode === "raw"
                                ? editState.rawMarkdown
                                : undefined,
                          });
                          resetEditState();
                        })()
                      }
                      disabled={isSaving}
                    >
                      {t("settings.admin.update")}
                    </Button>
                  </div>
                </div>
              ) : null}
            </ListItem>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
