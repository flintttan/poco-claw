# Agent persistent state and runtime isolation plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-04 |
| **预期改动范围** | backend agent models / backend dispatch semantics / executor_manager runtime lifecycle / executor workspace mounting / frontend agent detail UX / tests |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 收敛 agent 边界、目录结构与非目标 (2026-05-05)
- [x] Phase 1: 建立 `AgentIdentity / RuntimePreset / PersistentState` 模型边界 (2026-05-05)
- [x] Phase 2: 建立单 agent 单可写 persistent runtime 语义 (2026-05-05)
- [x] Phase 3: 建立 temporary runtime snapshot 与显式合并协议 (2026-05-05)
- [x] Phase 4: 建立前端可见性、操作入口与验收 (2026-05-05)

---

## 背景

### 问题陈述

新的 constitution 已经明确：MVP 中的 agent 不再只是一个可复用 preset 配置，而是 server / channel 协作面中的长期成员。这会立刻带来一个过去没有真正定死的问题：agent 的长期状态到底放在哪里，谁可以写，什么时候写，以及它和当前运行中的容器是什么关系。

同时，新的 chat-first 会话层需求已经单独沉淀在 `11-chat-first-channel-conversation-plan.md`：用户首先进入 channel / DM 对话，再按需把消息显式派生为 task。由于后续执行会从 `10` 开始，这份 spec 需要显式对齐那条主线，避免继续默认 “agent 主要通过 task 页面出现”。

当前 Poco 已有的相关基础主要包括：

- `backend/app/models/preset.py`：保存 prompt、skills、MCP、container_mode 等运行配置
- `backend/app/models/agent_assignment.py`：把 issue 绑定到 preset 与 session
- `executor_manager/app/services/container_pool.py`：管理 ephemeral / persistent container
- `executor/app/core/workspace.py`：在运行实例里准备工作目录和 `.claude_data`

但这套能力还没有形成“长期 agent”语义。尤其是：

- preset 同时被期待承载身份、记忆、操作流程和容器策略
- persistent container 容易被误当成长期记忆边界
- 多任务并发时，没有清晰的“谁拥有可写长期状态”的约束

在新的产品主线下，这些问题不能继续留给应用层自由发挥。否则后续 server/channel/task 协作面一旦跑起来，agent 会非常快地陷入记忆污染和运行时耦合。

### 目标

本计划的目标是为新的长期 agent 模型建立稳定边界。重点包括：

- 把身份、运行配置、持久状态和执行 runtime 明确拆开
- 定义 agent-owned 持久目录结构
- 定义“每个 agent identity 任一时刻最多一个可写 persistent runtime”
- 定义 temporary runtime 如何只读持久状态快照，并通过显式 merge 进入长期状态
- 定义 agent 如何以 channel / DM 成员身份暴露给协作面，而不是只作为 task assignee 存在

### 与 `11` 的分工

`11-chat-first-channel-conversation-plan.md` 负责定义会话主界面、三列布局、DM、thread 和 “create as task” 入口；这份 spec 负责定义 agent identity、persistent state 和 runtime 语义。两者的接口边界是：

- `11` 定义 agent 在 channel / DM 中如何被看见和被打开
- `10` 定义打开后用户能看到哪些 runtime / state 信息，以及这些状态如何被解释
- `11` 不定义 persistent runtime 规则
- `10` 不定义完整聊天布局

### 关键洞察

#### 1. 持久状态的所有者必须是 agent，而不是容器

容器是执行载体，agent 才是长期协作实体。长期知识、当前上下文和任务状态应首先属于 agent-owned state，而不是某个恰好仍然活着的容器。

#### 2. 单写者模型是早期最重要的稳定器

如果一个 agent 允许多个 runtime 共享同一份可写状态目录，`MEMORY.md`、`active-context`、工作草稿和队列状态都会立刻被并发污染。

#### 3. temporary runtime 的价值在于隔离试探性执行，而不是分享写权限

MVP 中 temporary runtime 的主要作用是做短任务、验证任务、边缘 case 检查。它应该读长期状态快照，但不应该拥有长期状态写权限。

---

