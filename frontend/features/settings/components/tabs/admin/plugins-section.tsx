import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type {
  PluginCreateInput,
  PluginUpdateInput,
} from "@/features/capabilities/plugins/types";
import type { AdminPlugin } from "@/features/settings/api/admin-api";
import { useT } from "@/lib/i18n/client";

import {
  AdminCreateActions,
  AdminCreateGrid,
  AdminEditActions,
  AdminItemActions,
  AdminLabeledInputField,
  AdminLabeledTextareaField,
  AdminMaskedUpdateHint,
  AdminPolicyHint,
  AdminPolicySwitchField,
  AdminPolicySwitchInline,
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  SectionCard,
  parseJsonObject,
  summarizeJson,
} from "./shared";

interface PluginEditState {
  name: string;
  description: string;
  version: string;
  entry: string;
  manifest: string;
  defaultEnabled: boolean;
  forceEnabled: boolean;
}

interface AdminPluginsSectionProps {
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  plugins: AdminPlugin[];
  onRetry: () => void;
  onCreate: (input: PluginCreateInput) => Promise<void>;
  onUpdate: (pluginId: number, input: PluginUpdateInput) => Promise<void>;
  onDelete: (pluginId: number) => Promise<void>;
}

export function AdminPluginsSection({
  isLoading,
  hasError,
  isSaving,
  plugins,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminPluginsSectionProps) {
  const { t } = useT("translation");
  const [newPluginName, setNewPluginName] = React.useState("");
  const [newPluginDescription, setNewPluginDescription] = React.useState("");
  const [newPluginVersion, setNewPluginVersion] = React.useState("");
  const [newPluginEntry, setNewPluginEntry] = React.useState("{}");
  const [newPluginManifest, setNewPluginManifest] = React.useState("{}");
  const [newDefaultEnabled, setNewDefaultEnabled] = React.useState(false);
  const [newForceEnabled, setNewForceEnabled] = React.useState(false);
  const [editingPluginId, setEditingPluginId] = React.useState<number | null>(
    null,
  );
  const [pluginEditState, setPluginEditState] =
    React.useState<PluginEditState | null>(null);

  const resetEditingState = React.useCallback(() => {
    setEditingPluginId(null);
    setPluginEditState(null);
  }, []);

  return (
    <SectionCard
      title={t("settings.admin.pluginsTitle")}
      description={t("settings.admin.pluginsDescription")}
    >
      {isLoading ? <AdminSectionLoading /> : null}
      {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
      <div
        className={
          isLoading || hasError ? "pointer-events-none opacity-60" : undefined
        }
      >
        <AdminPolicyHint />
        <AdminCreateGrid columns="two">
          <Input
            value={newPluginName}
            onChange={(e) => setNewPluginName(e.target.value)}
            placeholder={t("settings.admin.pluginNamePlaceholder")}
          />
          <Input
            value={newPluginDescription}
            onChange={(e) => setNewPluginDescription(e.target.value)}
            placeholder={t("settings.admin.envDescriptionPlaceholder")}
          />
          <Input
            value={newPluginVersion}
            onChange={(e) => setNewPluginVersion(e.target.value)}
            placeholder={t("settings.admin.pluginVersionPlaceholder")}
          />
          <div className="flex justify-end md:col-span-1">
            <AdminCreateActions
              isSaving={isSaving}
              onCreate={async () => {
                if (!newPluginName.trim()) {
                  throw new Error(t("settings.admin.pluginNameRequired"));
                }
                await onCreate({
                  name: newPluginName.trim(),
                  description: newPluginDescription || undefined,
                  version: newPluginVersion || undefined,
                  entry: parseJsonObject(
                    newPluginEntry,
                    t("settings.admin.invalidJsonObject"),
                  ),
                  manifest: parseJsonObject(
                    newPluginManifest,
                    t("settings.admin.invalidJsonObject"),
                  ),
                  default_enabled: newDefaultEnabled,
                  force_enabled: newForceEnabled,
                });
                setNewPluginName("");
                setNewPluginDescription("");
                setNewPluginVersion("");
                setNewPluginEntry("{}");
                setNewPluginManifest("{}");
                setNewDefaultEnabled(false);
                setNewForceEnabled(false);
              }}
            />
          </div>
        </AdminCreateGrid>
        <AdminCreateGrid columns="two">
          <Textarea
            value={newPluginEntry}
            onChange={(e) => setNewPluginEntry(e.target.value)}
            className="min-h-24"
            placeholder='{"s3_key":"..."}'
          />
          <Textarea
            value={newPluginManifest}
            onChange={(e) => setNewPluginManifest(e.target.value)}
            className="min-h-24"
            placeholder='{"name":"plugin-manifest"}'
          />
          <AdminPolicySwitchInline
            label={t("settings.admin.policyDefaultEnabled")}
            checked={newDefaultEnabled}
            onCheckedChange={setNewDefaultEnabled}
          />
          <AdminPolicySwitchInline
            label={t("settings.admin.policyForceEnabled")}
            checked={newForceEnabled}
            onCheckedChange={setNewForceEnabled}
          />
        </AdminCreateGrid>
        <div className="space-y-2">
          {plugins.map((item) => (
            <ListItem
              key={item.id}
              title={item.name}
              description={item.description || summarizeJson(item.masked_entry)}
              badge={
                item.entry_has_sensitive_data ||
                item.manifest_has_sensitive_data ? (
                  <Badge variant="outline">{t("settings.admin.masked")}</Badge>
                ) : undefined
              }
              danger={
                <AdminItemActions
                  isSaving={isSaving}
                  onEdit={() => {
                    setEditingPluginId(item.id);
                    setPluginEditState({
                      name: item.name,
                      description: item.description ?? "",
                      version: item.version ?? "",
                      entry: "",
                      manifest: "",
                      defaultEnabled: item.default_enabled,
                      forceEnabled: item.force_enabled,
                    });
                  }}
                  onDelete={() => onDelete(item.id)}
                />
              }
            >
              {editingPluginId === item.id && pluginEditState ? (
                <div className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-3">
                    <AdminLabeledInputField
                      label={t("settings.admin.pluginNamePlaceholder")}
                      value={pluginEditState.name}
                      onChange={(value) =>
                        setPluginEditState((current) =>
                          current ? { ...current, name: value } : current,
                        )
                      }
                    />
                    <AdminLabeledInputField
                      label={t("settings.admin.envDescriptionPlaceholder")}
                      value={pluginEditState.description}
                      onChange={(value) =>
                        setPluginEditState((current) =>
                          current
                            ? { ...current, description: value }
                            : current,
                        )
                      }
                    />
                    <AdminLabeledInputField
                      label={t("settings.admin.pluginVersionPlaceholder")}
                      value={pluginEditState.version}
                      onChange={(value) =>
                        setPluginEditState((current) =>
                          current ? { ...current, version: value } : current,
                        )
                      }
                    />
                    <AdminPolicySwitchField
                      label={t("settings.admin.policyDefaultEnabled")}
                      checked={pluginEditState.defaultEnabled}
                      onCheckedChange={(checked) =>
                        setPluginEditState((current) =>
                          current
                            ? { ...current, defaultEnabled: checked }
                            : current,
                        )
                      }
                    />
                    <AdminPolicySwitchField
                      label={t("settings.admin.policyForceEnabled")}
                      checked={pluginEditState.forceEnabled}
                      onCheckedChange={(checked) =>
                        setPluginEditState((current) =>
                          current
                            ? { ...current, forceEnabled: checked }
                            : current,
                        )
                      }
                    />
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <AdminLabeledTextareaField
                      label={t("settings.admin.pluginEntry")}
                      value={pluginEditState.entry}
                      onChange={(value) =>
                        setPluginEditState((current) =>
                          current ? { ...current, entry: value } : current,
                        )
                      }
                      className="min-h-32"
                      placeholder={t("settings.admin.reenterConfigPlaceholder")}
                    />
                    <AdminLabeledTextareaField
                      label={t("settings.admin.pluginManifest")}
                      value={pluginEditState.manifest}
                      onChange={(value) =>
                        setPluginEditState((current) =>
                          current ? { ...current, manifest: value } : current,
                        )
                      }
                      className="min-h-32"
                      placeholder={t("settings.admin.reenterConfigPlaceholder")}
                    />
                  </div>
                  <AdminMaskedUpdateHint />
                  <AdminEditActions
                    isSaving={isSaving}
                    onCancel={resetEditingState}
                    onSave={async () => {
                      await onUpdate(item.id, {
                        name: pluginEditState.name,
                        description: pluginEditState.description || undefined,
                        version: pluginEditState.version || undefined,
                        entry: pluginEditState.entry.trim()
                          ? parseJsonObject(
                              pluginEditState.entry,
                              t("settings.admin.invalidJsonObject"),
                            )
                          : undefined,
                        manifest: pluginEditState.manifest.trim()
                          ? parseJsonObject(
                              pluginEditState.manifest,
                              t("settings.admin.invalidJsonObject"),
                            )
                          : undefined,
                        default_enabled: pluginEditState.defaultEnabled,
                        force_enabled: pluginEditState.forceEnabled,
                      });
                      resetEditingState();
                    }}
                  />
                </div>
              ) : null}
            </ListItem>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
