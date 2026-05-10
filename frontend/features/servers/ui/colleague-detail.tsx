"use client";

import * as React from "react";
import {
  ArrowLeft,
  CalendarDays,
  Check,
  MessageSquare,
  Pencil,
  Power,
  RotateCw,
  Shield,
  Trash2,
  UserPlus,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { serversApi } from "@/features/servers";
import type { FileNode } from "@/features/chat/types";
import {
  getUserAvatarUrl,
  getUserDisplayName,
} from "@/features/servers/lib/server-conversation-view";
import {
  getAgentRuntimeDotClassName,
  getAgentRuntimeStatus,
} from "@/features/servers/lib/agent-runtime-status";
import type {
  ServerAgentItem,
  ServerChannelMemberItem,
  ServerMemberItem,
} from "@/features/servers/model/types";
import type { ColleagueSelection } from "@/features/servers/ui/server-workspace-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { ServerAgentAvatar } from "./server-agent-avatar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { AgentPersistentFilesPanel } from "./agent-persistent-files-panel";

const agentPersistentFilesCache = new Map<string, FileNode[]>();

export function ColleagueDetail({
  selection,
  agents,
  presets,
  members,
  serverId,
  canInspectPersistentFiles,
  canManageServer,
  activeChannelId,
  channelMembers = [],
  activeChannelIdByAgentId = {},
  channelNamesByAgentId = {},
  onClose,
  onOpenDm,
  onOpenActiveChannel,
  onRemoveMember,
  onRestartAgent,
  onStopAgent,
  onUpdateAgentDescription,
  onRemoveAgentFromServer,
  onRemoveMemberFromChannel,
}: {
  selection: ColleagueSelection | null;
  agents: ServerAgentItem[];
  presets: Preset[];
  members: ServerMemberItem[];
  serverId?: string | null;
  canInspectPersistentFiles?: boolean;
  canManageServer?: boolean;
  activeChannelId?: string | null;
  channelMembers?: ServerChannelMemberItem[];
  activeChannelIdByAgentId?: Record<string, string>;
  channelNamesByAgentId?: Record<string, string[]>;
  onClose: () => void;
  onOpenDm: (agentId: string) => void;
  onOpenActiveChannel?: (channelId: string) => void;
  onRemoveMember: (membershipId: number) => void;
  onRestartAgent: (agentId: string) => void;
  onStopAgent: (agentId: string) => void;
  onUpdateAgentDescription: (
    agentId: string,
    description: string,
  ) => Promise<void>;
  onRemoveAgentFromServer: (agentId: string) => void;
  onRemoveMemberFromChannel: (membershipId: number) => void;
}) {
  const { t } = useT("translation");
  const selectedAgent =
    selection?.kind === "agent"
      ? (agents.find((agent) => agent.id === selection.id) ?? null)
      : null;
  const selectedMember =
    selection?.kind === "human"
      ? (members.find((member) => member.id === selection.id) ?? null)
      : null;
  const selectedRuntimeStatus = selectedAgent
    ? getAgentRuntimeStatus(selectedAgent)
    : null;
  const selectedAgentId = selectedAgent?.id ?? null;
  const selectedAgentRemoved = Boolean(selectedAgent?.removedAt);
  const selectedAgentActiveChannelId = selectedAgent
    ? (activeChannelIdByAgentId[selectedAgent.id] ?? "")
    : "";
  const selectedMemberChannelMembership =
    selectedMember && activeChannelId
      ? (channelMembers.find(
          (member) => member.userId === selectedMember.userId,
        ) ?? null)
      : null;
  const [persistentFiles, setPersistentFiles] = React.useState<FileNode[]>([]);
  const [isLoadingPersistentFiles, setIsLoadingPersistentFiles] =
    React.useState(false);
  const [removeAgentConfirmOpen, setRemoveAgentConfirmOpen] =
    React.useState(false);
  const [restartAgentConfirmOpen, setRestartAgentConfirmOpen] =
    React.useState(false);
  const [stopAgentConfirmOpen, setStopAgentConfirmOpen] = React.useState(false);
  const [isEditingDescription, setIsEditingDescription] = React.useState(false);
  const [descriptionDraft, setDescriptionDraft] = React.useState("");
  const [isSavingDescription, setIsSavingDescription] = React.useState(false);
  const selectedAgentChannelNames = selectedAgent
    ? (channelNamesByAgentId[selectedAgent.id] ?? [])
    : [];
  const selectedAgentStopped =
    (selectedAgent?.lifecycleState || "").trim().toLowerCase() === "inactive";

  React.useEffect(() => {
    setIsEditingDescription(false);
    setDescriptionDraft(selectedAgent?.description ?? "");
    setIsSavingDescription(false);
  }, [selectedAgent?.description, selectedAgent?.id]);

  const handleDescriptionAction = async () => {
    if (!selectedAgent || selectedAgentRemoved || isSavingDescription) {
      return;
    }
    if (!isEditingDescription) {
      setDescriptionDraft(selectedAgent.description ?? "");
      setIsEditingDescription(true);
      return;
    }
    setIsSavingDescription(true);
    try {
      await onUpdateAgentDescription(selectedAgent.id, descriptionDraft);
      setIsEditingDescription(false);
    } finally {
      setIsSavingDescription(false);
    }
  };

  React.useEffect(() => {
    if (!canInspectPersistentFiles || !serverId || !selectedAgentId) {
      setPersistentFiles([]);
      return;
    }
    const cacheKey = `${serverId}:${selectedAgentId}`;
    const cachedFiles = agentPersistentFilesCache.get(cacheKey);
    if (cachedFiles) {
      setPersistentFiles(cachedFiles);
      setIsLoadingPersistentFiles(false);
      return;
    }
    let cancelled = false;
    const load = async () => {
      try {
        setIsLoadingPersistentFiles(true);
        const files = await serversApi.listAgentStateFiles(
          serverId,
          selectedAgentId,
        );
        if (!cancelled) {
          agentPersistentFilesCache.set(cacheKey, files);
          setPersistentFiles(files);
        }
      } catch (error) {
        console.error(
          "[ColleagueDetail] failed to load persistent files",
          error,
        );
        if (!cancelled) {
          setPersistentFiles([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingPersistentFiles(false);
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [canInspectPersistentFiles, selectedAgentId, serverId]);

  return (
    <aside className="absolute inset-y-0 right-0 z-30 flex w-full flex-col border-l border-border bg-card md:left-[17rem] md:w-auto lg:left-[18rem] xl:static xl:h-full xl:w-full xl:min-w-0 xl:shrink-0">
      <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-5">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("conversationView.backToContext")}
            className="shrink-0 xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <p className="text-base font-semibold text-foreground">
            {t("conversationView.colleagues.detailTitle")}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          {t("conversationView.close")}
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {selectedAgent ? (
          <div className="flex h-full min-h-0 flex-col gap-5 px-6 py-6">
            <div className="flex items-start gap-4">
              <ServerAgentAvatar
                agent={selectedAgent}
                presets={presets}
                className="size-14 shrink-0"
                fallbackClassName="text-lg"
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="truncate text-lg font-semibold text-foreground">
                    {selectedAgent.displayName}
                  </p>
                  {selectedRuntimeStatus ? (
                    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground">
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          getAgentRuntimeDotClassName(
                            selectedRuntimeStatus.tone,
                          ),
                        )}
                      />
                      {t(selectedRuntimeStatus.labelKey)}
                    </span>
                  ) : null}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <p className="text-sm text-muted-foreground">
                    @{selectedAgent.handle}
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => onOpenDm(selectedAgent.id)}
                    disabled={selectedAgentRemoved}
                    className="h-7 pl-3.5 pr-3"
                  >
                    <MessageSquare className="size-3.5" />
                    {t("conversationView.messageAgent")}
                  </Button>
                </div>
              </div>
            </div>
            <div className="rounded-md border border-border bg-background px-4 py-4">
              <div className="flex items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  {t("conversationView.colleagues.description")}
                </p>
                {canManageServer && !selectedAgentRemoved ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => void handleDescriptionAction()}
                    disabled={isSavingDescription}
                    aria-label={
                      isEditingDescription
                        ? t("conversationView.colleagues.saveDescription")
                        : t("conversationView.colleagues.editDescription")
                    }
                    className="size-6 text-muted-foreground hover:text-foreground"
                  >
                    {isEditingDescription ? (
                      <Check className="size-4" />
                    ) : (
                      <Pencil className="size-4" />
                    )}
                  </Button>
                ) : null}
              </div>
              {isEditingDescription ? (
                <textarea
                  value={descriptionDraft}
                  onChange={(event) => setDescriptionDraft(event.target.value)}
                  rows={4}
                  className="mt-3 min-h-24 w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm leading-6 text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50"
                  placeholder={t(
                    "conversationView.colleagues.agentDescriptionPlaceholder",
                  )}
                />
              ) : (
                <p className="mt-3 text-sm leading-6 text-foreground">
                  {selectedAgent.description ||
                    t("conversationView.colleagues.agentEmptyDescription")}
                </p>
              )}
            </div>
            {canInspectPersistentFiles && selectedAgent.persistentState ? (
              <div className="flex min-h-0 flex-1 flex-col space-y-3 overflow-hidden px-1 py-1">
                <div className="shrink-0 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    {t("conversationView.colleagues.persistentFiles")}
                  </p>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {t("conversationView.colleagues.persistentFilesHint")}
                  </p>
                </div>
                <AgentPersistentFilesPanel
                  files={persistentFiles}
                  isLoading={isLoadingPersistentFiles}
                  emptyMessage={t(
                    "conversationView.colleagues.persistentFilesEmpty",
                  )}
                  className="min-h-0 flex-1"
                />
              </div>
            ) : null}
            <div className="mt-auto flex shrink-0 flex-wrap justify-end gap-2 border-t border-border pt-5">
              {selectedRuntimeStatus?.labelKey ===
                "conversationView.colleagues.runtimeStates.active" &&
              selectedAgentActiveChannelId &&
              onOpenActiveChannel ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    onOpenActiveChannel(selectedAgentActiveChannelId)
                  }
                >
                  <MessageSquare className="size-4" />
                  {t("conversationView.backToContext")}
                </Button>
              ) : null}
              {canManageServer ? (
                <>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setRestartAgentConfirmOpen(true)}
                    disabled={selectedAgentRemoved}
                  >
                    <RotateCw className="size-4" />
                    {selectedAgentStopped
                      ? t("conversationView.colleagues.startAgent")
                      : t("conversationView.colleagues.restartAgent")}
                  </Button>
                  {!selectedAgentStopped ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setStopAgentConfirmOpen(true)}
                      disabled={selectedAgentRemoved}
                    >
                      <Power className="size-4" />
                      {t("conversationView.colleagues.stopAgent")}
                    </Button>
                  ) : null}
                  <AlertDialog
                    open={restartAgentConfirmOpen}
                    onOpenChange={setRestartAgentConfirmOpen}
                  >
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          {selectedAgentStopped
                            ? t("conversationView.colleagues.startAgentTitle", {
                                name: selectedAgent.displayName,
                              })
                            : t(
                                "conversationView.colleagues.restartAgentTitle",
                                {
                                  name: selectedAgent.displayName,
                                },
                              )}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          {selectedAgentStopped
                            ? t(
                                "conversationView.colleagues.startAgentDescription",
                              )
                            : t(
                                "conversationView.colleagues.restartAgentDescription",
                              )}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>
                          {t("common.cancel")}
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => {
                            onRestartAgent(selectedAgent.id);
                            setRestartAgentConfirmOpen(false);
                          }}
                        >
                          {selectedAgentStopped
                            ? t("conversationView.colleagues.startAgent")
                            : t("conversationView.colleagues.restartAgent")}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                  <AlertDialog
                    open={stopAgentConfirmOpen}
                    onOpenChange={setStopAgentConfirmOpen}
                  >
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          {t("conversationView.colleagues.stopAgentTitle", {
                            name: selectedAgent.displayName,
                          })}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          {t(
                            "conversationView.colleagues.stopAgentDescription",
                          )}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>
                          {t("common.cancel")}
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => {
                            onStopAgent(selectedAgent.id);
                            setStopAgentConfirmOpen(false);
                          }}
                        >
                          {t("conversationView.colleagues.stopAgent")}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                  {!selectedAgentRemoved ? (
                    <AlertDialog
                      open={removeAgentConfirmOpen}
                      onOpenChange={setRemoveAgentConfirmOpen}
                    >
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => setRemoveAgentConfirmOpen(true)}
                        className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Trash2 className="size-4" />
                        {t("conversationView.colleagues.remove")}
                      </Button>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            {t("conversationView.colleagues.removeAgentTitle", {
                              name: selectedAgent.displayName,
                            })}
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            {selectedAgentChannelNames.length > 0
                              ? t(
                                  "conversationView.colleagues.removeAgentDescription",
                                  {
                                    channels: selectedAgentChannelNames
                                      .slice(0, 3)
                                      .join(", "),
                                  },
                                )
                              : t(
                                  "conversationView.colleagues.removeAgentDescriptionUnknown",
                                )}
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>
                            {t("common.cancel")}
                          </AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => {
                              onRemoveAgentFromServer(selectedAgent.id);
                              setRemoveAgentConfirmOpen(false);
                            }}
                          >
                            {t("conversationView.colleagues.remove")}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  ) : null}
                </>
              ) : null}
            </div>
          </div>
        ) : selectedMember ? (
          <div className="h-full space-y-5 overflow-y-auto px-6 py-6">
            <div className="flex items-start gap-4">
              {getUserAvatarUrl(selectedMember.user) ? (
                <Avatar className="size-14 shrink-0 rounded-md border border-border">
                  <AvatarImage
                    src={getUserAvatarUrl(selectedMember.user) ?? undefined}
                    alt={getUserDisplayName(
                      selectedMember.user,
                      selectedMember.userId,
                    )}
                  />
                  <AvatarFallback className="rounded-md bg-muted text-lg font-semibold text-foreground">
                    {getUserDisplayName(
                      selectedMember.user,
                      selectedMember.userId,
                    )
                      .charAt(0)
                      .toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              ) : (
                <span className="flex size-14 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                  <UserRound className="size-6" />
                </span>
              )}
              <div className="min-w-0">
                <p className="truncate text-lg font-semibold text-foreground">
                  {getUserDisplayName(
                    selectedMember.user,
                    selectedMember.userId,
                  )}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {selectedMember.status}
                </p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <InfoTile
                icon={<Shield className="size-4" />}
                label={t("conversationView.colleagues.role")}
                value={selectedMember.role}
              />
              <InfoTile
                icon={<CalendarDays className="size-4" />}
                label={t("conversationView.colleagues.joined")}
                value={selectedMember.joinedAt}
              />
            </div>
            <InfoTile
              icon={<UserPlus className="size-4" />}
              label={t("conversationView.colleagues.invitedBy")}
              value={
                selectedMember.invitedBy ||
                t("conversationView.colleagues.emptyValue")
              }
            />
            <div className="flex flex-wrap gap-2 border-t border-border pt-5">
              {canManageServer && selectedMemberChannelMembership ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    onRemoveMemberFromChannel(
                      selectedMemberChannelMembership.id,
                    )
                  }
                  className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                >
                  <Trash2 className="size-4" />
                  {t("conversationView.colleagues.removeFromChannel")}
                </Button>
              ) : null}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onRemoveMember(selectedMember.id)}
                disabled={!canManageServer}
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="size-4" />
                {t("conversationView.colleagues.removeMember")}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center px-6 py-12 text-center text-sm text-muted-foreground">
            {t("conversationView.colleagues.emptySelection")}
          </div>
        )}
      </div>
    </aside>
  );
}

function InfoTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-border bg-background px-4 py-3">
      <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="mt-2 break-all text-sm text-foreground">{value}</p>
    </div>
  );
}
