import type {
  ChannelTask,
  ChannelTaskStatus,
  ChannelTaskView,
} from "../model/types";

export const CHANNEL_TASK_STATUS_ORDER: ChannelTaskStatus[] = [
  "todo",
  "in_progress",
  "in_review",
  "done",
];

export function resolveChannelTaskView(
  value: string | null | undefined,
): ChannelTaskView {
  return value === "list" ? "list" : "board";
}

export function buildChannelTaskColumns(
  tasks: ChannelTask[],
): Array<{ status: ChannelTaskStatus; tasks: ChannelTask[] }> {
  return CHANNEL_TASK_STATUS_ORDER.map((status) => ({
    status,
    tasks: tasks
      .filter((task) => task.status === status)
      .sort((left, right) => {
        if (left.position !== right.position) {
          return left.position - right.position;
        }
        return Date.parse(right.updatedAt) - Date.parse(left.updatedAt);
      }),
  }));
}

export function moveChannelTask(
  tasks: ChannelTask[],
  move: {
    taskId: string;
    status: ChannelTaskStatus;
    position: number;
  },
): ChannelTask[] {
  const sourceTask = tasks.find((task) => task.taskId === move.taskId);
  if (!sourceTask) {
    return tasks;
  }

  const grouped = new Map<ChannelTaskStatus, ChannelTask[]>(
    CHANNEL_TASK_STATUS_ORDER.map((status) => [status, []]),
  );

  for (const task of tasks.map((item) => ({ ...item }))) {
    grouped.get(task.status)?.push(task);
  }

  const sourceColumn = grouped.get(sourceTask.status);
  const targetColumn = grouped.get(move.status);
  if (!sourceColumn || !targetColumn) {
    return tasks;
  }

  const sourceIndex = sourceColumn.findIndex(
    (task) => task.taskId === move.taskId,
  );
  if (sourceIndex === -1) {
    return tasks;
  }

  const [movedTask] = sourceColumn.splice(sourceIndex, 1);
  const targetIndex = Math.max(0, Math.min(move.position, targetColumn.length));

  if (sourceTask.status === move.status && sourceIndex === targetIndex) {
    return tasks;
  }

  movedTask.status = move.status;
  targetColumn.splice(targetIndex, 0, movedTask);

  return CHANNEL_TASK_STATUS_ORDER.flatMap((status) =>
    (grouped.get(status) ?? []).map((task, index) => ({
      ...task,
      status,
      position: index,
    })),
  );
}

export function buildChannelTaskListGroups(
  tasks: ChannelTask[],
): Array<{ status: ChannelTaskStatus; tasks: ChannelTask[] }> {
  return CHANNEL_TASK_STATUS_ORDER.map((status) => ({
    status,
    tasks: tasks
      .filter((task) => task.status === status)
      .sort((left, right) => {
        const rightTimestamp = Date.parse(right.updatedAt);
        const leftTimestamp = Date.parse(left.updatedAt);
        return rightTimestamp - leftTimestamp;
      }),
  })).filter((group) => group.tasks.length > 0);
}
