"use client";

import { Shield } from "lucide-react";

import { AdminEnvVarsSection } from "@/features/settings/components/tabs/admin/env-vars-section";
import { AdminMcpSection } from "@/features/settings/components/tabs/admin/mcp-section";
import { AdminModelConfigSection } from "@/features/settings/components/tabs/admin/model-config-section";
import { AdminPluginsSection } from "@/features/settings/components/tabs/admin/plugins-section";
import { AdminPresetsSection } from "@/features/settings/components/tabs/admin/presets-section";
import { AdminSlashCommandsSection } from "@/features/settings/components/tabs/admin/slash-commands-section";
import { AdminSubAgentsSection } from "@/features/settings/components/tabs/admin/sub-agents-section";
import { AdminClaudeMdSection } from "@/features/settings/components/tabs/admin/claude-md-section";
import { AdminSkillsSection } from "@/features/settings/components/tabs/admin/skills-section";
import { AdminUsersSection } from "@/features/settings/components/tabs/admin/users-section";
import { SectionCard } from "@/features/settings/components/tabs/admin/shared";
import { useAdminConsole } from "@/features/settings/hooks/use-admin-console";
import { useT } from "@/lib/i18n/client";

export function AdminSettingsTab() {
  const { t } = useT("translation");
  const {
    envVars,
    users,
    skills,
    mcpServers,
    plugins,
    slashCommands,
    subAgents,
    presets,
    presetVisuals,
    systemClaudeMd,
    modelConfig,
    isLoadingScope,
    hasErrorScope,
    isSavingScope,
    refreshScope,
    saveModelConfig,
    createEnvVar,
    updateEnvVar,
    deleteEnvVar,
    createSkill,
    updateSkill,
    deleteSkill,
    createMcpServer,
    updateMcpServer,
    deleteMcpServer,
    createPlugin,
    updatePlugin,
    deletePlugin,
    createSlashCommand,
    updateSlashCommand,
    deleteSlashCommand,
    createSubAgent,
    updateSubAgent,
    deleteSubAgent,
    createPreset,
    updatePreset,
    deletePreset,
    saveSystemClaudeMd,
    deleteSystemClaudeMd,
    updateUserRole,
  } = useAdminConsole();

  const sectionSaving = {
    modelConfig: isSavingScope("modelConfig"),
    envVars: isSavingScope("envVars"),
    skills: isSavingScope("skills"),
    mcp: isSavingScope("mcp"),
    plugins: isSavingScope("plugins"),
    slashCommands: isSavingScope("slashCommands"),
    subAgents: isSavingScope("subAgents"),
    presets: isSavingScope("presets"),
    claudeMd: isSavingScope("claudeMd"),
    users: isSavingScope("users"),
  };

  const sectionLoading = {
    modelConfig: isLoadingScope("modelConfig"),
    envVars: isLoadingScope("envVars"),
    skills: isLoadingScope("skills"),
    mcp: isLoadingScope("mcp"),
    plugins: isLoadingScope("plugins"),
    slashCommands: isLoadingScope("slashCommands"),
    subAgents: isLoadingScope("subAgents"),
    presets: isLoadingScope("presets"),
    claudeMd: isLoadingScope("claudeMd"),
    users: isLoadingScope("users"),
  };

  const sectionError = {
    modelConfig: hasErrorScope("modelConfig"),
    envVars: hasErrorScope("envVars"),
    skills: hasErrorScope("skills"),
    mcp: hasErrorScope("mcp"),
    plugins: hasErrorScope("plugins"),
    slashCommands: hasErrorScope("slashCommands"),
    subAgents: hasErrorScope("subAgents"),
    presets: hasErrorScope("presets"),
    claudeMd: hasErrorScope("claudeMd"),
    users: hasErrorScope("users"),
  };

  return (
    <div className="flex-1 space-y-6 overflow-y-auto p-5">
      <SectionCard
        title={t("settings.admin.title")}
        description={t("settings.admin.description")}
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Shield className="size-4" />
          <span>{t("settings.admin.scopeHint")}</span>
        </div>
      </SectionCard>

      <AdminModelConfigSection
        isLoading={sectionLoading.modelConfig}
        hasError={sectionError.modelConfig}
        isSaving={sectionSaving.modelConfig}
        modelConfig={modelConfig}
        onRetry={() => refreshScope("modelConfig")}
        onSave={saveModelConfig}
      />

      <AdminEnvVarsSection
        envVars={envVars}
        isLoading={sectionLoading.envVars}
        hasError={sectionError.envVars}
        isSaving={sectionSaving.envVars}
        onRefresh={() => refreshScope("envVars")}
        onRetry={() => refreshScope("envVars")}
        onCreate={createEnvVar}
        onUpdate={updateEnvVar}
        onDelete={deleteEnvVar}
      />

      <AdminSkillsSection
        isLoading={sectionLoading.skills}
        hasError={sectionError.skills}
        isSaving={sectionSaving.skills}
        skills={skills}
        onRetry={() => refreshScope("skills")}
        onCreate={createSkill}
        onUpdate={updateSkill}
        onDelete={deleteSkill}
      />

      <AdminMcpSection
        isLoading={sectionLoading.mcp}
        hasError={sectionError.mcp}
        isSaving={sectionSaving.mcp}
        mcpServers={mcpServers}
        onRetry={() => refreshScope("mcp")}
        onCreate={createMcpServer}
        onUpdate={updateMcpServer}
        onDelete={deleteMcpServer}
      />

      <AdminPluginsSection
        isLoading={sectionLoading.plugins}
        hasError={sectionError.plugins}
        isSaving={sectionSaving.plugins}
        plugins={plugins}
        onRetry={() => refreshScope("plugins")}
        onCreate={createPlugin}
        onUpdate={updatePlugin}
        onDelete={deletePlugin}
      />

      <AdminSlashCommandsSection
        isLoading={sectionLoading.slashCommands}
        hasError={sectionError.slashCommands}
        isSaving={sectionSaving.slashCommands}
        commands={slashCommands}
        onRetry={() => refreshScope("slashCommands")}
        onCreate={createSlashCommand}
        onUpdate={updateSlashCommand}
        onDelete={deleteSlashCommand}
      />

      <AdminSubAgentsSection
        isLoading={sectionLoading.subAgents}
        hasError={sectionError.subAgents}
        isSaving={sectionSaving.subAgents}
        subAgents={subAgents}
        onRetry={() => refreshScope("subAgents")}
        onCreate={createSubAgent}
        onUpdate={updateSubAgent}
        onDelete={deleteSubAgent}
      />

      <AdminPresetsSection
        isLoading={sectionLoading.presets}
        hasError={sectionError.presets}
        isSaving={sectionSaving.presets}
        presets={presets}
        onRetry={() => refreshScope("presets")}
        skills={skills}
        mcpServers={mcpServers}
        plugins={plugins}
        presetVisuals={presetVisuals}
        onCreate={createPreset}
        onUpdate={updatePreset}
        onDelete={deletePreset}
      />

      <AdminClaudeMdSection
        isLoading={sectionLoading.claudeMd}
        hasError={sectionError.claudeMd}
        isSaving={sectionSaving.claudeMd}
        settings={systemClaudeMd}
        onRetry={() => refreshScope("claudeMd")}
        onSave={saveSystemClaudeMd}
        onDelete={deleteSystemClaudeMd}
      />

      <AdminUsersSection
        isLoading={sectionLoading.users}
        hasError={sectionError.users}
        isSaving={sectionSaving.users}
        users={users}
        onRetry={() => refreshScope("users")}
        onUpdateRole={updateUserRole}
      />
    </div>
  );
}
