# Server channel UX follow-ups plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-08 |
| **预期改动范围** | frontend server conversation page / message row actions / drawer behavior / execution container reuse / i18n / targeted frontend tests |
| **改动类型** | fix |
| **优先级** | P1 |
| **状态** | in-progress |

## 实施阶段

- [x] Phase 0: 收敛问题列表、现状约束与提交边界 (2026-05-08)
- [x] Phase 1: 修复频道消息区基础交互 (2026-05-08)
- [x] Phase 2: 修复消息卡片动作与 colleague 跳转 (2026-05-08)
- [x] Phase 3: 修复 execution drawer 进入态与终止操作 (2026-05-08)
- [x] Phase 4: 验证、回写 spec 状态并分阶段提交 (2026-05-08)

## 实现记录

- 2026-05-08: 基于四份 constitution 文档重新梳理频道 UX 后续修复，范围聚焦在 server channel 前端体验，不改动频道共享边界、execution placeholder 契约和 channel-scoped tool 注入模型。
- 2026-05-08: 当前工作分支为 `fix/channel-ux-followups`，后续提交按 phase 聚合，避免把消息流交互、execution drawer 行为和文档更新混成一个提交。
- 2026-05-08: Phase 1 已完成：频道主消息区补齐首次滚底、跟随新消息时的自动滚底和“回到底部”按钮；主频道与 thread drawer 输入框改为 Enter 发送、Shift + Enter 换行；`As Task` 不再主动切到 tasks 视图，并在具备 agent 协作意图时补 user follow-up 以承接现有 mention 触发链路。
- 2026-05-08: Phase 2 已完成：频道消息卡片动作区补齐复制按钮并去掉外层描边；agent execution / agent session 消息的头像现在都能回到对应 execution drawer；colleagues 与 colleague detail 在 agent 处于 active 且能解析到 session 对应频道时，支持直接跳回相关 channel。
- 2026-05-08: Phase 3 已完成：server channel 进入 execution drawer 时默认收起右侧 computer / artifacts 面板，并隐藏更偏普通聊天语义的 preset badge；终止按钮继续复用既有 `cancelSessionAction -> /sessions/{id}/cancel` 链路，无需新增 server 专用 cancel API。
- 2026-05-08: Phase 4 已完成：已通过 `cd frontend && node --test --experimental-strip-types --experimental-specifier-resolution=node features/servers/lib/server-conversation-messages.test.ts`、`cd frontend && pnpm lint`、`cd frontend && pnpm build` 验证。本仓库当前 `pnpm test` 全量脚本仍存在既有失败（与本次改动无关），包括 alias 解析失败和 `features/workspaces/lib/team-sections.test.ts` 的基线断言失败，因此本轮仅把新增/相关验证作为交付门槛。

---

## 背景

### 问题陈述

频道页第一轮实现已经把 `thread drawer`、`execution drawer`、`shared artifacts drawer` 和 `colleagues` 视图接起来了，但实际交互还存在几类明显断层：

- 频道消息区没有复用普通聊天页的滚动心智，进入频道后不会自动滚到底部，也没有“滚动到底部”按钮。
- 频道输入框与 thread 输入框没有复用普通聊天页的 Enter 发送语义，当前默认只能点击发送。
- 把一条消息转成 task 时会主动切到 tasks 视图，这和“留在当前频道继续看 agent 输出”的协作预期相冲突。
- execution placeholder 点击后能打开 drawer，但 drawer 默认展开 computer / artifacts 侧栏，且仍保留对普通聊天更有意义的身份信息 badge，没有针对频道协作做收口。
- execution placeholder 之外，agent 的普通频道消息缺少稳定的“回到对应执行过程”入口；用户希望点击 agent 头像后也能再次展开这次工作的具体过程。
- colleagues 里 agent 显示为 active 时，当前仍然不能直接跳回它对应的频道上下文。

这些问题都不需要重开 constitution 层面的设计讨论，但它们直接影响频道协作是否“像聊天”，以及 execution observability 是否真的可用。

### 目标

这份计划的目标是用一轮前端 follow-up 修复把频道页体验收口到更稳定的产品状态，重点包括：

- 频道消息区复用普通聊天页的自动滚底与“滚到底部”按钮心智
- 输入框回车默认发送，保留 `Shift + Enter` 换行
- 创建 channel task 后保持留在当前频道，不主动切换 tasks 视图
- 消息卡片动作区补齐复制按钮，并让按钮样式靠近普通聊天页
- 为 execution placeholder、agent session 消息和 agent 头像提供统一的 execution 打开入口
- execution drawer 默认收起右侧 computer / artifacts 面板，同时保留终止能力
- colleague 为 active 时，支持跳回与其相关的频道上下文

