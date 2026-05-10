# Persistent agent trigger envelope plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-08 |
| **预期改动范围** | backend channel agent trigger prompt construction / agent run and message metadata / executor prompt composition / frontend agent session message rendering and i18n / backend, executor, frontend tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | ready-for-review |

## 实施阶段

- [x] Phase 0: 固化 trigger envelope schema 与兼容策略
- [x] Phase 1: 后端生成并持久化 trigger envelope
- [x] Phase 2: executor 基于 envelope 组合 SDK prompt
- [x] Phase 3: 前端 agent session 两层消息显示
- [x] Phase 4: 测试、回归与旧 prompt 收敛

---

## 背景

### 问题陈述

当前频道触发持久化 agent 时，`ServerAgentTriggerService` 会调用 `ChannelSharedContextService.build_message_trigger_prompt()`，把触发消息、channel id、thread root id、频道成员、agent 列表、行为规则、recent messages 和 artifacts preview 拼成一条大 prompt。随后 `TaskService.enqueue_task()` 会把这条 prompt 当成普通 user message 写进 agent session。

这会带来两个直接问题。第一，用户点进 agent session 回看时，看到的是系统拼接文本，而不是清晰的“触发上下文”和“用户原始消息”。第二，agent 的上下文获取方式是 backend 一次性内联，而不是根据 id 通过 runtime tools 渐进读取，容易出现截断、噪音和不必要 token 消耗。

根据 `2026-05-08-persistent-agent-message-passing-and-tool-injection.md`，后续应把持久化 agent 的频道触发输入拆成两层：默认收缩显示的 `AgentTriggerEnvelope`，以及普通可见的 trigger body。

### 目标

- 定义稳定的 `AgentTriggerEnvelope` schema，包含 server/channel/message/thread/agent/run/source actor 等索引。
- 后端触发 agent 时同时持久化 trigger envelope 和 trigger body，不再只有一条 composed prompt。
- executor 仍可把 envelope 摘要、trigger body 和 tool contract 组合成 SDK prompt，但 UI 和持久化层保留结构化边界。
- agent session UI 默认收缩显示 trigger envelope，并在其下方显示原始触发正文。
- 兼容旧 session / 旧 run，不破坏现有 agent callback、execution placeholder 和频道 mirror 行为。

### 非目标

- 不在本 spec 内实现所有 channel runtime tools；它们由 `23-unified-channel-runtime-tools-plan.md` 承接。
- 不改变 Claude Agent SDK 的 session resume 机制。
- 不把 trigger envelope 设计成可由用户编辑的对象。
- 不新增复杂审计页面；第一版只保证 agent session 中可读、可展开。

## 设计原则

### 1. Trigger envelope 是运行时索引，不是业务正文

envelope 只回答“这次 run 从哪里来、指向什么对象、agent 可以按哪些 id 继续读取”。它不应该包含大段 recent messages 或 artifact content。

### 2. Trigger body 保持原始语义

trigger body 是用户或上游 agent 真正发出的自然语言请求。它应该尽量接近频道消息原文，不能被系统提示、索引或 artifacts preview 混写。

### 3. UI 默认折叠系统上下文

agent session 应显示两层输入：上方折叠的 trigger context，下方普通 user message。这样用户可以理解 agent 为什么被触发，又不会被系统 metadata 干扰阅读。

## Trigger envelope schema

建议第一版 schema：

```json
{
  "version": 1,
  "trigger_type": "channel_mention",
  "server_id": "00000000-0000-0000-0000-000000000000",
  "channel_id": "00000000-0000-0000-0000-000000000000",
  "trigger_message_id": "00000000-0000-0000-0000-000000000000",
  "thread_root_message_id": "00000000-0000-0000-0000-000000000000",
  "target_agent_identity_id": "00000000-0000-0000-0000-000000000000",
  "target_agent_handle": "reviewer",
  "source_actor": {
    "actor_type": "user",
    "user_id": "user_123",
    "display_name": "Alice"
  },
  "references": {
    "message_ids": ["00000000-0000-0000-0000-000000000000"],
    "artifact_ids": [],
    "task_ids": []
  },
  "handoff": {
    "parent_run_id": null,
    "depth": 0,
    "dedupe_key": "channel-trigger:<message_id>:<agent_id>"
  }
}
```

`trigger_type` 第一版支持：

- `channel_mention`
- `agent_dm`
- `agent_collaboration`

`scheduled_channel_task` 可以预留，但本 spec 不实现。

## Phase 0: 固化 trigger envelope schema 与兼容策略

### 目标

先确定 schema、存储位置、旧数据兼容方式和 prompt 迁移边界。

### 任务清单

#### 0.1 定义 schema 与类型

