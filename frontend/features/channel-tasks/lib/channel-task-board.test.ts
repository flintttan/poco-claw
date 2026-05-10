import assert from "node:assert/strict";
import test from "node:test";

import type { ChannelTask } from "../model/types";
import {
  CHANNEL_TASK_STATUS_ORDER,
  buildChannelTaskColumns,
  buildChannelTaskListGroups,
  moveChannelTask,
  resolveChannelTaskView,
} from "./channel-task-board.ts";

function createTask(overrides: Partial<ChannelTask> = {}): ChannelTask {
  return {
    taskId: "task-1",
    serverId: "server-1",
    channelId: "channel-1",
    title: "Refine collaboration board",
    description: "Keep channel task ordering stable",
    status: "todo",
    position: 0,
    priority: "medium",
    dueDate: null,
    assigneeUserId: null,
    assigneePresetId: null,
    reporterUserId: null,
    relatedProjectId: null,
    creatorUserId: "user-1",
    updatedBy: "user-1",
    threadRootMessageId: "message-1",
    createdAt: "2026-05-04T10:00:00Z",
    updatedAt: "2026-05-04T10:00:00Z",
    ...overrides,
  };
}

test("resolveChannelTaskView falls back to board for unsupported values", () => {
  assert.equal(resolveChannelTaskView("board"), "board");
  assert.equal(resolveChannelTaskView("list"), "list");
  assert.equal(resolveChannelTaskView("timeline"), "board");
  assert.equal(resolveChannelTaskView(undefined), "board");
});

test("buildChannelTaskColumns keeps the fixed workflow order", () => {
  const columns = buildChannelTaskColumns([
    createTask({ taskId: "task-1", status: "done", position: 0 }),
    createTask({ taskId: "task-2", status: "todo", position: 1 }),
    createTask({ taskId: "task-3", status: "in_progress", position: 0 }),
  ]);

  assert.deepEqual(
    columns.map((column) => column.status),
    CHANNEL_TASK_STATUS_ORDER,
  );
});

test("moveChannelTask resequences tasks across statuses", () => {
  const nextTasks = moveChannelTask(
    [
      createTask({ taskId: "task-1", status: "todo", position: 0 }),
      createTask({ taskId: "task-2", status: "todo", position: 1 }),
      createTask({ taskId: "task-3", status: "in_review", position: 0 }),
    ],
    {
      taskId: "task-2",
      status: "in_review",
      position: 0,
    },
  );

  assert.deepEqual(
    buildChannelTaskColumns(nextTasks)
      .find((column) => column.status === "todo")
      ?.tasks.map((task) => `${task.taskId}:${task.position}`),
    ["task-1:0"],
  );
  assert.deepEqual(
    buildChannelTaskColumns(nextTasks)
      .find((column) => column.status === "in_review")
      ?.tasks.map((task) => `${task.taskId}:${task.position}`),
    ["task-2:0", "task-3:1"],
  );
});

test("buildChannelTaskListGroups omits empty statuses while keeping workflow order", () => {
  const groups = buildChannelTaskListGroups([
    createTask({ taskId: "task-1", status: "done" }),
    createTask({ taskId: "task-2", status: "todo" }),
  ]);

  assert.deepEqual(
    groups.map((group) => group.status),
    ["todo", "done"],
  );
});