### 非目标

以下内容不在本次范围内：

- 不重做频道 execution placeholder 的后端数据模型
- 不改动 shared artifacts 的发布边界或 channel artifact tool 协议
- 不把频道主消息流直接改造成完整 execution transcript
- 不新增 websocket / SSE 实时链路
- 不新增新的 backend session cancellation API，只复用现有 cancel session 链路

### 关键约束

#### 1. 频道页必须继续复用既有 execution 体系

`ExecutionContainer`、`cancelSessionAction` 和 `sessions/{id}/cancel` 已经存在。本轮需要做的是 server 页面适配，不是再造一套执行视图。

#### 2. 频道消息流里只能放紧凑入口，不能把完整历史塞回主流

constitution 已经明确：主消息流放 compact execution item，完整 session 细节进入 drawer。本轮补的是“更多地方能回到这条执行链路”，不是把内部 transcript 重叠渲染到频道流里。

#### 3. 创建 task 后的留在原地，比自动切视图更重要

频道协作的核心是连续对话。把消息转成 task 是附加结构化动作，不应打断用户继续看消息流和 agent 输出。

---

## Phase 0: 收敛问题列表、现状约束与提交边界

### 目标

先把这轮修复和现有决策记录对齐，并明确每个 phase 对应的提交边界。

### 任务清单

#### 0.1 对齐相关 constitution

**描述：** 以以下文档作为实现约束：

- `specs/constitution/2026-05-05-channel-shared-context-and-artifacts.md`
- `specs/constitution/2026-05-06-server-agent-observability-tasks-and-persistence.md`
- `specs/constitution/2026-05-07-agent-dispatch-latency-optimization.md`
- `specs/constitution/2026-05-08-persistent-agent-message-passing-and-tool-injection.md`

**验收标准：**

- [x] spec 明确本轮不改共享边界和 trigger 协议
- [x] spec 明确 execution drawer 仍复用现有 session 视图

#### 0.2 明确提交边界

**描述：** 本轮提交按以下边界组织：

- Phase 1: 基础交互
- Phase 2: 消息卡片动作与跳转
- Phase 3: execution drawer 收口

**验收标准：**

- [x] spec 中的 phase 可直接映射到 commit 主题

---

## Phase 1: 修复频道消息区基础交互

### 目标

让频道主消息区和 thread drawer 在滚动、输入和 task 创建行为上贴近普通聊天页。

### 任务清单

#### 1.1 补齐自动滚底与滚底按钮

**描述：** 频道页进入时自动滚到最新消息；当用户离开底部后，出现和普通聊天页一致的“滚动到底部”按钮。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- 如有需要：新增 `frontend/features/servers/lib/` 下的滚动辅助逻辑

**验收标准：**

- [x] 首次进入频道会滚到底部
- [x] 新消息到达时，用户位于底部附近会自动跟随
- [x] 用户上滑后会出现滚底按钮，点击后回到底部

#### 1.2 补齐 Enter 发送语义

**描述：** 频道输入框和 thread 输入框默认 `Enter` 发送，`Shift + Enter` 换行；mention 候选弹层打开时继续优先处理 mention 选择。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`

**验收标准：**

- [x] 频道输入框按 Enter 会发送
- [x] thread 输入框按 Enter 会发送
- [x] `Shift + Enter` 仍然换行
- [x] mention 面板打开时 Enter 仍然优先插入 mention

#### 1.3 调整创建 task 后的留在原地行为

**描述：** `As Task` 创建成功后不主动切到 tasks 视图；主频道和 thread drawer 都保持停留在当前上下文，只刷新需要的 task / message 数据。若当前草稿本身承载了 agent 协作意图，则应继续落一条会触发现有 mention 链路的 user reply，避免“建成 task 但没有 agent 输出”的断层。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`

**验收标准：**

- [x] 主频道 `As Task` 成功后不切走当前视图
- [x] thread `As Task` 成功后不切走当前 drawer
- [x] 相关 task 数据仍然会刷新
- [x] 带 agent 协作意图的 task 草稿仍能承接后续 agent 输出

---

## Phase 2: 修复消息卡片动作与 colleague 跳转

### 目标

统一频道消息卡片的快捷操作，并让 agent 相关入口都能回到对应执行过程或频道上下文。

### 任务清单

#### 2.1 补齐复制按钮并统一动作样式

**描述：** agent 消息右上角改成三个按钮，最左侧新增复制消息；按钮样式向普通聊天页靠齐，移除外层描边，hover 时只改变按钮自身颜色和背景。

