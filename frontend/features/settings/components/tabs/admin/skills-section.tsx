import * as React from "react";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type {
  Skill,
  SkillCreateInput,
  SkillUpdateInput,
} from "@/features/capabilities/skills/types";
import { useT } from "@/lib/i18n/client";

import {
  AdminCreateActions,
  AdminCreateGrid,
  AdminEditActions,
  AdminItemActions,
  AdminLabeledInputField,
  AdminLabeledTextareaField,
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

interface SkillEditState {
  name: string;
  description: string;
  entry: string;
  defaultEnabled: boolean;
  forceEnabled: boolean;
}

interface AdminSkillsSectionProps {
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  skills: Skill[];
  onRetry: () => void;
  onCreate: (input: SkillCreateInput) => Promise<void>;
  onUpdate: (skillId: number, input: SkillUpdateInput) => Promise<void>;
  onDelete: (skillId: number) => Promise<void>;
}

export function AdminSkillsSection({
  isLoading,
  hasError,
  isSaving,
  skills,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminSkillsSectionProps) {
  const { t } = useT("translation");
  const [newSkillName, setNewSkillName] = React.useState("");
  const [newSkillDescription, setNewSkillDescription] = React.useState("");
  const [newSkillEntry, setNewSkillEntry] = React.useState("{}");
  const [newDefaultEnabled, setNewDefaultEnabled] = React.useState(false);
  const [newForceEnabled, setNewForceEnabled] = React.useState(false);
  const [editingSkillId, setEditingSkillId] = React.useState<number | null>(
    null,
  );
  const [skillEditState, setSkillEditState] =
    React.useState<SkillEditState | null>(null);

  const resetEditingState = React.useCallback(() => {
    setEditingSkillId(null);
    setSkillEditState(null);
  }, []);

  return (
    <SectionCard
      title={t("settings.admin.skillsTitle")}
      description={t("settings.admin.skillsDescription")}
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
            value={newSkillName}
            onChange={(e) => setNewSkillName(e.target.value)}
            placeholder={t("settings.admin.skillNamePlaceholder")}
          />
          <Input
            value={newSkillDescription}
            onChange={(e) => setNewSkillDescription(e.target.value)}
            placeholder={t("settings.admin.envDescriptionPlaceholder")}
          />
          <Textarea
            value={newSkillEntry}
            onChange={(e) => setNewSkillEntry(e.target.value)}
            className="min-h-24"
            placeholder='{"s3_key":"..."}'
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
          <AdminCreateActions
            isSaving={isSaving}
            onCreate={async () => {
              if (!newSkillName.trim()) {
                throw new Error(t("settings.admin.skillNameRequired"));
              }
              await onCreate({
                name: newSkillName.trim(),
                description: newSkillDescription || undefined,
                entry: parseJsonObject(
                  newSkillEntry,
                  t("settings.admin.invalidJsonObject"),
                ),
                default_enabled: newDefaultEnabled,
                force_enabled: newForceEnabled,
              });
              setNewSkillName("");
              setNewSkillDescription("");
              setNewSkillEntry("{}");
              setNewDefaultEnabled(false);
              setNewForceEnabled(false);
            }}
          />
        </AdminCreateGrid>
        <div className="space-y-2">
          {skills.map((item) => (
            <ListItem
              key={item.id}
              title={item.name}
              description={item.description || summarizeJson(item.entry)}
              danger={
                <AdminItemActions
                  isSaving={isSaving}
                  onEdit={() => {
                    setEditingSkillId(item.id);
                    setSkillEditState({
                      name: item.name,
                      description: item.description ?? "",
                      entry: JSON.stringify(item.entry ?? {}, null, 2),
                      defaultEnabled: item.default_enabled,
                      forceEnabled: item.force_enabled,
                    });
                  }}
                  onDelete={() => onDelete(item.id)}
                />
              }
            >
              {editingSkillId === item.id && skillEditState ? (
                <div className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-2">
                    <AdminLabeledInputField
                      label={t("settings.admin.skillNamePlaceholder")}
                      value={skillEditState.name}
                      onChange={(value) =>
                        setSkillEditState((current) =>
                          current ? { ...current, name: value } : current,
                        )
                      }
                    />
                    <AdminLabeledInputField
                      label={t("settings.admin.envDescriptionPlaceholder")}
                      value={skillEditState.description}
                      onChange={(value) =>
                        setSkillEditState((current) =>
                          current
                            ? { ...current, description: value }
                            : current,
                        )
                      }
                    />
                    <AdminPolicySwitchField
                      label={t("settings.admin.policyDefaultEnabled")}
                      checked={skillEditState.defaultEnabled}
                      onCheckedChange={(checked) =>
                        setSkillEditState((current) =>
                          current
                            ? { ...current, defaultEnabled: checked }
                            : current,
                        )
                      }
                    />
                    <AdminPolicySwitchField
                      label={t("settings.admin.policyForceEnabled")}
                      checked={skillEditState.forceEnabled}
                      onCheckedChange={(checked) =>
                        setSkillEditState((current) =>
                          current
                            ? { ...current, forceEnabled: checked }
                            : current,
                        )
                      }
                    />
                  </div>
                  <AdminLabeledTextareaField
                    label={t("settings.admin.jsonConfig")}
                    value={skillEditState.entry}
                    onChange={(value) =>
                      setSkillEditState((current) =>
                        current ? { ...current, entry: value } : current,
                      )
                    }
                    className="min-h-32"
                  />
                  <AdminEditActions
                    isSaving={isSaving}
                    onCancel={resetEditingState}
                    onSave={async () => {
                      await onUpdate(item.id, {
                        name: skillEditState.name,
                        description: skillEditState.description || undefined,
                        entry: parseJsonObject(
                          skillEditState.entry,
                          t("settings.admin.invalidJsonObject"),
                        ),
                        default_enabled: skillEditState.defaultEnabled,
                        force_enabled: skillEditState.forceEnabled,
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
