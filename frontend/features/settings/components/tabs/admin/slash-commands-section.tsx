import * as React from "react";
import { Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type {
  SlashCommand,
  SlashCommandCreateInput,
  SlashCommandMode,
  SlashCommandUpdateInput,
} from "@/features/capabilities/slash-commands/types";
import { useT } from "@/lib/i18n/client";

import {
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  SectionCard,
} from "./shared";

interface SlashCommandEditState {
  name: string;
  enabled: boolean;
  mode: SlashCommandMode;
  description: string;
  argumentHint: string;
  allowedTools: string;
  content: string;
  rawMarkdown: string;
}

interface AdminSlashCommandsSectionProps {
  commands: SlashCommand[];
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRetry: () => void;
  onCreate: (input: SlashCommandCreateInput) => Promise<void>;
  onUpdate: (
    commandId: number,
    input: SlashCommandUpdateInput,
  ) => Promise<void>;
  onDelete: (commandId: number) => Promise<void>;
}

function buildDescription(
  command: SlashCommand,
  t: (key: string) => string,
): string {
  const parts = [`/${command.name}`];
  if (command.description) {
    parts.push(command.description);
  }
  if (command.argument_hint) {
    parts.push(command.argument_hint);
  }
  if (command.mode === "structured" && command.content) {
    parts.push(command.content);
  }
  if (command.mode === "raw" && command.raw_markdown) {
    parts.push(command.raw_markdown);
  }
  return parts.join(" · ") || t("settings.admin.valueEmpty");
}

export function AdminSlashCommandsSection({
  commands,
  isLoading,
  hasError,
  isSaving,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminSlashCommandsSectionProps) {
  const { t } = useT("translation");
  const [editingCommandId, setEditingCommandId] = React.useState<number | null>(
    null,
  );
  const [editState, setEditState] =
    React.useState<SlashCommandEditState | null>(null);

  const [newName, setNewName] = React.useState("");
  const [newEnabled, setNewEnabled] = React.useState(true);
  const [newMode, setNewMode] = React.useState<SlashCommandMode>("raw");
  const [newDescription, setNewDescription] = React.useState("");
  const [newArgumentHint, setNewArgumentHint] = React.useState("");
  const [newAllowedTools, setNewAllowedTools] = React.useState("");
  const [newContent, setNewContent] = React.useState("");
  const [newRawMarkdown, setNewRawMarkdown] = React.useState("");

  const resetEditState = React.useCallback(() => {
    setEditingCommandId(null);
    setEditState(null);
  }, []);

  const resetCreateState = React.useCallback(() => {
    setNewName("");
    setNewEnabled(true);
    setNewMode("raw");
    setNewDescription("");
    setNewArgumentHint("");
    setNewAllowedTools("");
    setNewContent("");
    setNewRawMarkdown("");
  }, []);

  return (
    <SectionCard
      title={t("settings.admin.slashCommandsTitle")}
      description={t("settings.admin.slashCommandsDescription")}
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
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("settings.admin.slashCommandNamePlaceholder")}
          />
          <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
            <Switch checked={newEnabled} onCheckedChange={setNewEnabled} />
            <span className="text-sm text-muted-foreground">
              {newEnabled ? t("common.enabled") : t("common.disabled")}
            </span>
          </div>
          <div className="grid gap-3 md:col-span-2 md:grid-cols-3">
            <Button
              type="button"
              variant={newMode === "raw" ? "default" : "outline"}
              onClick={() => setNewMode("raw")}
              disabled={isSaving}
            >
              {t("library.slashCommands.mode.raw")}
            </Button>
            <Button
              type="button"
              variant={newMode === "structured" ? "default" : "outline"}
              onClick={() => setNewMode("structured")}
              disabled={isSaving}
            >
              {t("library.slashCommands.mode.structured")}
            </Button>
            <Button
              onClick={() =>
                void (async () => {
                  if (!newName.trim()) {
                    throw new Error(
                      t("settings.admin.slashCommandNameRequired"),
                    );
                  }
                  await onCreate({
                    name: newName.trim(),
                    enabled: newEnabled,
                    mode: newMode,
                    description: newDescription || undefined,
                    argument_hint: newArgumentHint || undefined,
                    allowed_tools: newAllowedTools || undefined,
                    content: newMode === "structured" ? newContent : undefined,
                    raw_markdown:
                      newMode === "raw" ? newRawMarkdown : undefined,
                  });
                  resetCreateState();
                })()
              }
              disabled={isSaving}
            >
              {t("settings.admin.create")}
            </Button>
          </div>
          <Input
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
            placeholder={t(
              "library.slashCommands.fields.descriptionPlaceholder",
            )}
          />
          <Input
            value={newArgumentHint}
            onChange={(e) => setNewArgumentHint(e.target.value)}
            placeholder={t(
              "library.slashCommands.fields.argumentHintPlaceholder",
            )}
          />
          <Input
            value={newAllowedTools}
            onChange={(e) => setNewAllowedTools(e.target.value)}
            placeholder={t(
              "library.slashCommands.fields.allowedToolsPlaceholder",
            )}
            className="md:col-span-2"
          />
          {newMode === "structured" ? (
            <Textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              className="min-h-28 md:col-span-2"
              placeholder={t("library.slashCommands.fields.contentPlaceholder")}
            />
          ) : (
            <Textarea
              value={newRawMarkdown}
              onChange={(e) => setNewRawMarkdown(e.target.value)}
              className="min-h-28 md:col-span-2"
              placeholder={t(
                "library.slashCommands.fields.rawMarkdownPlaceholder",
              )}
            />
          )}
        </div>

        <div className="space-y-2">
          {commands.map((item) => (
            <ListItem
              key={item.id}
              title={`/${item.name}`}
              description={buildDescription(item, t)}
              badge={
                <>
                  <Badge variant="outline">
                    {item.mode === "structured"
                      ? t("library.slashCommands.mode.structured")
                      : t("library.slashCommands.mode.raw")}
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
                      setEditingCommandId(item.id);
                      setEditState({
                        name: item.name,
                        enabled: item.enabled,
                        mode: item.mode,
                        description: item.description ?? "",
                        argumentHint: item.argument_hint ?? "",
                        allowedTools: item.allowed_tools ?? "",
                        content: item.content ?? "",
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
              {editingCommandId === item.id && editState ? (
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
                      placeholder={t(
                        "settings.admin.slashCommandNamePlaceholder",
                      )}
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
                  <div className="grid gap-3 md:grid-cols-3">
                    <Button
                      type="button"
                      variant={editState.mode === "raw" ? "default" : "outline"}
                      onClick={() =>
                        setEditState((current) =>
                          current ? { ...current, mode: "raw" } : current,
                        )
                      }
                      disabled={isSaving}
                    >
                      {t("library.slashCommands.mode.raw")}
                    </Button>
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
                      disabled={isSaving}
                    >
                      {t("library.slashCommands.mode.structured")}
                    </Button>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
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
                        "library.slashCommands.fields.descriptionPlaceholder",
                      )}
                    />
                    <Input
                      value={editState.argumentHint}
                      onChange={(e) =>
                        setEditState((current) =>
                          current
                            ? { ...current, argumentHint: e.target.value }
                            : current,
                        )
                      }
                      placeholder={t(
                        "library.slashCommands.fields.argumentHintPlaceholder",
                      )}
                    />
                  </div>
                  <Input
                    value={editState.allowedTools}
                    onChange={(e) =>
                      setEditState((current) =>
                        current
                          ? { ...current, allowedTools: e.target.value }
                          : current,
                      )
                    }
                    placeholder={t(
                      "library.slashCommands.fields.allowedToolsPlaceholder",
                    )}
                  />
                  {editState.mode === "structured" ? (
                    <Textarea
                      value={editState.content}
                      onChange={(e) =>
                        setEditState((current) =>
                          current
                            ? { ...current, content: e.target.value }
                            : current,
                        )
                      }
                      className="min-h-32"
                      placeholder={t(
                        "library.slashCommands.fields.contentPlaceholder",
                      )}
                    />
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
                      className="min-h-32"
                      placeholder={t(
                        "library.slashCommands.fields.rawMarkdownPlaceholder",
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
                            argument_hint: editState.argumentHint || undefined,
                            allowed_tools: editState.allowedTools || undefined,
                            content:
                              editState.mode === "structured"
                                ? editState.content
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