## Phase 0: 收敛 agent 边界、目录结构与非目标

### 目标

先把 agent 的几个核心对象和目录结构钉死，避免后续实现时继续把东西塞回 preset。

### 任务清单

#### 0.1 定义四层对象边界

**描述：** 明确以下四层的职责，作为本计划的总边界：

- `AgentIdentity`：协作层身份
- `RuntimePreset`：执行配置
- `PersistentState`：长期状态目录
- `RuntimeContainer`：一次执行实例

**验收标准：**

- [x] spec 中明确四层边界与各自职责
- [x] spec 中明确 preset 不再承担完整 identity / memory / runtime 语义

#### 0.2 定义持久目录最小结构

**描述：** 明确 agent-owned persistent state 在 MVP 中的最小目录结构。

**建议最小结构：**

```text
agents/<agent_id>/
  profile.json
  MEMORY.md
  notes/
    key-knowledge.md
    active-context.md
  state/
    task-state.json
    channel-state.json
  artifacts/
```

**验收标准：**

- [x] spec 中明确最小目录结构
- [x] spec 中明确哪些文件属于长期状态入口

#### 0.3 明确非目标

**非目标：**

- 不在本计划中引入 daemon / local runner
- 不在本计划中做一个 agent 的多 writable runtime 并发
- 不在本计划中自动解决 memory merge 策略的所有高级场景

**验收标准：**

- [x] 非目标写明，避免后续 scope 膨胀

---

## Phase 1: 建立 `AgentIdentity / RuntimePreset / PersistentState` 模型边界

### 目标

先把数据与元数据边界建立好，为后续 runtime 生命周期和前端展示打地基。

### 任务清单

#### 1.1 建立 AgentIdentity 模型

**描述：** 引入新的协作身份实体，让 agent 成为 server/channel 内的成员，而不是仅以 preset id 被间接引用。这个身份还必须能进入 direct message 会话，成为用户直接对话的对象。

**建议字段：**

- name / handle
- display_name
- description
- avatar / visual binding
- server scope / visibility
- bound preset id
- lifecycle state

**涉及文件：**

- `backend/app/models/preset.py`
- `backend/app/models/workspace_member.py`
- `backend/app/models/` — 新增 agent identity 相关模型
- `backend/app/repositories/`
- `backend/app/schemas/`
- `backend/app/api/v1/`

**实现记录：**

- 新增 `backend/app/models/agent_identity.py`
- 新增 `backend/app/models/agent_persistent_state.py`
- 新增 `backend/app/models/server_channel_agent_member.py`
- 新增 `backend/app/services/agent_identity_service.py`
- 新增 `backend/app/api/v1/server_agents.py`

**验收标准：**

- [x] agent identity 独立于 preset 存在
- [x] agent identity 可成为 server/channel 协作成员
- [x] agent identity 可成为 DM 中的会话成员

#### 1.2 收敛 RuntimePreset 为执行配置来源

**描述：** 明确现有 `Preset` 在新主线下的职责：它仍然是 prompt、skills、MCP、模型和 container 策略的配置来源，而不是长期记忆和身份本身。

**涉及文件：**

- `backend/app/models/preset.py`
- `backend/app/services/preset_service.py`
- `frontend/features/capabilities/presets/*`

**验收标准：**

- [x] preset 的产品定位被重新定义为 runtime config
- [x] 不再继续把 identity / memory 字段直接塞回 preset 主体

#### 1.3 建立 PersistentState 元数据与文件索引

**描述：** 除了实际目录本身，后台还需要最小元数据来知道 agent 的状态目录在哪里、版本如何、最近更新时间和写入状态是什么。

**涉及文件：**

- `backend/app/models/`
- `backend/app/repositories/`
- `backend/app/schemas/`
- `executor_manager/app/services/workspace_manager.py`
- `executor/app/core/workspace.py`

**实现记录：** `executor_manager/app/services/workspace_manager.py` 已新增 `get_agent_state_dir()` 与 `create_agent_state_snapshot()`，和 backend 的 `AgentPersistentState` 元数据形成统一目录约定。

**验收标准：**

