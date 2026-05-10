# Unified channel runtime tools plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-08 |
| **预期改动范围** | backend internal channel runtime APIs / executor-manager channel runtime proxy / executor ChannelRuntimeClient and MCP server injection / existing channel artifacts and tasks tools / new message, agent directory, collaboration, reaction tools / tests |
| **改动类型** | feat / refactor |
| **优先级** | P1 |
| **状态** | ready for review |

## 实施阶段

- [x] Phase 0: 固化统一 channel runtime tool contract
- [x] Phase 1: 建立 backend internal message / agent directory / collaboration API
- [x] Phase 2: 建立 executor-manager 统一代理前缀
- [x] Phase 3: 建立 executor `ChannelRuntimeClient` 与 `__poco_channel_runtime`
- [x] Phase 4: 迁移 artifacts / tasks / reactions 到统一注入入口
- [x] Phase 5: 测试、兼容与旧入口清理

---

## 背景

### 问题陈述

当前 executor 里已经有两个 channel-scoped MCP server：`channel_tasks` 和 `channel_artifacts`。后续还需要加入消息读取、agent 协作触发、reaction 等能力。如果每个能力都新增一个 `__poco_channel_*` MCP server，executor 的注入层会迅速膨胀，prompt contract 也会变成多个彼此独立的工具说明。

根据 `2026-05-08-persistent-agent-message-passing-and-tool-injection.md`，新增频道 tool 应收敛到一个 `ChannelRuntimeClient` 和一个 built-in MCP server：`__poco_channel_runtime`。agent 看到的是同一组 channel runtime tools；executor 只做一次 channel runtime 注入；backend 仍可按领域拆 service 和 internal API。

### 目标

- executor 只注入一个 channel runtime MCP server，内部包含 artifacts、messages、agents、collaboration、tasks、reactions 等工具。
- 新增 tool 不再创建独立 MCP server key。
- 现有 artifacts / tasks tools 保持 agent-facing tool 名称不变，迁移到统一 server 内。
- 新增 `read_channel_messages`、`list_channel_agents`、`request_agent_collaboration`。
- reaction tools 与 `20-channel-message-reactions-plan.md` 对齐，进入统一 channel runtime。
- tool scope 统一从当前 `session_id` 的 config snapshot 解析，不接受 server/channel/agent 身份参数。

### 非目标

- 不在本 spec 内实现 reaction 数据模型；由 `20-channel-message-reactions-plan.md` 承接。
- 不在本 spec 内实现 trigger envelope UI；由 `22-persistent-agent-trigger-envelope-plan.md` 承接。
- 不做自定义用户安装的 MCP server 管理。
- 不改变现有公开 server channel REST API 的用户侧权限模型。

## Tool surface

第一版统一 channel runtime MCP server 暴露以下工具。

| 领域 | Tool | 输入 | 输出 |
| --- | --- | --- | --- |
| Artifacts | `list_channel_artifacts` | `{}` | 当前频道 published artifacts metadata |
| Artifacts | `search_channel_artifacts` | `{ query, limit, include_content }` | 匹配 artifacts，可选内容片段 |
| Artifacts | `read_channel_artifact` | `{ artifact_id?, logical_path?, max_bytes? }` | 单个 artifact 内容或 metadata |
| Messages | `read_channel_messages` | `{ message_ids?, thread_root_message_id?, limit? }` | 完整消息、thread replies、reaction groups |
| Agents | `list_channel_agents` | `{}` | 当前频道 active agents 的 id、handle、display name、description |
| Collaboration | `request_agent_collaboration` | `{ agent_handle, request_text, reason?, mode?, thread_root_message_id?, reference_message_ids?, reference_artifact_ids? }` | enqueue result / no-op / error |
| Tasks | `create_channel_task` | `{ title, description?, priority? }` | task response |
| Tasks | `claim_channel_task` | `{ task_id }` | task response |
| Tasks | `update_channel_task_status` | `{ task_id, status, position? }` | task response |
| Tasks | `comment_on_channel_task` | `{ task_id, text }` | comment response |
| Reactions | `add_channel_message_reaction` | `{ message_id, emoji }` | reaction group / message reaction response |
| Reactions | `remove_channel_message_reaction` | `{ message_id, emoji }` | reaction group / no-op response |

