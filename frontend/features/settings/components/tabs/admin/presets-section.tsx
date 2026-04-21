import * as React from "react";

import { Button } from "@/components/ui/button";
import { PresetFormDialog } from "@/features/capabilities/presets/components/preset-form-dialog";
import type {
  Preset,
  PresetCapabilityItem,
  PresetCreateInput,
  PresetUpdateInput,
} from "@/features/capabilities/presets/lib/preset-types";
import type {
  AdminMcpServer,
  AdminPlugin,
} from "@/features/settings/api/admin-api";
import type { PresetVisualOption } from "@/features/capabilities/presets/lib/preset-types";
import type { Skill } from "@/features/capabilities/skills/types";
import { useT } from "@/lib/i18n/client";

import {
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  SectionCard,
} from "./shared";

interface AdminPresetsSectionProps {
  presets: Preset[];
  skills: Skill[];
  mcpServers: AdminMcpServer[];
  plugins: AdminPlugin[];
  presetVisuals: PresetVisualOption[];
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRetry: () => void;
  onCreate: (input: PresetCreateInput) => Promise<void>;
  onUpdate: (presetId: number, input: PresetUpdateInput) => Promise<void>;
  onDelete: (presetId: number) => Promise<void>;
}

function summarizePreset(preset: Preset): string {
  return [
    preset.description,
    preset.prompt_template,
    `skills:${preset.skill_ids.length}`,
    `mcp:${preset.mcp_server_ids.length}`,
    `plugins:${preset.plugin_ids.length}`,
    `subagents:${preset.subagent_configs.length}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

export function AdminPresetsSection({
  presets,
  skills,
  mcpServers,
  plugins,
  presetVisuals,
  isLoading,
  hasError,
  isSaving,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminPresetsSectionProps) {
  const { t } = useT("translation");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingPreset, setEditingPreset] = React.useState<Preset | null>(null);

  const capabilityItemsOverride = React.useMemo<{
    skills: PresetCapabilityItem[];
    mcp: PresetCapabilityItem[];
    plugins: PresetCapabilityItem[];
  }>(
    () => ({
      skills: skills
        .filter((item) => item.scope === "system")
        .map((item) => ({
          id: item.id,
          name: item.name,
          description: item.description,
          scope: item.scope,
        })),
      mcp: mcpServers
        .filter((item) => item.scope === "system")
        .map((item) => ({
          id: item.id,
          name: item.name,
          description: item.description,
          scope: item.scope,
        })),
      plugins: plugins
        .filter((item) => item.scope === "system")
        .map((item) => ({
          id: item.id,
          name: item.name,
          description: item.description,
          scope: item.scope,
        })),
    }),
    [mcpServers, plugins, skills],
  );

  const handleCreate = React.useCallback(
    async (input: PresetCreateInput) => {
      await onCreate(input);
      setDialogOpen(false);
      setEditingPreset(null);
    },
    [onCreate],
  );

  const handleUpdate = React.useCallback(
    async (presetId: number, input: PresetUpdateInput) => {
      await onUpdate(presetId, input);
      setDialogOpen(false);
      setEditingPreset(null);
    },
    [onUpdate],
  );

  const handleDelete = React.useCallback(
    async (presetId: number) => {
      await onDelete(presetId);
      setDialogOpen(false);
      setEditingPreset(null);
    },
    [onDelete],
  );

  return (
    <>
      <SectionCard
        title={t("settings.admin.presetsTitle")}
        description={t("settings.admin.presetsDescription")}
        actions={
          <Button
            size="sm"
            onClick={() => {
              setEditingPreset(null);
              setDialogOpen(true);
            }}
            disabled={isSaving}
          >
            {t("settings.admin.create")}
          </Button>
        }
      >
        {isLoading ? <AdminSectionLoading /> : null}
        {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
        <div
          className={
            isLoading || hasError ? "pointer-events-none opacity-60" : undefined
          }
        >
          <div className="space-y-2">
            {presets.map((item) => (
              <ListItem
                key={item.preset_id}
                title={item.name}
                description={summarizePreset(item)}
                danger={
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditingPreset(item);
                      setDialogOpen(true);
                    }}
                    disabled={isSaving}
                  >
                    {t("settings.admin.edit")}
                  </Button>
                }
              />
            ))}
          </div>
        </div>
      </SectionCard>

      <PresetFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={editingPreset ? "edit" : "create"}
        initialPreset={editingPreset}
        capabilityItemsOverride={capabilityItemsOverride}
        visualOptionsOverride={presetVisuals}
        savingKey={
          isSaving
            ? editingPreset
              ? String(editingPreset.preset_id)
              : "create"
            : null
        }
        onCreate={handleCreate}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
      />
    </>
  );
}
