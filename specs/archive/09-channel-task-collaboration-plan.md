# Channel task collaboration workflow plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-04 |
| **预期改动范围** | backend task models / task APIs / frontend channel task views / kanban/list UX / i18n copy / tests |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 收敛 task 模型与旧 issue 的替代边界 (2026-05-04)
- [x] Phase 1: 建立 channel-native task 数据契约与 API (2026-05-04)
- [x] Phase 2: 建立频道内 board/list 双视图 (2026-05-04)
- [x] Phase 3: 建立 task detail、认领与 system message 协作流 (2026-05-04)
- [x] Phase 4: 验收与旧 issue 入口收口 (2026-05-04, pending user acceptance)

---

## 背景

### 问题陈述

`08-server-channel-foundation-plan.md` 解决的是新的协作地基，但它本身不会自动把“团队工作项”迁到 channel 里。当前代码里承担工作项职责的仍然是：

- `workspace_issue`
- `workspace_board`
- `agent_assignment`
- team issues 页中的 kanban 视图

这套设计已经为旧的 workspace/team 模型跑通了一轮看板与 AI assignee 体验，但它和新的产品主线存在结构冲突：用户希望 task 是 channel 中的可讨论对象，task 的状态变化是频道协作事件，而不是一个独立的 issue 页面对象。

因此，需要一份单独的 task collaboration spec，把旧的 issue/board 能力重新组织成：

- channel 中的 task
- 固定四阶段 workflow
- 聊天视图与看板视图双表示
- task detail 与认领 / 状态流转 / agent 状态的统一交互

### 目标

本计划的目标是建立新的 task 协作工作流，并让它成为 channel 的一部分，而不是继续依附于旧 board 页面。重点包括：

- 定义 channel-native task 的数据契约
- 固定 `todo -> in_progress -> in_review -> done` 四阶段状态流
- 让 task 同时存在于消息流和看板视图中
- 让认领、状态更新、system message 广播、task detail 在同一语义下闭环

### 关键洞察

#### 1. task 必须是 channel 对象，而不是仅在 channel 里“引用一个 issue”

如果只是把旧 issue 卡片嵌进 channel 页面，新的协作模型仍然会被旧 issue 主线牵着走。task 需要在数据模型和页面结构上都成为 channel-native 对象。

#### 2. 看板要保留，但它是 task 的视图，不再是独立上下文

看板仍然有价值，但它应该成为 channel 下 task 的一种可视化视图，而不是继续承担 board 作为独立组织层的职责。

#### 3. 旧的 issue 资产可以在实现层迁移或投影，但不应继续作为产品主语

当前 `workspace_issue` 和相关 frontend kanban 逻辑能提供部分实现基础，但本 spec 的目标是让新的外部心智变成 task，而不是再造一层 issue 别名。

---

## Phase 0: 收敛 task 模型与旧 issue 的替代边界

### 目标

先明确新 task 到底替代旧 issue 的哪些职责，以及哪些旧资产只作为迁移时的实现参考。

### 任务清单

#### 0.1 定义 task 的最小字段集

**描述：** 明确 MVP 中 task 需要承载的最小语义，避免把旧 issue 的所有字段、board 自定义字段和执行状态一次性都塞进第一版。

**MVP task 至少包含：**

- title
- description / rich content
- status
- assignee（人或 agent）
- creator
- reporter（可选）
- related_project_id（可选）
- priority（可选）
- due_date（可选）
- thread root / reply relationship

**当前实现说明：**

- 后端新增 `server_channel_tasks` 表与 `thread_root_message_id` 锚点，task 直接归属于 `server/channel`
- assignee 继续复用 `user` / `preset(agent)` 双模，但不复用 `agent_assignment` 作为 task 主表
- MVP 不纳入旧 issue 的 `type`、独立 `board_id`、`workspace_id`、自定义字段和值表，也不把执行 session 状态并入 task 主字段

**验收标准：**

- [x] spec 中明确 task 的最小字段集
- [x] spec 中明确哪些旧 issue 字段不进入 MVP

#### 0.2 定义旧 issue 的替代边界

**描述：** 新 task 成为产品主语后，旧 `workspace_issue` 在实现中的角色必须被明确限制，避免双模型长期并行扩张。

**验收标准：**

- [x] spec 中明确 task 是新的产品主语
- [x] spec 中明确旧 issue 在 MVP 里若被复用，也仅为过渡实现资产

---

## Phase 1: 建立 channel-native task 数据契约与 API

### 目标

为 channel task 建立清晰的后端模型与 API，而不是继续沿用零散的 issue PATCH 语义。

### 任务清单

#### 1.1 建立 task 模型与 repository/service

**描述：** 在 channel/message 基础层之上建立 task 模型，支持状态流、认领、关联项目和 assignee 语义。

**涉及文件：**

