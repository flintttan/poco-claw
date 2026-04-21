import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type {
  McpServerCreateInput,
  McpServerUpdateInput,
} from "@/features/capabilities/mcp/types";
import type { AdminMcpServer } from "@/features/settings/api/admin-api";
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

interface McpEditState {
  name: string;
  description: string;
  serverConfig: string;
  defaultEnabled: boolean;
  forceEnabled: boolean;
}

interface AdminMcpSectionProps {
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  mcpServers: AdminMcpServer[];
  onRetry: () => void;
  onCreate: (input: McpServerCreateInput) => Promise<void>;
  onUpdate: (serverId: number, input: McpServerUpdateInput) => Promise<void>;
  onDelete: (serverId: number) => Promise<void>;
}

export function AdminMcpSection({
  isLoading,
  hasError,
  isSaving,
  mcpServers,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminMcpSectionProps) {
  const { t } = useT("translation");
  const [newMcpName, setNewMcpName] = React.useState("");
  const [newMcpDescription, setNewMcpDescription] = React.useState("");
  const [newMcpConfig, setNewMcpConfig] = React.useState('{"mcpServers":{}}');
  const [newDefaultEnabled, setNewDefaultEnabled] = React.useState(false);
  const [newForceEnabled, setNewForceEnabled] = React.useState(false);
  const [editingMcpId, setEditingMcpId] = React.useState<number | null>(null);
  const [mcpEditState, setMcpEditState] = React.useState<McpEditState | null>(
    null,
  );

  const resetEditingState = React.useCallback(() => {
    setEditingMcpId(null);
    setMcpEditState(null);
  }, []);

  return (
    <SectionCard
      title={t("settings.admin.mcpTitle")}
      description={t("settings.admin.mcpDescription")}
    >
      {isLoading ? <AdminSectionLoading /> : null}
      {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
      <div
        className={
          isLoading || hasError ? "pointer-events-none opacity-60" : undefined
        }
      >
        <AdminPolicyHint />
        <AdminCreateGrid columns="three">
          <Input
            value={newMcpName}
            onChange={(e) => setNewMcpName(e.target.value)}
            placeholder={t("settings.admin.mcpNamePlaceholder")}
          />
          <Input
            value={newMcpDescription}
            onChange={(e) => setNewMcpDescription(e.target.value)}
            placeholder={t("settings.admin.envDescriptionPlaceholder")}
          />
          <AdminCreateActions
            isSaving={isSaving}
            onCreate={async () => {
              if (!newMcpName.trim()) {
                throw new Error(t("settings.admin.mcpNameRequired"));
              }
              await onCreate({
                name: newMcpName.trim(),
                description: newMcpDescription || undefined,
                server_config: parseJsonObject(
                  newMcpConfig,
                  t("settings.admin.invalidJsonObject"),
                ),
                default_enabled: newDefaultEnabled,
                force_enabled: newForceEnabled,
              });
              setNewMcpName("");
              setNewMcpDescription("");
              setNewMcpConfig('{"mcpServers":{}}');
              setNewDefaultEnabled(false);
              setNewForceEnabled(false);
            }}
          />
        </AdminCreateGrid>
        <Textarea
          value={newMcpConfig}
          onChange={(e) => setNewMcpConfig(e.target.value)}
          className="min-h-28"
        />
        <AdminCreateGrid columns="two">
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
        <div className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
          {t("settings.admin.mcpSecretHint")}
        </div>
        <div className="space-y-2">
          {mcpServers.map((item) => (
            <ListItem
              key={item.id}
              title={item.name}
              description={
                item.description || summarizeJson(item.masked_server_config)
              }
              badge={
                item.has_sensitive_data ? (
                  <Badge variant="outline">{t("settings.admin.masked")}</Badge>
                ) : undefined
              }
              danger={
                <AdminItemActions
                  isSaving={isSaving}
                  onEdit={() => {
                    setEditingMcpId(item.id);
                    setMcpEditState({
                      name: item.name,
                      description: item.description ?? "",
                      serverConfig: "",
                      defaultEnabled: item.default_enabled,
                      forceEnabled: item.force_enabled,
                    });
                  }}
                  onDelete={() => onDelete(item.id)}
                />
              }
            >
              {editingMcpId === item.id && mcpEditState ? (
                <div className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-2">
                    <AdminLabeledInputField
                      label={t("settings.admin.mcpNamePlaceholder")}
                      value={mcpEditState.name}
                      onChange={(value) =>
                        setMcpEditState((current) =>
                          current ? { ...current, name: value } : current,
                        )
                      }
                    />
                    <AdminLabeledInputField
                      label={t("settings.admin.envDescriptionPlaceholder")}
                      value={mcpEditState.description}
                      onChange={(value) =>
                        setMcpEditState((current) =>
                          current
                            ? { ...current, description: value }
                            : current,
                        )
                      }
                    />
                    <AdminPolicySwitchField
                      label={t("settings.admin.policyDefaultEnabled")}
                      checked={mcpEditState.defaultEnabled}
                      onCheckedChange={(checked) =>
                        setMcpEditState((current) =>
                          current
                            ? { ...current, defaultEnabled: checked }
                            : current,
                        )
                      }
                    />
                    <AdminPolicySwitchField
                      label={t("settings.admin.policyForceEnabled")}
                      checked={mcpEditState.forceEnabled}
                      onCheckedChange={(checked) =>
                        setMcpEditState((current) =>
                          current
                            ? { ...current, forceEnabled: checked }
                            : current,
                        )
                      }
                    />
                  </div>
                  <AdminLabeledTextareaField
                    label={t("settings.admin.jsonConfig")}
                    value={mcpEditState.serverConfig}
                    onChange={(value) =>
                      setMcpEditState((current) =>
                        current ? { ...current, serverConfig: value } : current,
                      )
                    }
                    className="min-h-32"
                    placeholder={t("settings.admin.reenterConfigPlaceholder")}
                  />
                  <AdminMaskedUpdateHint />
                  <AdminEditActions
                    isSaving={isSaving}
                    onCancel={resetEditingState}
                    onSave={async () => {
                      await onUpdate(item.id, {
                        name: mcpEditState.name,
                        description: mcpEditState.description || undefined,
                        server_config: mcpEditState.serverConfig.trim()
                          ? parseJsonObject(
                              mcpEditState.serverConfig,
                              t("settings.admin.invalidJsonObject"),
                            )
                          : undefined,
                        default_enabled: mcpEditState.defaultEnabled,
                        force_enabled: mcpEditState.forceEnabled,
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