- [x] backend 能定位 agent 的持久状态目录
- [x] executor / manager 能按 agent identity 挂载该目录

---

## Phase 2: 建立单 agent 单可写 persistent runtime 语义

### 目标

把“一个 agent identity 任一时刻最多一个可写 persistent runtime”从口头约定变成可执行规则。

### 任务清单

#### 2.1 定义 persistent runtime 生命周期

**描述：** 明确 persistent runtime 的创建、复用、释放和 busy 语义。

**涉及文件：**

- `backend/app/models/agent_assignment.py`
- `backend/app/services/agent_assignment_service.py`
- `backend/app/services/session_service.py`
- `executor_manager/app/services/container_pool.py`
- `executor_manager/app/scheduler/task_dispatcher.py`

**实现记录：**

- `TaskConfig` 已新增 `agent_identity_id / channel_task_id / agent_runtime_mode`
- `AgentRuntimeService.reserve_persistent_runtime()` 在 enqueue 阶段占用单 agent 可写 runtime
- `agent_assignments` 已新增 `agent_identity_id / server_channel_task_id` 绑定字段
- `executor_manager/app/services/container_pool.py` 在 persistent 模式下按 agent 复用容器 id

**验收标准：**

- [x] 同一 agent identity 不会并发获得两个 writable persistent runtime
- [x] persistent runtime 有明确的 busy / idle / failed / retired 状态

#### 2.2 建立任务排队或改派协议

**描述：** 当同一个 agent 已有 active writable runtime 时，新任务不能静默并发进入同一可写状态目录，需要明确策略。

**MVP 可接受策略：**

- 进入 agent 内部队列
- 返回 busy 提示，要求人工改派

**实现记录：** 当前实现采用 `busy` 拒绝策略：当 persistent state 已绑定其他 active session 时，enqueue 直接返回 `Agent persistent runtime is busy`，由上层改派或稍后重试。

**验收标准：**

- [x] spec 中明确 busy 时的新任务处理策略
- [x] 不允许“多个任务共享同一可写 runtime 并发写”

#### 2.3 收敛 assignment 与 runtime 的绑定关系

**描述：** 随着 task 主线切换，assignment 不再只是“issue 绑定 preset”，而应能表达“task 绑定 agent identity 和 runtime state”。

**涉及文件：**

- `backend/app/models/agent_assignment.py`
- `backend/app/repositories/agent_assignment_repository.py`
- `backend/app/schemas/agent_assignment.py`
- `backend/app/services/agent_assignment_service.py`

**实现记录：** assignment schema/model 已预留 `agent_identity_id` 与 `server_channel_task_id`，用于表达 task 绑定 agent identity 与 runtime 归属。

**验收标准：**

- [x] assignment 能表达 agent identity 级 runtime 绑定
- [x] runtime 状态在 task detail 中可追踪

---

## Phase 3: 建立 temporary runtime snapshot 与显式合并协议

### 目标

让 temporary runtime 成为受控的只读试探性执行层，而不是长期状态的另一个写入口。

### 任务清单

#### 3.1 定义 snapshot 装载协议

**描述：** temporary runtime 启动时如何读取 persistent state，必须明确成 snapshot 语义，而不是共享可写挂载。

**涉及文件：**

- `executor_manager/app/services/workspace_manager.py`
- `executor_manager/app/services/container_pool.py`
- `executor/app/core/workspace.py`
- `executor/app/hooks/workspace.py`

**实现记录：** `ContainerPool` 已新增 agent state mount 解析：persistent 模式挂 live state 为 `rw`，temporary 模式挂 snapshot 为 `ro`，统一挂载到 `/agent_state`。

**验收标准：**

- [x] temporary runtime 读取的是 persistent state snapshot
- [x] temporary runtime 默认没有长期状态目录写权限

#### 3.2 定义 merge / promote 协议

**描述：** temporary runtime 的输出如果要进入长期状态，必须通过显式 merge 或人工确认，而不是执行结束自动写回。

**实现记录：** 当前只建立了 snapshot + read-only 挂载边界，不实现自动写回；任何 promote / merge 继续保持显式动作，避免临时执行结果静默进入长期状态。

**验收标准：**