- `backend/app/models/workspace_issue.py` — 评估复用或迁移
- `backend/app/models/workspace_board.py`
- `backend/app/models/agent_assignment.py`
- `backend/app/models/` — 新增 task 相关模型
- `backend/app/repositories/workspace_issue_repository.py`
- `backend/app/repositories/agent_assignment_repository.py`
- `backend/app/services/workspace_issue_service.py`
- `backend/app/services/agent_assignment_service.py`
- `backend/app/schemas/workspace_issue.py`
- `backend/app/schemas/agent_assignment.py`
- 新的 task repository / service / schema

**实现记录：**

- 新增 `backend/app/models/server_channel_task.py`
- 新增 `backend/app/repositories/server_channel_task_repository.py`
- 新增 `backend/app/services/server_channel_task_service.py`
- 新增 `backend/app/schemas/server_channel_task.py`
- 迁移脚本：`backend/alembic/versions/5dabd02f9e77_add_server_channel_tasks.py`

**验收标准：**

- [x] task 有独立的数据契约和 service 边界
- [x] task 支持固定四阶段状态流
- [x] task assignee 支持人类与 agent 双模但保持互斥

#### 1.2 建立 task API

**描述：** 明确 task 的创建、读取、认领、状态更新、详情读取、按 channel 查询与 board/list 投影 API。

**涉及文件：**

- `backend/app/api/v1/` — 新增 channel tasks 相关入口
- `backend/app/schemas/`
- `backend/app/services/`

**实现记录：** 新增 `/servers/{server_id}/channels/{channel_id}/tasks` 路由，提供 create / list / detail / patch / claim / unclaim / update-status。

**验收标准：**

- [x] 存在 task create / list / detail / claim / update-status API
- [x] 读取 channel task 时，不需要通过旧 issue 路由绕行

#### 1.3 建立 task system message 广播协议

**描述：** task 的创建、认领、状态流转和完成结果，必须通过 channel system message 广播给协作面，而不是只改 task 表状态。

**实现记录：** task 创建会写入顶层 `task` message 作为 thread root；claim / unclaim / status change 会在同一 thread 下追加 `system` message。

**验收标准：**

- [x] task 状态变化会产生可读的 system message
- [x] 认领和完成结果在频道中可追溯

---

## Phase 2: 建立频道内 board/list 双视图

### 目标

让用户在同一个 channel 内切换 task 的聊天流视图和看板视图，而不是离开频道再进入独立 issue 页面。

### 任务清单

#### 2.1 建立 channel task list 视图

**描述：** list 视图负责按时间或筛选条件浏览当前 channel 的 task，强调上下文和讨论关系。

**涉及文件：**

- `frontend/features/issues/*` — 评估迁移与复用
- `frontend/features/chat/*`
- 新的 `frontend/features/channels/*`、`frontend/features/tasks/*`（如采用）
- `frontend/components/shared/page-header-shell.tsx`

**实现记录：**

- 新增 `frontend/features/channel-tasks/*` feature，按 `api / model / lib / ui` 分层承接 channel task 页面
- 新增 `frontend/app/[lng]/(shell)/servers/[serverId]/channels/[channelId]/page.tsx`
- server 页的 channel 卡片直接进入 channel task 页面，不再停留在静态目录页

**验收标准：**

- [x] 用户可在 channel 内按列表浏览 task
- [x] task 与线程/消息上下文可联动查看

#### 2.2 建立 channel task board 视图

**描述：** 在 channel 内保留 board 视图，但它仅负责按固定四状态展示 task，不再作为独立领域对象。

**可复用参考：**

- `frontend/features/issues/ui/team-kanban-board.tsx`
- `frontend/features/issues/lib/kanban-columns.ts`
- `specs/draft/07-workspace-team-kanban-board-rebuild-plan.md`

**实现记录：** 新页面保留固定四列 board，并通过原生拖拽 + `update-status` API 完成跨列与列内排序。

**验收标准：**

- [x] board 视图按 `todo / in_progress / in_review / done` 展示 task
- [x] task 可拖拽变更状态与顺序
- [x] board 视图属于 channel，不再要求先选独立 board 实体

#### 2.3 定义 board/list 切换与 URL 语义

**描述：** 统一视图切换方式，避免旧 team/issues 页面和新 channel 页各自使用不同的导航模型。

**实现记录：** 当前 channel 页使用 `view=list|board` query state 驱动视图切换，URL 语义落在 `server/channel` 路径下。

**验收标准：**

- [x] 同一 channel 内可以切换 board / list
- [x] URL、query state 或内部 state 语义在产品层清晰一致

---

## Phase 3: 建立 task detail、认领与 system message 协作流

### 目标

让 task 的处理过程在频道中具备完整的协作闭环，而不只是一个能改状态的卡片。

### 任务清单

