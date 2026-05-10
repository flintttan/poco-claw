# Agent-driven channel task operations plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-06 |
| **预期改动范围** | backend channel task service adapters / agent-facing structured task tools or internal APIs / executor prompt and tool contract / task-thread linkage / tests |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 收敛 agent task 操作边界与非目标
- [x] Phase 1: 定义结构化 task tool 或专用接口契约
- [x] Phase 2: 建立 backend task adapter 与消息回流闭环
- [x] Phase 3: 把 task 自主协作接入 executor 提示词与验证

---

## 背景

### 问题陈述

`09-channel-task-collaboration-plan.md` 已经把 channel task 建成了一等子域，用户可以在频道中创建 task、更新状态、认领 task，并通过 task root message 和 thread 看到状态变化。但这套能力当前基本还是“人驱动”的：用户显式创建 task，用户手动拖动状态，用户触发 claim/unclaim。

与此同时，新的 server agent 协作面已经把 agent 提升成频道里的长期成员。它现在可以被 mention 触发、参与 thread、维护 persistent state，还会在后续 execution observability 模型中变成可观察对象。如果 task 仍然只能由用户显式操作，那么 agent 虽然参与了协作，却还不是 task 流转的一等参与者。

当前代码库里也已经出现了一个信号：`agent_assignments` 预留了 `server_channel_task_id` 字段，但这条关系还没有真正被 server task 主线使用起来。与此同时，executor 里的 `todos` 只是一种 session 内部执行清单，并不是 channel task。也就是说，系统已经有 task service、有 session todo、有 assignment 字段，但还没有一条稳定的“agent -> channel task service”结构化操作通路。

### 目标

这份计划的目标是让 agent 成为 channel task 的一等协作者，而不是继续依赖自然语言转述或用户手动二次操作。重点包括：

- 为 agent 定义结构化的 channel task 操作能力
- 让 agent 可以创建 channel task、更新状态、认领和评论 task
- 保持 `ServerChannelTaskService` 作为 task 子域唯一主服务边界
- 让 task 状态变化继续通过结构化 system message 回流到频道 thread
- 清晰区分 session todos 和 channel tasks，避免两种“任务”语义混淆

### 关键洞察

#### 1. 不能把 agent task 协作做成 callback 文本协议

如果依赖模型在消息里说“我创建了一个任务”，再由 callback 或文本解析器猜测意图，task 子域会重新退化成脆弱的自由文本协议。这和 channel task 已经建立起来的结构化服务边界相冲突。

#### 2. session todos 和 channel tasks 是两层对象

session todos 表示 agent 这次执行内部的计划与步骤；channel task 表示团队协作中的结构化工作项。两者可以有关联，但不能互相替代。

#### 3. task 操作必须绑定当前 server/channel 上下文

agent 在 persistent runtime 中可能跨多次会话工作，但 task 写入必须受当前 `server_id / channel_id / thread_root_message_id / agent_identity_id` 限制，不能让 agent 获得模糊的全局 task 写权限。

---

## Phase 0: 收敛 agent task 操作边界与非目标

### 目标

先把 agent 允许做哪些 task 操作、不允许做哪些自动推断讲清楚，避免实现时重新滑回“先做个文本协议顶一下”。

### 任务清单

#### 0.1 定义 agent 侧最小 task 能力集

**描述：** 第一版最小 task 能力建议包括：

- `create_channel_task`
- `update_channel_task_status`
- `claim_channel_task`
- `comment_on_channel_task`

`unclaim`、`edit task fields`、`bulk reorder` 可以视实现复杂度决定是否进入第一版。

**涉及文件：**

- `specs/constitution/2026-05-06-server-agent-observability-tasks-and-persistence.md`
- `backend/app/services/server_channel_task_service.py`

**验收标准：**

- [x] agent 侧 task 能力集被明确定义
- [x] 第一版能力与用户侧 task API 边界清晰

#### 0.2 定义和 session todos 的关系

**描述：** 明确 session todos 不自动提升为 channel task；只有 agent 显式调用结构化 task 能力，才创建或更新 channel task。

**涉及文件：**

- `executor/app/hooks/todo.py`
- `backend/app/services/server_channel_task_service.py`