**涉及文件：**

- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [x] 消息卡片有复制 / thread / save 三个动作
- [x] 按钮无外层 border，hover 态更贴近普通聊天页
- [x] 复制成功和失败有稳定反馈

#### 2.2 统一 execution 打开入口

**描述：** 除 execution placeholder 本体外，点击 agent 头像时也应能打开对应 session 的 execution drawer。优先支持带 `session_id` 的频道 system message，包括 `agent_execution` 和 `agent_session` 两类。

**涉及文件：**

- `frontend/features/servers/ui/conversation-message-row.tsx`
- 如有需要：新增 `frontend/features/servers/lib/server-conversation-messages.ts`

**验收标准：**

- [x] execution placeholder 点击卡片可打开 execution drawer
- [x] 带 `session_id` 的 agent 消息点击头像可打开 execution drawer
- [x] 普通用户消息不受影响

#### 2.3 让 active colleague 支持跳回频道

**描述：** colleague 为 active 时，显示可点击跳转入口，优先跳到该 agent 当前 active session 所在的频道；如果缺少必要上下文，则保持禁用。

**涉及文件：**

- `frontend/features/servers/ui/colleagues-panel.tsx`
- `frontend/features/servers/ui/colleague-detail.tsx`
- `frontend/features/servers/model/types.ts`

**验收标准：**

- [x] active agent 在 colleagues 中有明确可点击入口
- [x] 点击后能跳回对应 channel conversation
- [x] 缺少 active channel 线索时不会误跳转

---

## Phase 3: 修复 execution drawer 进入态与终止操作

### 目标

让频道里的 execution drawer 更像“从频道里查看一次工作过程”，而不是完全复用普通聊天页默认面板状态。

### 任务清单

#### 3.1 默认收起右侧 computer / artifacts 区

**描述：** 从频道进入 execution drawer 时，默认关闭右侧 computer / artifacts 面板，但保留用户手动展开能力。

**涉及文件：**

- `frontend/features/chat/components/layout/execution-container.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`

**验收标准：**

- [x] 频道 execution drawer 默认只显示主 chat panel
- [x] 用户仍可手动打开右侧 panel
- [x] 普通聊天页默认行为不被破坏

#### 3.2 移除频道 execution drawer 中的身份 badge

**描述：** 频道 execution drawer 中隐藏更偏普通聊天语义的身份 / preset badge，保留必要的运行状态和终止入口。

**涉及文件：**

- `frontend/features/chat/components/execution/chat-panel/chat-panel.tsx`
- `frontend/features/chat/components/execution/chat-panel/status-bar.tsx`
- `frontend/features/servers/ui/conversation-drawers.tsx`

**验收标准：**

- [x] 从频道进入 execution drawer 时不显示身份 badge
- [x] 普通聊天页原有 badge 行为不被破坏

#### 3.3 保留并验证终止链路

**描述：** 在频道 execution drawer 中保留终止按钮，并确认继续复用现有 `cancelSessionAction -> /sessions/{id}/cancel` 链路。

**涉及文件：**

- `frontend/features/chat/components/execution/chat-panel/chat-panel.tsx`
- `frontend/features/chat/actions/session-actions.ts`
- `backend/app/api/v1/sessions.py`（只做链路确认，不预期改动）

**验收标准：**

- [x] 频道 execution drawer 可见终止按钮
- [x] 点击后 session 状态进入 `canceling`
- [x] 不需要新增专门的 server-side cancel API

---

## Phase 4: 验证、回写 spec 状态并分阶段提交

### 目标

完成前端验证、同步更新 spec todo，并按阶段生成 commit message 与提交。

### 任务清单

#### 4.1 补最小验证

**描述：** 至少覆盖相关前端单测和静态检查；如涉及可提炼的纯逻辑，补对应 `.test.ts`。

**涉及文件：**

- `frontend/features/servers/**/*.test.ts`
- `frontend/package.json`

**验收标准：**

- [x] 相关前端测试通过
- [x] `cd frontend && pnpm lint` 通过

#### 4.2 同步更新 spec todo

**描述：** 每完成一个 phase，对应勾选阶段和验收项，并在“实现记录”补充日期与结果。

**验收标准：**

- [x] spec 的 phase 状态与代码实际进度一致

#### 4.3 生成 COMMIT.md 并提交

**描述：** 每次提交前仅基于 staged diff 运行 `staged-commit-message` 流程，覆盖写入根目录 `COMMIT.md`，然后提交。

**验收标准：**

- [x] 每个 commit 都有对应的 staged-only `COMMIT.md`
- [x] commit 主题与 spec phase 边界一致