#### 3.1 建立 task detail 结构

**描述：** task detail 必须统一承接描述、关联项目、assignee、状态流、system activity 和后续 agent execution 入口。

**涉及文件：**

- `frontend/features/issues/ui/team-issue-detail-content.tsx`
- `frontend/features/issues/ui/team-issue-detail-dialog.tsx`
- `frontend/features/issues/lib/issue-detail-view.ts`
- 新的 task detail 组件

**实现记录：**

- 新增 `frontend/features/channel-tasks/ui/channel-task-detail-dialog.tsx`
- detail 通过 `task=<taskId>` query state 叠加在 channel 页面上，不脱离当前频道
- detail 内已接入 task patch、claim / unclaim、status update 与 thread activity 展示

**验收标准：**

- [x] task detail 支持 overview / collaboration activity / execution summary 分区
- [x] detail 与 channel 上下文不脱离

#### 3.2 定义 claim / unclaim / review 流程

**描述：** 与旧 issue 相比，新 task 更强调频道协作，因此 claim 和 `in_review` 阶段要成为明确协议，而不是普通字段更新。

**实现记录：** detail 内的认领按钮直接走 `claim / unclaim` API；状态切换包含 `in_review`，并在刷新 thread activity 后展示对应 system message。

**验收标准：**

- [x] claim 动作会更新 assignee 并广播 system message
- [x] `in_review` 具有明确的产品语义和交互入口
- [x] 一个 task 在任意时刻只有一个活跃 assignee

#### 3.3 连接后续 agent execution 入口

**描述：** 当前 spec 不深入定义 agent runtime，但 task detail 需要为后续 `agent identity + persistent runtime` 留出稳定挂点。

**实现记录：** detail 中新增 `execution summary` 区块，当前先展示占位说明、当前状态和 assignee 绑定状态，为后续 runtime 接入保留稳定位置。

**验收标准：**

- [x] task detail 预留 execution summary / runtime state 位置
- [x] 新的 execution 入口不需要重新回到旧 issue 页面

---

## Phase 4: 验收与旧 issue 入口收口

### 目标

在新 task 流程可用后，限制旧 issue 继续作为产品层主入口扩展。

### 任务清单

#### 4.1 收口旧 issues 页面职责

**描述：** `frontend/features/issues/*` 和相关 backend issue API 在新主线稳定后，必须被明确收口：要么迁入新 task 模块，要么标记为过渡层。

**实现记录：**

- `frontend/app/[lng]/(shell)/team/issues/page.tsx` 现在直接重定向到 `/${lng}/servers`
- `frontend/features/workspaces/ui/team-library-shell.tsx` 的 rail footer 不再暴露旧 board 列表，改为引导用户进入新的 server/channel task 页面
- 旧 `frontend/features/issues/*` 当前保留为过渡实现资产，不再作为新增 channel task 需求的默认落点

**验收标准：**

- [x] 新增协作需求不再默认落到旧 issue 页面
- [x] 旧 issue 相关 spec 的剩余有效部分被记录

#### 4.2 补齐测试与引用更新

**描述：** 为 task API、board/list 视图、认领状态流和 system message 补齐基础测试。

**实现记录：**

- backend: `uv run python -m unittest tests.test_server_channel_task_service tests.test_server_channel_task_api`
- frontend targeted: `pnpm exec node --test --experimental-strip-types --experimental-specifier-resolution=node features/channel-tasks/lib/channel-task-board.test.ts`
- frontend global checks: `pnpm lint`、`pnpm build`
- 说明：`pnpm test` 全量套件仍有仓库内既有失败，主要是 `features/projects/actions/project-actions.test.ts` 与 `features/task-composer/api/task-submit-api.test.ts` 的 alias 解析问题，以及 `features/workspaces/lib/team-sections.test.ts` 的既有断言不一致；本轮新增的 channel task 用例已通过

**验收标准：**

- [x] task model / API / frontend view 有最小测试覆盖
- [x] 与 `07` 的可复用部分和替代关系被注明

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 新 task 和旧 issue 长期双轨发展 | 用户和开发者都不知道哪个才是主语 | 在 Phase 0 和 Phase 4 明确 task 为产品主语，issue 仅保留过渡实现角色 |
| 看板视图失去上下文，重新长成独立 board 页面 | 又回到旧模型 | 把 board/list 统一绑定在 channel 下，禁止独立 board 主入口 |
| `in_review` 只是新增枚举，没有协作语义 | 状态增多但产品价值不清晰 | 在 Phase 3 明确定义 review 阶段的 claim/交付语义和 system message 广播 |

---

## 总结

这份 spec 的目标是把“任务”真正拉回协作主舞台。完成后，用户在 Poco 里推进工作将不再主要依赖旧 issue 页面，而是围绕 channel 中的 task、线程讨论、认领流转和看板视图展开。