**验收标准：**

- [x] session todos 和 channel tasks 的语义边界清晰

#### 0.3 明确非目标

**描述：** 当前阶段不做：

- 从自由文本自动猜测 task 创建意图
- 从 `TodoWrite` 自动同步到 channel task
- 让 agent 获得跨 server 或跨 channel 的任意 task 写权限

**验收标准：**

- [x] 非目标写清楚，避免隐式 scope 膨胀

---

## Phase 1: 定义结构化 task tool 或专用接口契约

### 目标

为 agent 操作 channel task 建立稳定的结构化输入输出契约，避免 callback 文本推断。

### 任务清单

#### 1.1 设计 tool 或内部 API payload

**描述：** 定义每个 task 操作的结构化参数，至少包含当前 channel 上下文和最小业务字段。

**建议示例：**

- `create_channel_task(title, description, priority?, thread_root_message_id?)`
- `update_channel_task_status(task_id, status, position?)`
- `claim_channel_task(task_id, assignee_mode?)`
- `comment_on_channel_task(task_id, text)`

**涉及文件：**

- `executor/app/schemas/request.py`
- `backend/app/schemas/server_channel_task.py`
- 如有需要：新增 agent task tool schema

**验收标准：**

- [x] 每个操作有明确结构化 payload
- [x] payload 能从 session config 解析默认上下文

#### 1.2 约束上下文来源

**描述：** agent 调 task 能力时，`server_id / channel_id / agent_identity_id / thread_root_message_id` 应优先来自 `config_snapshot` 或运行时上下文，而不是完全依赖模型自己填写。

**涉及文件：**

- `backend/app/services/task_service.py`
- `backend/app/services/session_service.py`
- `backend/app/services/server_agent_trigger_service.py`

**验收标准：**

- [x] task 操作的上下文绑定当前会话
- [x] 不能跨频道误写 task

#### 1.3 明确错误返回与拒绝策略

**描述：** 如果当前 session 没有 channel 上下文、task 不存在、状态非法或权限不足，task 能力必须返回结构化错误，而不是静默失败。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- 如有需要：新增 adapter error schema

**验收标准：**

- [x] 错误返回结构化、可观察
- [x] agent 可以据此在会话中做出合理解释

### Phase 1 implementation notes

- backend 新增了 `server_channel_task_agent` schema，第一版结构化能力集收敛为 `create / update_status / claim_self / comment` 四个操作。
- 新增 `ServerChannelTaskAgentService.resolve_context()`，从当前 `session.config_snapshot` 强制解析 `server_id / channel_id / agent_identity_id / thread_root_message_id`，作为后续 agent task 写入的唯一默认上下文来源。
- 当前 contract 明确区分了 session todos 与 channel tasks：todo 不会自动提升为 channel task，只有显式调用结构化 task 能力才会进入 channel task 子域。

---

## Phase 2: 建立 backend task adapter 与消息回流闭环

### 目标

让 agent 的结构化 task 操作最终仍然走 channel task 主服务边界，并保持现有 system message 协作流。

### 任务清单

#### 2.1 新增 agent-facing task adapter

**描述：** 在 backend 增加一层 agent-facing task adapter，把 executor 侧结构化调用转换为 `ServerChannelTaskService` 的 create/status/claim/comment 调用。

**涉及文件：**

- 新增 `backend/app/services/server_channel_task_agent_service.py` 或等价 adapter
- `backend/app/services/server_channel_task_service.py`
- 如有需要：新增内部 API 路由

**验收标准：**

- [x] agent 侧 task 操作不绕开 `ServerChannelTaskService`
- [x] adapter 层只做上下文绑定、权限校验和参数归一

#### 2.2 保持 task system message 回流