不增加 `ask_agent_for_review`、`delegate_to_agent`、`summon_agent` 等语义细分工具。agent 协作语义通过可见频道输出和 `request_text` 表达，tool 只负责结构化触发和审计字段。

## Phase 0: 固化统一 channel runtime tool contract

### 目标

确定统一注入 key、client 边界、tool 命名、错误格式和兼容策略。

### 任务清单

#### 0.1 定义统一 MCP server key

**描述：** 新增 `CHANNEL_RUNTIME_MCP_SERVER_KEY = "__poco_channel_runtime"`。后续新增 channel tool 必须挂在该 server。旧 key `__poco_channel_tasks` 和 `__poco_channel_artifacts` 可以迁移期保留，但不能作为新增工具入口。

**涉及文件：**

- `executor/app/core/channel_runtime.py`
- `executor/app/core/engine.py`

**验收标准：**

- [x] channel-scoped run 注入 `__poco_channel_runtime`
- [x] 非 channel-scoped run 不注入
- [x] 新增 tools 不引入新的 `__poco_channel_*` server key

#### 0.2 定义统一结果格式

**描述：** 复用当前 `_format_tool_result(title, data)` 的文本 JSON 格式，统一错误返回为 `{ "error": "...", "code": "..." }`。不要让不同子工具返回完全不同的 envelope。

**涉及文件：**

- `executor/app/core/channel_runtime.py`
- `executor/tests/test_channel_runtime_tools.py`

**验收标准：**

- [x] 成功结果包含 tool title 和 JSON body
- [x] 失败结果不抛给 SDK 崩溃，而是返回结构化 error

## Phase 1: 建立 backend internal message / agent directory / collaboration API

### 目标

让 executor-manager 能代表当前 session 访问频道消息、频道 agent 列表，并显式触发 agent-to-agent collaboration。

### 任务清单

#### 1.1 新增 channel runtime scope resolver

**描述：** 抽出可复用 service，通过 `session_id` 解析 `server_id`、`channel_id`、`agent_identity_id`、`trigger_message_id` 和 `thread_root_message_id`，并校验 agent 仍是当前 channel active member。

**涉及文件：**

- `backend/app/services/channel_runtime_scope_service.py`
- `backend/tests/test_channel_runtime_scope_service.py`

**验收标准：**

- [x] scope 来自 session config snapshot，不来自 request body
- [x] agent 不在 channel 时拒绝 runtime tool
- [x] 跨 channel message / task / artifact 操作被拒绝

#### 1.2 新增 read channel messages internal API

**描述：** 提供当前 session scope 下的消息读取能力，支持按 message ids 读取，也支持读取 thread root 及 replies。响应应包含 message id、author、source、created_at、content.text、reply_count、reaction groups 和必要 metadata。

**建议路径：**

- `POST /api/v1/internal/channel-runtime/messages/read`

**涉及文件：**

- `backend/app/api/v1/internal_channel_runtime.py`
- `backend/app/services/server_channel_message_service.py`
- `backend/app/schemas/server_channel_message.py`

**验收标准：**

- [x] 只能读取当前 channel 的消息
- [x] 支持 trigger message id 和 thread root id
- [x] 返回 full `content.text`，不使用截断 preview 代替正文

#### 1.3 新增 list channel agents internal API

**描述：** 返回当前 channel active agents，供 agent 决定是否需要协作触发。返回字段包括 `agent_identity_id`、`handle`、`display_name`、`description`、`visual_key`。

**建议路径：**

- `POST /api/v1/internal/channel-runtime/agents/list`

**涉及文件：**

- `backend/app/api/v1/internal_channel_runtime.py`
- `backend/app/repositories/server_channel_agent_member_repository.py`
- `backend/app/repositories/agent_identity_repository.py`

**验收标准：**

- [x] 只返回当前 channel active agents
- [x] 不泄露不在当前 channel 的 private agent

#### 1.4 新增 request collaboration internal API

**描述：** 接收上游 agent 的显式 collaboration 请求，并复用 server agent trigger / task enqueue 能力触发目标 agent。普通 agent 输出里的 `@handle` 不自动触发，只有该 API 会创建 agent collaboration run。

