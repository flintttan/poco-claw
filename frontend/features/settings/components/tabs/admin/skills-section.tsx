"use client";

import * as React from "react";

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  AdminItemActions,
  AdminPolicyHint,
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  parseJsonObject,
  summarizeJson,
} from "./shared";
import { AdminCatalogShell } from "./admin-catalog-shell";

interface SkillEditState {
  name: string;
  description: string;
  entry: string;
}

interface SkillCreateState {
  name: string;
  description: string;
  entry: string;
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
  const [searchQuery, setSearchQuery] = React.useState("");
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editSkill, setEditSkill] = React.useState<Skill | null>(null);

  const [createState, setCreateState] = React.useState<SkillCreateState>({
    name: "",
    description: "",
    entry: "{}",
  });
  const [editState, setEditState] = React.useState<SkillEditState>({
    name: "",
    description: "",
    entry: "{}",
  });

  const filteredSkills = React.useMemo(() => {
    if (!searchQuery) return skills;
    const lowerQuery = searchQuery.toLowerCase();
    return skills.filter((skill) => {
      return (
        skill.name.toLowerCase().includes(lowerQuery) ||
        (skill.description || "").toLowerCase().includes(lowerQuery) ||
        JSON.stringify(skill.entry || {})
          .toLowerCase()
          .includes(lowerQuery)
      );
    });
  }, [searchQuery, skills]);

  React.useEffect(() => {
    if (!editSkill) return;
    setEditState({
      name: editSkill.name,
      description: editSkill.description ?? "",
      entry: JSON.stringify(editSkill.entry ?? {}, null, 2),
    });
  }, [editSkill]);

  return (
    <>
      <AdminCatalogShell
        title={t("settings.admin.skillsTitle")}
        description={t("settings.admin.skillsDescription")}
        summary={`${t("settings.admin.skillsTitle")} · ${filteredSkills.length}`}
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={t("library.skillsPage.searchPlaceholder")}
        createLabel={t("library.skillsPage.addCard")}
        onCreate={() => setCreateOpen(true)}
      >
        {isLoading ? <AdminSectionLoading /> : null}
        {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
        <div
          className={
            isLoading || hasError ? "pointer-events-none opacity-60" : undefined
          }
        >
          <AdminPolicyHint />
          <div className="space-y-2">
            {filteredSkills.map((item) => (
              <ListItem
                key={item.id}
                title={item.name}
                description={item.description || summarizeJson(item.entry)}
                danger={
                  <AdminItemActions
                    isSaving={isSaving}
                    onEdit={() => setEditSkill(item)}
                    onDelete={() => onDelete(item.id)}
                  />
                }
              />
            ))}
          </div>
        </div>
      </AdminCatalogShell>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.admin.skillsTitle")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input
              value={createState.name}
              onChange={(e) =>
                setCreateState((current) => ({
                  ...current,
                  name: e.target.value,
                }))
              }
              placeholder={t("settings.admin.skillNamePlaceholder")}
            />
            <Input
              value={createState.description}
              onChange={(e) =>
                setCreateState((current) => ({
                  ...current,
                  description: e.target.value,
                }))
              }
              placeholder={t("settings.admin.envDescriptionPlaceholder")}
            />
            <Textarea
              value={createState.entry}
              onChange={(e) =>
                setCreateState((current) => ({
                  ...current,
                  entry: e.target.value,
                }))
              }
              className="min-h-24"
              placeholder='{"s3_key":"..."}'
            />
          </div>
          <DialogFooter>
            <AdminCreateActions
              isSaving={isSaving}
              onCreate={async () => {
                if (!createState.name.trim()) {
                  throw new Error(t("settings.admin.skillNameRequired"));
                }
                await onCreate({
                  name: createState.name.trim(),
                  description: createState.description || undefined,
                  entry: parseJsonObject(
                    createState.entry,
                    t("settings.admin.invalidJsonObject"),
                  ),
                });
                setCreateOpen(false);
                setCreateState({ name: "", description: "", entry: "{}" });
              }}
            />
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={editSkill !== null}
        onOpenChange={(open) => {
          if (!open) setEditSkill(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("settings.admin.edit")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input
              value={editState.name}
              onChange={(e) =>
                setEditState((current) => ({
                  ...current,
                  name: e.target.value,
                }))
              }
              placeholder={t("settings.admin.skillNamePlaceholder")}
            />
            <Input
              value={editState.description}
              onChange={(e) =>
                setEditState((current) => ({
                  ...current,
                  description: e.target.value,
                }))
              }
              placeholder={t("settings.admin.envDescriptionPlaceholder")}
            />
            <Textarea
              value={editState.entry}
              onChange={(e) =>
                setEditState((current) => ({
                  ...current,
                  entry: e.target.value,
                }))
              }
              className="min-h-24"
            />
          </div>
          <DialogFooter>
            <AdminCreateActions
              isSaving={isSaving}
              onCreate={async () => {
                if (!editSkill) return;
                await onUpdate(editSkill.id, {
                  name: editState.name,
                  description: editState.description || undefined,
                  entry: parseJsonObject(
                    editState.entry,
                    t("settings.admin.invalidJsonObject"),
                  ),
                });
                setEditSkill(null);
              }}
            />
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