**描述：** agent 创建或更新 task 后，仍由 task service 统一生成 task root message 或状态变化 system message。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/models/server_channel_message.py`

**验收标准：**

- [x] agent 创建 task 后，频道 thread 中能追溯 task root
- [x] agent 状态更新后，频道 thread 中能追溯 system message

#### 2.3 收敛 assignment 关系

**描述：** 如果后续需要把 channel task 和 agent runtime 绑定，应优先复用或正式接通 `agent_assignments.server_channel_task_id`，而不是再造一套并行关联。

**涉及文件：**

- `backend/app/models/agent_assignment.py`
- `backend/app/repositories/agent_assignment_repository.py`
- `backend/app/services/agent_assignment_service.py`

**验收标准：**

- [x] task 与 agent runtime 的关系有明确演进路径
- [x] 不新增多套平行绑定关系

---

## Phase 3: 把 task 自主协作接入 executor 提示词与验证

### 目标

让 agent 在运行时知道何时该用结构化 task 能力，并补齐验证链路。

### 任务清单

#### 3.1 在执行层注入 task collaboration hint

**描述：** 在 persistent 或 channel-scoped agent 执行中，明确告诉 agent：如果当前工作需要沉淀为团队任务，应优先使用结构化 task 能力，而不是只在自然语言里口头声明。

**涉及文件：**

- `executor/app/core/engine.py`
- `backend/app/services/channel_shared_context_service.py`

**验收标准：**

- [x] task 协作提示词和 persistent-state 提示词不冲突
- [x] agent 明确知道“什么时候该创建或更新 channel task”

#### 3.2 补充可观测性与审计

**描述：** agent 触发的 task 操作需要在 backend 或 channel thread 中有稳定审计线索，便于追查是谁、在什么上下文下改了 task。

**涉及文件：**

- `backend/app/services/server_channel_task_service.py`
- `backend/app/models/server_channel_message.py`
- 如有需要：审计或日志服务

**验收标准：**

- [x] task 变更能回溯到 agent identity 或 session context

#### 3.3 完成验证与回写 spec

**描述：** 为 create/status/claim/comment 这几条最小闭环补齐验证，并回写 spec 状态。

**涉及文件：**

- `backend/tests/*`
- 如有需要：executor 侧测试
- `specs/draft/17-agent-driven-channel-task-operations-plan.md`

**验收标准：**

- [x] 有定向验证覆盖 agent 创建和更新 channel task
- [x] spec 回写实际实现记录和状态

### Phase 2 implementation notes

- backend 新增了 `ServerChannelTaskAgentService` 作为 agent-facing adapter：它先从当前 session 解析 channel-scoped context，再把 `create / status / claim / comment` 四类结构化操作转给 `ServerChannelTaskService`。
- backend 新增 `/api/v1/internal/server-channel-tasks/{create,status,claim,comment}` internal API；executor manager 再以 `/api/v1/agent-channel-tasks/*` 形式做代理，复用现有 internal token 与 session 绑定链路。
- `ServerChannelTaskService` 新增了 `comment_on_task()`，并为 task root message / system message 统一注入 `actor_type / actor_agent_identity_id / actor_agent_handle / actor_session_id` 等审计字段；这保证 agent 改动仍通过原有 task service 回流到频道 thread。
- 当前没有新增并行 task-runtime 绑定表，只保留 `agent_assignments.server_channel_task_id` 作为后续正式接通的演进位，避免再造第二套关系。

### Phase 3 implementation notes

- executor 新增内置 channel task MCP server，向 agent 暴露 `create_channel_task`、`update_channel_task_status`、`claim_channel_task`、`comment_on_channel_task` 四个结构化工具。
- `AgentExecutor._compose_user_prompt()` 新增 channel task collaboration hint，只在存在 `server_id / channel_id / agent_identity_id` 的 channel-scoped agent 会话中注入，明确区分 session todos 与 channel tasks，并要求优先使用结构化 task 工具。
- task hint 与已有 persistent-state hint 是串联注入的，两者不会互相覆盖：一个约束私有长期状态写入，一个约束团队任务协作。

## 验证记录

- backend: `uv run python -m unittest tests.test_internal_server_channel_tasks_api tests.test_server_channel_task_agent_service tests.test_server_channel_task_service`
- executor: `uv run python -m unittest tests.test_engine_channel_task_hint tests.test_engine_persistent_state_hint`
- syntax: `uv run python -m py_compile executor_manager/app/api/v1/agent_channel_tasks.py executor_manager/app/services/backend_client.py executor/app/core/channel_tasks.py executor/app/core/engine.py executor/app/api/v1/task.py`