**建议路径：**

- `POST /api/v1/internal/channel-runtime/collaboration/request`

请求核心字段：

```json
{
  "agent_handle": "api",
  "request_text": "Please review the auth-specific part.",
  "reason": "Needs owner review",
  "mode": "consult",
  "thread_root_message_id": "00000000-0000-0000-0000-000000000000",
  "reference_message_ids": ["00000000-0000-0000-0000-000000000000"],
  "reference_artifact_ids": []
}
```

**涉及文件：**

- `backend/app/api/v1/internal_channel_runtime.py`
- `backend/app/services/server_agent_trigger_service.py`
- `backend/app/services/channel_shared_context_service.py`
- `backend/app/services/task_service.py`

**验收标准：**

- [x] 目标 agent 必须在当前 channel 且 active
- [x] 目标 agent 不能等于当前 agent
- [x] 使用 dedupe key 防止同一来源重复触发
- [x] hop depth 第一版最大为 2
- [x] 生成 `trigger_type=agent_collaboration`

## Phase 2: 建立 executor-manager 统一代理前缀

### 目标

executor 不直接访问 backend internal API，而是继续通过 executor-manager 代理。新增统一代理前缀，隐藏 backend internal token。

### 任务清单

#### 2.1 新增 agent channel runtime proxy

**建议路径：**

- `POST /api/v1/agent-channel-runtime/messages/read`
- `POST /api/v1/agent-channel-runtime/agents/list`
- `POST /api/v1/agent-channel-runtime/collaboration/request`
- `POST /api/v1/agent-channel-runtime/reactions/add`
- `POST /api/v1/agent-channel-runtime/reactions/remove`

Artifacts / tasks 可先继续走现有代理，也可以在 Phase 4 迁移到同一前缀。

**涉及文件：**

- `executor_manager/app/api/v1/agent_channel_runtime.py`
- `executor_manager/app/services/backend_client.py`
- `executor_manager/app/api/v1/__init__.py`

**验收标准：**

- [x] 代理自动带 internal token
- [x] 代理透传 trace headers
- [x] 代理不允许 body 覆盖 session scope

## Phase 3: 建立 executor `ChannelRuntimeClient` 与 `__poco_channel_runtime`

### 目标

在 executor 中建立唯一 channel runtime facade 和 MCP server。

### 任务清单

#### 3.1 新增 ChannelRuntimeClient

**描述：** `ChannelRuntimeClient` 持有 executor-manager base url 和 session id，提供 artifacts、messages、agents、collaboration、tasks、reactions 方法。内部可以组合现有 `ChannelArtifactClient` / `ChannelTaskClient`，但 executor engine 只感知一个 facade。

**涉及文件：**

- `executor/app/core/channel_runtime.py`
- `executor/app/core/channel_artifacts.py`（已删除旧独立注入入口）
- `executor/app/core/channel_tasks.py`（已删除旧独立注入入口）

**验收标准：**

- [x] client 构造只需要 base_url 和 session_id
- [x] trace headers 与现有工具保持一致
- [x] 子能力错误统一格式化

#### 3.2 新增统一 MCP server factory

**描述：** `create_channel_runtime_mcp_server(runtime_client)` 返回一个包含所有 channel runtime tools 的 MCP server。工具函数可以分文件实现，但最终只通过一个 factory 注入。

**涉及文件：**

- `executor/app/core/channel_runtime.py`
- `executor/app/core/engine.py`
- `executor/app/api/v1/task.py`

**验收标准：**

- [x] `AgentExecutor` 只有 `_inject_channel_runtime_mcp`
- [x] channel-scoped run 可看到 artifacts / tasks / messages / agents / collaboration / reaction tools
- [x] 非 channel run 不注入任何 channel runtime tool

## Phase 4: 迁移 artifacts / tasks / reactions 到统一注入入口

### 目标

把现有分散 channel MCP 注入迁移到统一 runtime，同时保持 agent-facing tool 名称兼容。

### 任务清单

#### 4.1 迁移 artifacts tools

