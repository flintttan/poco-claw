"use client";

import * as React from "react";
import {
  CheckCheck,
  ChevronRight,
  CircleDashed,
  LoaderCircle,
  Save,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { channelTasksApi } from "@/features/channel-tasks/api/channel-tasks-api";
import type {
  ChannelTask,
  ChannelTaskActivityMessage,
  ChannelTaskStatus,
} from "@/features/channel-tasks/model/types";
import { useT } from "@/lib/i18n/client";

function StatusIcon({ status }: { status: ChannelTaskStatus }) {
  if (status === "in_progress") {
    return <LoaderCircle className="size-3.5 text-primary" />;
  }
  if (status === "in_review") {
    return <ChevronRight className="size-3.5 text-primary" />;
  }
  if (status === "done") {
    return <CheckCheck className="size-3.5 text-primary" />;
  }
  return <CircleDashed className="size-3.5 text-muted-foreground" />;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function ActivityItem({ message }: { message: ChannelTaskActivityMessage }) {
  return (
    <div className="rounded-2xl border border-border/60 bg-background/70 px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <Badge variant="outline">{message.messageType}</Badge>
        <span className="text-xs text-muted-foreground">
          {formatDateTime(message.createdAt)}
        </span>
      </div>
      <p className="mt-2 text-sm text-foreground">
        {message.textPreview || JSON.stringify(message.content)}
      </p>
    </div>
  );
}

export function ChannelTaskDetailDialog({
  open,
  onOpenChange,
  serverId,
  channelId,
  taskId,
  onTaskUpdated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverId: string;
  channelId: string;
  taskId: string | null;
  onTaskUpdated: (task: ChannelTask) => void;
}) {
  const { t } = useT("translation");
  const [task, setTask] = React.useState<ChannelTask | null>(null);
  const [activity, setActivity] = React.useState<ChannelTaskActivityMessage[]>(
    [],
  );
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");

  const loadTask = React.useCallback(async () => {
    if (!open || !taskId) {
      return;
    }
    setIsLoading(true);
    try {
      const nextTask = await channelTasksApi.getTask(
        serverId,
        channelId,
        taskId,
      );
      setTask(nextTask);
      setTitle(nextTask.title);
      setDescription(nextTask.description ?? "");
      if (nextTask.threadRootMessageId) {
        setActivity(
          await channelTasksApi.getTaskThread(
            serverId,
            channelId,
            nextTask.threadRootMessageId,
          ),
        );
      } else {
        setActivity([]);
      }
    } catch (error) {
      console.error("[ChannelTasks] detail load failed", error);
      toast.error(t("channelTasks.toasts.detailLoadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [channelId, open, serverId, t, taskId]);

  React.useEffect(() => {
    void loadTask();
  }, [loadTask]);

  const syncTask = (nextTask: ChannelTask) => {
    setTask(nextTask);
    setTitle(nextTask.title);
    setDescription(nextTask.description ?? "");
    onTaskUpdated(nextTask);
  };

  const handleSave = async () => {
    if (!taskId) {
      return;
    }
    setIsSaving(true);
    try {
      const nextTask = await channelTasksApi.updateTask(
        serverId,
        channelId,
        taskId,
        {
          title,
          description,
        },
      );
      syncTask(nextTask);
      toast.success(t("channelTasks.toasts.updated"));
    } catch (error) {
      console.error("[ChannelTasks] update failed", error);
      toast.error(t("channelTasks.toasts.updateFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  const handleClaimToggle = async () => {
    if (!taskId || !task) {
      return;
    }
    setIsSaving(true);
    try {
      const nextTask =
        task.assigneeUserId || task.assigneePresetId
          ? await channelTasksApi.unclaimTask(serverId, channelId, taskId)
          : await channelTasksApi.claimTask(serverId, channelId, taskId);
      syncTask(nextTask);
      await loadTask();
      toast.success(
        task.assigneeUserId || task.assigneePresetId
          ? t("channelTasks.toasts.unclaimed")
          : t("channelTasks.toasts.claimed"),
      );
    } catch (error) {
      console.error("[ChannelTasks] claim toggle failed", error);
      toast.error(t("channelTasks.toasts.claimFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  const handleStatusChange = async (status: ChannelTaskStatus) => {
    if (!taskId || !task) {
      return;
    }
    setIsSaving(true);
    try {
      const nextTask = await channelTasksApi.updateTaskStatus(
        serverId,
        channelId,
        taskId,
        {
          status,
          position: task.position,
        },
      );
      syncTask(nextTask);
      await loadTask();
      toast.success(t("channelTasks.toasts.statusUpdated"));
    } catch (error) {
      console.error("[ChannelTasks] status update failed", error);
      toast.error(t("channelTasks.toasts.statusFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-hidden sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>{t("channelTasks.detail.title")}</DialogTitle>
          <DialogDescription>
            {t("channelTasks.detail.description")}
          </DialogDescription>
        </DialogHeader>

        {isLoading || !task ? (
          <div className="space-y-4">
            <Skeleton className="h-10 rounded-xl" />
            <Skeleton className="h-32 rounded-2xl" />
            <Skeleton className="h-48 rounded-2xl" />
          </div>
        ) : (
          <div className="grid gap-6 overflow-y-auto pr-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
            <section className="space-y-4">
              <div className="rounded-3xl border border-border/70 bg-card p-5">
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <p className="text-sm font-semibold text-foreground">
                      {t("channelTasks.detail.overview")}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {t("channelTasks.detail.overviewDescription")}
                    </p>
                  </div>
                  <Input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                  />
                  <Textarea
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    rows={6}
                    className="rounded-2xl border-border/60 bg-background/80 shadow-none"
                  />
                  <div className="flex flex-wrap gap-2">
                    {(
                      ["todo", "in_progress", "in_review", "done"] as const
                    ).map((status) => (
                      <Button
                        key={status}
                        type="button"
                        variant={task.status === status ? "default" : "outline"}
                        size="sm"
                        disabled={isSaving}
                        onClick={() => void handleStatusChange(status)}
                      >
                        <StatusIcon status={status} />
                        {t(`channelTasks.statuses.${status}`)}
                      </Button>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      onClick={() => void handleSave()}
                      disabled={isSaving}
                    >
                      <Save className="size-4" />
                      {t("channelTasks.actions.save")}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => void handleClaimToggle()}
                      disabled={isSaving}
                    >
                      {task.assigneeUserId || task.assigneePresetId
                        ? t("channelTasks.actions.unclaim")
                        : t("channelTasks.actions.claim")}
                    </Button>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-border/70 bg-card p-5">
                <div className="space-y-1.5">
                  <p className="text-sm font-semibold text-foreground">
                    {t("channelTasks.detail.activity")}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t("channelTasks.detail.activityDescription")}
                  </p>
                </div>
                <div className="mt-4 space-y-3">
                  {activity.length > 0 ? (
                    activity.map((message) => (
                      <ActivityItem key={message.messageId} message={message} />
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      {t("channelTasks.detail.emptyActivity")}
                    </p>
                  )}
                </div>
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-3xl border border-border/70 bg-card p-5">
                <div className="space-y-1.5">
                  <p className="text-sm font-semibold text-foreground">
                    {t("channelTasks.detail.execution")}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t("channelTasks.detail.executionDescription")}
                  </p>
                </div>
                <div className="mt-4 rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-5">
                  <p className="text-sm text-foreground">
                    {t("channelTasks.detail.executionPlaceholder")}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge variant="secondary">
                      {t("channelTasks.detail.currentStatus", {
                        status: t(`channelTasks.statuses.${task.status}`),
                      })}
                    </Badge>
                    <Badge variant="outline">
                      {task.assigneeUserId || task.assigneePresetId
                        ? t("channelTasks.detail.assigneeAttached")
                        : t("channelTasks.detail.assigneePending")}
                    </Badge>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