**描述：** 新增后端 Pydantic schema 表达 `AgentTriggerEnvelope`、`TriggerSourceActor`、`TriggerReferences` 和 `TriggerHandoff`。字段命名使用 snake_case，序列化到 JSON 后保持稳定。

**涉及文件：**

- `backend/app/schemas/agent_trigger.py`
- `backend/tests/test_agent_trigger_envelope_schema.py`

**验收标准：**

- [x] schema 能校验必填 id、trigger_type 和 source_actor
- [x] schema 能序列化为 JSON，用于 run/message metadata
- [x] 无效 trigger_type 被拒绝

#### 0.2 决定持久化位置

**描述：** 第一版优先不新增表。建议把 envelope 放入：

- `agent_runs.config_snapshot.trigger_context`
- `agent_messages.content.metadata.trigger_context`

其中 run snapshot 是执行链路权威输入，message metadata 是 agent session UI 读取入口。两者内容应一致，或 message metadata 由 run snapshot 派生。

**涉及文件：**

- `backend/app/services/session_queue_service.py`
- `backend/app/models/agent_run.py`
- `backend/app/models/agent_message.py`

**验收标准：**

- [x] 新 run 能在 config snapshot 中保存 trigger_context
- [x] agent user message 能携带 trigger_context metadata
- [x] 旧 message 没有 metadata 时前端仍按普通消息渲染

## Phase 1: 后端生成并持久化 trigger envelope

### 目标

把频道 agent 触发从“只生成 composed prompt”改成“生成 envelope + trigger body + runtime prompt input”。

### 任务清单

#### 1.1 拆分 ChannelSharedContextService 职责

**描述：** 将 `build_message_trigger_prompt()` 拆成更明确的方法：

- `build_trigger_envelope(...)`
- `extract_trigger_body(message)`
- `build_legacy_prompt_for_sdk(envelope, body, context_index)`，迁移期保留

recent messages 和 artifacts 不再默认完整内联，只保留轻量索引或由 executor contract 指向 runtime tools。

**涉及文件：**

- `backend/app/services/channel_shared_context_service.py`
- `backend/tests/test_channel_shared_context_service.py`

**验收标准：**

- [x] trigger body 优先读取 `content.text`，不使用截断 preview 作为正文
- [x] envelope 包含 trigger message id 和 thread root id
- [x] recent context 不再作为唯一上下文来源

#### 1.2 ServerAgentTriggerService 接入 envelope

**描述：** `trigger_for_channel_message()` 创建 `TaskEnqueueRequest` 时，把 envelope 放入 `TaskConfig` 或等价 metadata 字段，并把 trigger body 作为可见用户输入。`client_request_id` 继续使用 `channel-trigger:<message_id>:<agent_id>`，并同步写入 envelope.handoff.dedupe_key。

**涉及文件：**

- `backend/app/services/server_agent_trigger_service.py`
- `backend/app/schemas/session.py`
- `backend/app/schemas/task.py`

**验收标准：**

- [x] channel mention 触发时生成 `trigger_type=channel_mention`
- [x] agent DM 触发时生成 `trigger_type=agent_dm`
- [x] Task enqueue 的 prompt 不再必须等于完整 composed context

#### 1.3 SessionQueueService 持久化 message metadata

**描述：** `materialize_run()` 创建 user `AgentMessage` 时，如果 run config 包含 trigger_context，则写入 `AgentMessage.content.metadata.trigger_context`。同时保留 `TextBlock` 中的 trigger body，供旧 UI 和 SDK prompt 兼容。

**涉及文件：**

- `backend/app/services/session_queue_service.py`
- `backend/app/repositories/message_repository.py`

**验收标准：**

- [x] 新 agent message content 同时包含 text block 和 metadata.trigger_context
- [x] text_preview 来自 trigger body，而不是系统 composed prompt
- [x] 旧普通 chat enqueue 不受影响

## Phase 2: executor 基于 envelope 组合 SDK prompt

### 目标

executor 接收结构化 trigger context 后，负责把 envelope 摘要、trigger body 和 channel runtime contract 组合成真正发给 SDK 的 prompt。

### 任务清单

#### 2.1 TaskConfig 支持 trigger_context

**描述：** executor schema 增加 `trigger_context` 字段。该字段只用于 prompt composition 和 channel runtime scope，不由模型直接改写。

**涉及文件：**

- `executor/app/schemas/request.py`
- `executor_manager/app/schemas/task.py`

**验收标准：**

- [x] executor 可解析 trigger_context
- [x] 非频道 run 没有 trigger_context 时行为不变

#### 2.2 重写 channel trigger prompt contract

