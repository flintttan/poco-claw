"use client";

import { LayoutGrid, LayoutList } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  buildChannelTaskColumns,
  buildChannelTaskListGroups,
} from "@/features/channel-tasks/lib/channel-task-board";
import type {
  ChannelTask,
  ChannelTaskView,
} from "@/features/channel-tasks/model/types";
import type { ServerChannelItem } from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";

export function ChannelTasksWorkspace({
  tasks,
  taskView,
  activeChannelId,
  topLevelChannels,
  onSelectChannel,
  onUpdateView,
  onOpenTask,
}: {
  tasks: ChannelTask[];
  taskView: ChannelTaskView;
  activeChannelId: string | null;
  topLevelChannels: ServerChannelItem[];
  onSelectChannel: (channelId: string) => void;
  onUpdateView: (view: ChannelTaskView) => void;
  onOpenTask: (taskId: string) => void;
}) {
  const { t } = useT("translation");

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden">
      <div className="grid min-w-0 grid-cols-1 items-center gap-3 border-b border-border px-6 py-4 sm:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
        <Select value={activeChannelId ?? ""} onValueChange={onSelectChannel}>
          <SelectTrigger className="min-w-0 max-w-full border-border bg-background text-sm">
            <SelectValue placeholder={t("conversationView.channels")} />
          </SelectTrigger>
          <SelectContent>
            {topLevelChannels.map((channel) => (
              <SelectItem key={channel.id} value={channel.id}>
                {channel.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="min-w-0 justify-self-start sm:justify-self-end">
          <div className="flex max-w-full items-center gap-1 overflow-x-auto rounded-md border border-border bg-card p-1">
            <Button
              type="button"
              variant={taskView === "board" ? "default" : "ghost"}
              size="sm"
              onClick={() => onUpdateView("board")}
              className="shrink-0 whitespace-nowrap"
            >
              <LayoutGrid className="size-4" />
              {t("conversationView.boardView")}
            </Button>
            <Button
              type="button"
              variant={taskView === "list" ? "default" : "ghost"}
              size="sm"
              onClick={() => onUpdateView("list")}
              className="shrink-0 whitespace-nowrap"
            >
              <LayoutList className="size-4" />
              {t("conversationView.listView")}
            </Button>
          </div>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
        {taskView === "board" ? (
          <div className="overflow-x-auto">
            <div className="grid min-w-[980px] grid-cols-4 gap-4">
              {buildChannelTaskColumns(tasks).map((column) => (
                <section
                  key={column.status}
                  className="flex min-h-[32rem] flex-col rounded-md border border-border bg-muted/10 p-3"
                >
                  <div className="mb-3 flex items-center justify-between gap-3 px-1">
                    <span className="text-sm font-semibold text-foreground">
                      {t(`channelTasks.statuses.${column.status}`)}
                    </span>
                    <span className="rounded-md border border-border bg-background px-2 py-0.5 text-xs tabular-nums text-muted-foreground">
                      {column.tasks.length}
                    </span>
                  </div>
                  <div className="min-h-0 flex-1 space-y-3">
                    {column.tasks.length > 0 ? (
                      column.tasks.map((task) => (
                        <button
                          key={task.taskId}
                          type="button"
                          onClick={() => onOpenTask(task.taskId)}
                          className="w-full rounded-md border border-border bg-card px-4 py-4 text-left transition-colors hover:bg-muted/20"
                        >
                          <p className="text-xs font-medium text-muted-foreground">
                            #{task.taskId.slice(0, 4)}
                          </p>
                          <p className="mt-2 text-base font-semibold text-foreground">
                            {task.title}
                          </p>
                          {task.description ? (
                            <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                              {task.description}
                            </p>
                          ) : null}
                        </button>
                      ))
                    ) : (
                      <div className="flex min-h-32 items-center rounded-md border border-dashed border-border bg-background/70 px-4 py-10 text-sm text-muted-foreground">
                        {t("conversationView.emptyTaskColumn", {
                          status: t(`channelTasks.statuses.${column.status}`),
                        })}
                      </div>
                    )}
                  </div>
                </section>
              ))}
            </div>
          </div>
        ) : buildChannelTaskListGroups(tasks).length > 0 ? (
          <div className="space-y-6">
            {buildChannelTaskListGroups(tasks).map((group) => (
              <section key={group.status} className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="rounded-sm bg-primary/15 px-2 py-1 text-xs font-semibold uppercase text-foreground">
                    {t(`channelTasks.statuses.${group.status}`)}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {group.tasks.length}
                  </span>
                </div>
                <div className="space-y-3">
                  {group.tasks.map((task) => (
                    <button
                      key={task.taskId}
                      type="button"
                      onClick={() => onOpenTask(task.taskId)}
                      className="w-full rounded-md border border-border bg-card px-4 py-4 text-left hover:bg-muted/20"
                    >
                      <p className="text-base font-semibold text-foreground">
                        {task.title}
                      </p>
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="flex min-h-[28rem] items-center justify-center rounded-md border border-dashed border-border bg-muted/10 px-6 py-12 text-center">
            <div className="max-w-sm space-y-2">
              <LayoutList className="mx-auto size-8 text-muted-foreground" />
              <p className="text-sm font-semibold text-foreground">
                {t("conversationView.emptyTaskListTitle")}
              </p>
              <p className="text-sm text-muted-foreground">
                {t("conversationView.emptyTaskListDescription")}
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