**描述：** `list_channel_artifacts`、`search_channel_artifacts`、`read_channel_artifact` 保持名称和参数不变，但由 `__poco_channel_runtime` 暴露。

**验收标准：**

- [x] 旧 artifacts tool 行为不变
- [x] prompt contract 更新为 channel runtime contract

#### 4.2 迁移 tasks tools

**描述：** `create_channel_task`、`claim_channel_task`、`update_channel_task_status`、`comment_on_channel_task` 保持名称和参数不变，但由 `__poco_channel_runtime` 暴露。

**验收标准：**

- [x] 旧 tasks tool 行为不变
- [x] task tools 不再单独注入独立 server key

#### 4.3 接入 reaction tools

**描述：** 根据 `20-channel-message-reactions-plan.md` 接入 `add_channel_message_reaction` 和 `remove_channel_message_reaction`。

**验收标准：**

- [x] reaction tools 在统一 runtime 中可用
- [x] 不新增 `__poco_channel_reactions`

## Phase 5: 测试、兼容与旧入口清理

### 目标

确保统一注入不破坏现有 artifacts / tasks 使用，同时新增 tools 可用且权限正确。

### 任务清单

#### 5.1 后端测试

**验收标准：**

- [x] scope resolver 测试通过
- [x] message read 跨 channel 被拒绝
- [x] collaboration dedupe 和 max depth 生效

#### 5.2 executor-manager 测试

**验收标准：**

- [x] runtime proxy 路由转发 session_id 和 payload
- [x] internal token 不暴露给 executor

#### 5.3 executor 测试

**验收标准：**

- [x] channel runtime server 只在 channel scope 注入
- [x] artifacts / tasks tool 名称仍存在
- [x] messages / agents / collaboration / reactions tool 参数校验生效
- [x] 不再出现新增独立 `__poco_channel_*` key

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 一次迁移 artifacts / tasks 造成回归 | 现有频道协作能力中断 | 保持 agent-facing tool 名称和 executor-manager 代理兼容，必要时分阶段迁移 |
| 单一 runtime 文件过大 | 可维护性下降 | 使用 facade + 子模块结构，只有注入入口统一，不要求所有实现写进一个文件 |
| collaboration tool 造成 agent 循环 | 任务风暴和噪音 | dedupe key、max depth、禁止 self target、仅显式 tool 触发 |
| message read 返回过多内容 | token 膨胀 | 默认 limit，按 id / thread 精确读取，必要时只返回 metadata + preview |
| backend internal API 过度耦合 | service 边界模糊 | internal route 可统一前缀，但 backend service 按 messages/tasks/reactions/collaboration 拆分 |

## 总结

这次改动的核心问题是：频道 runtime tool 会继续增加，如果每个能力都独立注入 MCP server，executor 注入层和 agent prompt contract 会变得混乱。解决思路是建立一个 `ChannelRuntimeClient` 和一个 `__poco_channel_runtime` MCP server，统一承载 artifacts、messages、agents、collaboration、tasks 和 reactions。agent-facing tool 名称保持清晰，backend service 仍按领域拆分，executor 注入层只保留一个 channel runtime 入口。

## 验证记录

- backend: `uv run python -m unittest tests.test_channel_runtime_scope_service tests.test_channel_runtime_service tests.test_internal_channel_runtime_api tests.test_internal_channel_message_reactions_api tests.test_channel_artifact_service tests.test_server_channel_task_agent_service`
- executor-manager: `uv run python -m unittest tests.test_agent_channel_runtime_api`
- executor: `uv run python -m unittest tests.test_channel_runtime_tools tests.test_engine_channel_artifact_tools tests.test_engine_channel_reaction_tools tests.test_engine_channel_task_hint tests.test_engine_channel_runtime_hint tests.test_engine_trigger_context_prompt`
- executor syntax: `uv run python -m py_compile app/core/channel_runtime.py app/core/engine.py app/api/v1/task.py`
- executor lint: `uv run ruff check app/core/channel_runtime.py app/core/engine.py app/api/v1/task.py tests/test_channel_runtime_tools.py tests/test_engine_channel_artifact_tools.py tests/test_engine_channel_reaction_tools.py tests/test_engine_channel_task_hint.py tests/test_engine_channel_runtime_hint.py`