**描述：** `_compose_user_prompt()` 对 channel-scoped run 增加 compact trigger context 段，告诉 agent 当前 trigger id、thread id 和可用 tools。不要再把完整 recent conversation 和 artifact preview 作为默认内联内容。

**涉及文件：**

- `executor/app/core/engine.py`
- `executor/tests/test_engine_trigger_context_prompt.py`

**验收标准：**

- [x] SDK prompt 包含 trigger envelope 的关键 id
- [x] SDK prompt 明确提示通过 channel runtime tools 按需读取消息和 artifacts
- [x] SDK prompt 不重复展示大段 recent context

## Phase 3: 前端 agent session 两层消息显示

### 目标

让用户在 agent session 中清楚看到“系统触发上下文”和“触发正文”的边界。

### 任务清单

#### 3.1 前端模型映射 trigger_context

**描述：** agent message API 映射时读取 `content.metadata.trigger_context`，转换成前端模型字段。

**涉及文件：**

- `frontend/features/chat/model/types.ts`
- `frontend/features/chat/api/` 或当前 agent session 消息 API 映射文件

**验收标准：**

- [x] 新消息模型包含 `triggerContext`
- [x] 无 triggerContext 的普通 user message 正常显示

#### 3.2 渲染可折叠 Trigger Context

**描述：** 在 user message 正文上方渲染一块默认收缩的 trigger context。折叠态显示来源、trigger type、channel id、message id；展开态显示更完整的人类可读字段。文案走 i18n。

**涉及文件：**

- `frontend/features/chat/ui/` 或当前 agent session message row 文件
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [x] trigger context 默认收缩
- [x] 展开后可看到 channel/message/thread/run/agent 索引
- [x] trigger body 仍按普通 user message 样式显示

## Phase 4: 测试、回归与旧 prompt 收敛

### 目标

用测试锁定新旧兼容边界，避免频道触发再次退回粗糙 prompt。

### 任务清单

#### 4.1 后端测试

**描述：** 覆盖 envelope 构造、message metadata 持久化、旧普通 chat enqueue 不变。

**验收标准：**

- [x] `backend/tests/test_channel_shared_context_service.py` 覆盖 envelope/body 分离
- [x] `backend/tests/test_session_queue_service.py` 覆盖 trigger_context metadata

#### 4.2 executor 测试

**描述：** 覆盖 trigger_context prompt composition 和无 trigger_context 的兼容路径。

**验收标准：**

- [x] channel run prompt 包含索引和 tool 指引
- [x] 普通 run prompt 不出现 channel trigger context

#### 4.3 前端测试与静态检查

**描述：** 覆盖 trigger context 的折叠/展开渲染和 i18n 文案。

**验收标准：**

- [x] `cd frontend && pnpm lint` 通过
- [x] 新增 trigger context 文案中英文 locale 都有值

### Phase 4 验证记录

- `cd backend && PYTHONPATH=. uv run --with pytest pytest tests/test_agent_trigger_envelope_schema.py tests/test_session_queue_service.py tests/test_channel_shared_context_service.py tests/test_server_agent_trigger_service.py -q`：10 passed。
- `cd executor && PYTHONPATH=. uv run --with pytest pytest tests/test_engine_trigger_context_prompt.py tests/test_engine_channel_artifact_tools.py tests/test_engine_channel_task_hint.py tests/test_engine_channel_reaction_tools.py -q`：12 passed。
- `cd frontend && node --test --experimental-strip-types --experimental-specifier-resolution=node features/chat/services/message-parser.test.ts`：2 passed。
- `cd frontend && pnpm lint`：通过。
- `cd frontend && pnpm build`：通过；保留 Next.js 关于 workspace root 多 lockfile 推断的 warning。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| envelope 和 text block 内容不一致 | UI 和 SDK 看到的触发语义不同 | 后端统一从同一个 trigger body source 派生 text block 和 prompt input |
| 旧 session 没有 metadata | 前端渲染异常 | 前端把 triggerContext 作为可选字段处理 |
| prompt 内联上下文减少后 agent 信息不足 | agent 首轮回答不完整 | 同步实现 `read_channel_messages` 和 artifacts tools 指引，让 agent 按需读取 |
| trigger_context 存进 config_snapshot 后膨胀 | run snapshot 变大 | envelope 只放 id 和短 metadata，不放正文历史和 artifact content |

## 总结

这次改动的核心问题是：频道触发持久化 agent 时，系统上下文和用户正文被混成一条大 prompt。解决思路是把触发输入拆成 `AgentTriggerEnvelope` 和 trigger body，backend 负责持久化结构化索引，executor 负责组合 SDK prompt，frontend 负责默认收缩显示 trigger context。这样既保留 SDK session 连续对话能力，也让频道上下文通过 runtime tools 渐进读取。