- [x] spec 中明确 merge / promote 是显式动作
- [x] 自动执行结果不会静默污染长期记忆

#### 3.3 明确临时执行与长期知识的交互边界

**描述：** 区分“这次任务产出”与“值得进入长期 knowledge base 的结论”，避免把所有执行日志都塞进 MEMORY。

**实现记录：** 当前目录结构继续区分 `MEMORY.md`、`notes/active-context.md`、`state/task-state.json` 与 `artifacts/`，临时 runtime 只读 snapshot，不直接回写这些长期入口。

**验收标准：**

- [x] spec 中明确长期知识、当前上下文、任务草稿三类产物的归属边界

---

## Phase 4: 建立前端可见性、操作入口与验收

### 目标

让用户在协作面里能看见 agent 的长期状态与运行时状态，而不是只能从底层 session 猜测。

### 任务清单

#### 4.1 建立 agent detail / status 面板

**描述：** 在 channel 右侧上下文面板、task detail 或 agent DM profile 中展示：

- 当前绑定 preset
- 当前 persistent runtime 状态
- 当前 active task
- 最近更新时间
- 长期状态目录摘要

**涉及文件：**

- `frontend/features/workspaces/*`
- `frontend/features/issues/*`
- 新的 `frontend/features/agents/*`（如采用）

**实现记录：**

- `frontend/features/servers/ui/server-page-client.tsx` 已新增 agent summary 区域
- 新增 `frontend/features/servers/ui/server-agent-detail-dialog.tsx`
- detail 中展示 preset 来源、runtime 状态、持久状态路径和当前 active task

**验收标准：**

- [x] 用户能看见 agent 的身份、配置来源和 runtime 状态
- [x] 用户能区分 persistent runtime 与 temporary runtime
- [x] 用户不需要先进入 task，才能看到 agent runtime 状态

#### 4.2 建立操作入口与受控动作

**描述：** 至少要为以下动作预留显式入口：

- 初始化 agent
- 查看长期状态摘要
- 触发 temporary runtime
- 将 temporary 结果 promote 回长期状态

**实现记录：** 当前 server agent detail 已显式暴露 `Temporary runtime` 与 `Promote result` 入口按钮；在 chat-first conversation shell 完成前，这两个入口先用非破坏性的提示承接，避免高风险动作隐藏在后台。

**验收标准：**

- [x] 高风险动作不是隐藏的后台分支
- [x] 用户能理解什么时候在改长期状态、什么时候只是跑临时任务

#### 4.3 建立和 chat-first 协作面的对接点

**描述：** 根据新的 chat-first 约束，agent detail / runtime 状态不能只依附于 task 页面，还必须能从会话面直接访问。

**至少应支持：**

- 在 channel 里点击 agent 成员，打开右侧 agent profile / activity / runtime 面板
- 在 agent DM 里直接查看该 agent 的 profile、activity 和 runtime state
- 在 thread / task detail / agent profile 之间共享同一套 runtime 状态语义

**实现记录：** 本阶段先把 agent detail / runtime 摘要挂到 `servers` 页面，作为 chat-first UI 重构前的过渡入口；下一份 `11` 会把同一套数据迁到 channel / DM 右侧面板。

**验收标准：**

- [x] spec 中明确 agent profile 可从 channel 和 DM 两侧进入
- [x] spec 中明确 thread / task / profile 共享同一套 agent runtime 解释

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 持久目录、preset、runtime 继续耦合 | 后续越改越像超级对象 | 在 Phase 0 和 Phase 1 显式固定四层边界 |
| persistent runtime 忙时没有清晰策略 | 任务 silently 并发写长期状态 | 在 Phase 2 明确单写者约束和排队/改派协议 |
| temporary runtime 共享挂载长期目录 | 长期记忆被短任务污染 | 在 Phase 3 强制 snapshot + 显式 merge |

---

## 总结

这份 spec 的作用是把“长期 agent”从一个模糊愿景收敛成可实施的边界。完成后，Poco 的 agent 将不再只是一个 preset 驱动的短期执行入口，而是一个拥有身份、长期状态和受控 runtime 的协作成员。
