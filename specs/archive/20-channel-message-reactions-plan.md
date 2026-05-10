# Channel message reactions plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-07 |
| **预期改动范围** | backend server channel message reaction model/API/internal runtime API / unified executor channel runtime MCP tool injection / executor-manager proxy / frontend conversation message UI and i18n / backend and executor tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 固化 reaction 对象模型与权限边界
- [x] Phase 1: 建立后端 reaction 持久化、聚合与用户 API
- [x] Phase 2: 建立 agent-facing reaction runtime tools
- [x] Phase 3: 接入频道消息 UI 与乐观交互
- [x] Phase 4: 补齐测试、迁移验证与体验收口

---

## 背景

### 问题陈述

当前频道聊天的核心持久化对象是 `server_channel_messages`。频道消息支持根消息与 thread reply，消息响应通过 `ServerChannelMessageResponse` 返回 `author_user`、`reply_count`、`content` 和时间字段。agent 在频道被 `@handle` 触发后，会由 `ServerAgentTriggerService` 创建执行占位消息；执行完成后，`CallbackService` 会把 assistant 输出镜像成同一张 `server_channel_messages` 里的 `system + source=agent_session` 消息。前端的 `MessageRow` 统一渲染人类消息、system 执行消息和 agent session 消息。

这套结构现在没有 reaction 能力。用户如果想对某条频道消息表达“认可、已读、赞同、需要关注”，只能继续发一条新消息，导致频道流被低信息量回复打断。agent 也没有结构化方式对消息做轻量反馈，只能自然语言回复。

直接把 reaction 写进 `server_channel_messages.content` 或额外 JSON 字段会带来几个问题：

- reaction 是多人、多 agent 对同一消息的可变关系，不是消息正文的一部分
- 需要支持同一 emoji 的聚合、当前 actor 是否已反应、撤销和并发去重
- 未来可能需要审计、通知、活动流或按 actor 查询，这些都不适合藏在 message JSON
- agent 贴表情需要稳定的运行时操作面，而不是让模型改写消息内容

因此，频道消息 reaction 应该作为独立关系模型落库，并通过消息读取接口返回聚合视图。

### 目标

这份 spec 的目标是为频道聊天增加第一版表情反应能力：

- 人类频道成员可以给根消息和 thread reply 添加或取消 emoji reaction
- 频道内 agent 也可以通过结构化 runtime tool 给消息添加或取消 reaction
- 消息列表和 thread 响应返回 reaction 聚合数据，前端可直接渲染
- reaction 权限继续基于 server/channel membership 和当前 channel-scoped session
- 保持频道消息正文、thread、agent execution placeholder 和 agent session mirror 的现有语义不变

### 非目标

以下内容不在第一版范围内：

- 不做自定义 emoji 上传、emoji 管理后台或 workspace 级 emoji pack
- 不做跨频道 reaction 搜索、全局通知中心或复杂 activity feed
- 不把 reaction 作为会触发 agent 执行的事件源
- 不允许 agent 伪造人类用户身份贴 reaction
- 不重做消息实时同步；第一版继续沿用当前频道消息刷新/polling 心智

### 当前实现观察

- `backend/app/models/server_channel_message.py` 只有消息本体字段，没有 reaction 或 author agent 外键。
- `backend/app/services/server_channel_message_service.py` 的 `_build_message_response` 是挂载派生字段的自然入口，目前已经注入 `reply_count` 和 `author_user`。
- `backend/app/repositories/server_channel_message_repository.py` 已经有 `list_by_channel`、`list_replies`、`count_replies_by_roots`，reaction 聚合可以采用类似 `count_replies_by_roots` 的批量查询方式，避免 N+1。
- `frontend/features/servers/api/servers-api.ts` 的 `mapConversationMessage` 是前端模型接入点；`frontend/features/servers/ui/conversation-message-row.tsx` 是渲染入口。
- 当前 agent-facing channel tools 已有两条先例：`executor/app/core/channel_tasks.py` 和 `executor/app/core/channel_artifacts.py`。它们都只在 `TaskConfig` 具备 `server_id`、`channel_id`、`agent_identity_id` 时由 executor 注入，并通过 executor-manager 代理到 backend internal API。根据 `2026-05-08-persistent-agent-message-passing-and-tool-injection.md`，后续新增频道 tool 不应继续扩散为多个独立 MCP server，而应收敛到统一 `ChannelRuntimeClient` / `__poco_channel_runtime` 注入入口。

### 关键洞察

#### 1. 新建关系表是正确方向

reaction 的基数是 `message x emoji x actor`，生命周期独立于消息正文。独立表可以自然表达唯一约束、撤销、聚合计数和 actor 列表，也能让根消息和 thread reply 使用同一套模型。

#### 2. actor 必须显式支持 human 与 agent 两种身份

当前频道消息本身只有 `author_user_id`，agent 消息通过 `content.agent_handle / agent_message_id` 表达来源。reaction 不能复用 `author_user_id`，否则 agent reaction 会失去稳定身份。第一版应把 reaction actor 建成一个 tagged union：`actor_type = "user" | "agent"`，并分别填 `actor_user_id` 或 `actor_agent_identity_id`。

#### 3. agent 贴表情应走统一 channel runtime MCP tool，而不是普通消息协议

agent 需要的是“对某条消息执行 reaction 操作”的结构化能力。该能力应加入统一 channel-scoped built-in MCP server，例如 `__poco_channel_runtime`，由 `ChannelRuntimeClient` 的 reaction 子能力提供 `add_channel_message_reaction` / `remove_channel_message_reaction`。tool 调用自动绑定当前 session 的 server/channel/agent identity，上游模型只传 `message_id` 和 `emoji`。

#### 4. 人类 reaction 入口应挂在消息按钮组，而不是常驻大控件

第一版 UI 应复用消息 hover / focus 时出现的按钮组，在按钮组里增加一个“添加表情”的 icon button。点击后，在按钮组下方弹出一个轻量悬浮面板，面板内展示固定预设 emoji。这样 reaction 入口足够轻，不会占用消息正文空间；同时用户可以清楚地看到 reaction 是针对当前这条消息的操作。

---

## Phase 0: 固化 reaction 对象模型与权限边界

### 目标

先确定数据语义、emoji 规范、actor 规则和权限边界，避免实现时把 reaction 混入 message content 或让 agent 手动声明身份。

### 任务清单

#### 0.1 定义 reaction 一等模型

**描述：** 新增 `ServerChannelMessageReaction` 概念，表达一条频道消息上的一个 actor reaction。建议表名为 `server_channel_message_reactions`，核心字段：

- `id`
- `message_id`
- `channel_id`
- `emoji`
- `actor_type`
- `actor_user_id`
- `actor_agent_identity_id`
- `created_at`
- `updated_at`

约束：

- `message_id` 外键到 `server_channel_messages.id`，`ondelete="CASCADE"`
- `channel_id` 冗余保存，便于授权过滤、聚合索引和避免 join 扩散
- `actor_type = "user"` 时必须有 `actor_user_id` 且 `actor_agent_identity_id` 为空
- `actor_type = "agent"` 时必须有 `actor_agent_identity_id` 且 `actor_user_id` 为空
- 唯一约束：`message_id, emoji, actor_type, actor_user_id, actor_agent_identity_id`

**涉及文件：**

- `backend/app/models/server_channel_message_reaction.py` - 新增 SQLAlchemy model
- `backend/app/models/__init__.py` - 导出新 model
- `backend/alembic/versions/` - 新增迁移

**验收标准：**

- [x] reaction 不存入 `server_channel_messages.content`
- [x] 同一 actor 对同一消息的同一 emoji 只能存在一条记录
- [x] 删除消息会级联删除 reaction

#### 0.2 定义 emoji 输入规范

**描述：** 第一版只接受标准 Unicode emoji 字符串，不支持自定义 emoji 名称。后端做最小规范化：

- `emoji` 去首尾空白
- 长度限制建议 1-32 个 Unicode code points 或等价安全长度
- 拒绝空字符串、纯文本单词、URL、过长字符串
- 暂不要求处理 skin tone 合并逻辑；只要前端传入的完整 emoji 序列一致，就聚合到同一组

**涉及文件：**

- `backend/app/schemas/server_channel_message_reaction.py`
- `backend/app/services/server_channel_message_reaction_service.py`

**验收标准：**

- [x] API 会拒绝空 emoji 和明显非法输入
- [x] 同一个 emoji 序列在后端有稳定存储形式

#### 0.3 定义权限边界

**描述：** 人类 reaction 权限复用 `ServerChannelMessageService._require_channel_access` 的语义：server member 可访问 public channel，private channel 必须是 active channel member。agent reaction 权限基于 session runtime context：

- 通过 `session_id` 解析 `config_snapshot.server_id/channel_id/agent_identity_id`
- 验证 agent 是该 channel 的 active member
- 验证目标 message 属于同一个 channel
- agent 只能以自己的 `agent_identity_id` 贴 reaction

**涉及文件：**

- `backend/app/services/server_channel_message_reaction_service.py`
- `backend/app/services/channel_artifact_service.py` - 可参考 `_resolve_runtime_scope`
- `backend/app/repositories/server_channel_agent_member_repository.py`

**验收标准：**

- [x] 用户不能给无权访问的频道消息贴 reaction
- [x] agent 不能对非当前 channel 的消息贴 reaction
- [x] agent tool 不接受 actor 身份参数

---

## Phase 1: 建立后端 reaction 持久化、聚合与用户 API

### 目标

让人类用户可以通过公开 API 添加/取消 reaction，并让消息列表和 thread 响应返回稳定聚合数据。

### 任务清单

#### 1.1 新增 repository 与 service

**描述：** 新增 repository 负责数据库 CRUD 和批量聚合，service 负责权限、规范化、事务与响应构造。建议最小方法：

- `upsert_user_reaction`
- `delete_user_reaction`
- `upsert_agent_reaction`
- `delete_agent_reaction`
- `list_grouped_by_messages(message_ids)`

聚合响应按 message id 返回 reaction groups，每组包含：

- `emoji`
- `count`
- `reacted_by_current_user`
- `reacted_by_current_agent`，仅 internal/runtime 或调试场景需要时返回
- `actors`，第一版可限制最多 5 个 preview actor，避免消息列表过重

**涉及文件：**

- `backend/app/repositories/server_channel_message_reaction_repository.py`
- `backend/app/services/server_channel_message_reaction_service.py`
- `backend/app/schemas/server_channel_message_reaction.py`

**验收标准：**

- [x] add reaction 幂等，重复添加不会增加 count
- [x] remove reaction 幂等，不存在时返回成功或明确 no-op
- [x] 聚合查询支持一次传入多条 message id

#### 1.2 扩展消息响应 schema

**描述：** 在 `ServerChannelMessageResponse` 新增 `reactions: list[ServerChannelMessageReactionGroupResponse] = []`。`list_messages` 和 `get_thread` 批量加载 reaction 聚合后注入 `_build_message_response`。

推荐响应结构：

```json
{
  "emoji": "👍",
  "count": 3,
  "reacted_by_current_user": true,
  "actors": [
    {
      "actor_type": "user",
      "user_id": "user_123",
      "user": { "user_id": "user_123", "display_name": "Alice" }
    },
    {
      "actor_type": "agent",
      "agent_identity_id": "00000000-0000-0000-0000-000000000000",
      "agent_handle": "reviewer",
      "agent_label": "Reviewer"
    }
  ]
}
```

**涉及文件：**

- `backend/app/schemas/server_channel_message.py`
- `backend/app/services/server_channel_message_service.py`
- `backend/app/repositories/server_channel_message_repository.py`

**验收标准：**

- [x] 频道根消息列表返回 reaction groups
- [x] thread root 和 replies 返回 reaction groups
- [x] 当前用户自己的 reaction 有布尔标记，前端无需重复推导

#### 1.3 新增公开 reaction API

**描述：** 在频道消息路由下新增用户侧 API：

- `PUT /servers/{server_id}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}`
- `DELETE /servers/{server_id}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}`

如果路径 emoji 编码处理不稳定，可以改用 body：

- `POST /servers/{server_id}/channels/{channel_id}/messages/{message_id}/reactions`，body `{ "emoji": "👍" }`
- `DELETE /servers/{server_id}/channels/{channel_id}/messages/{message_id}/reactions`，body `{ "emoji": "👍" }`

优先建议 body 方案，避免 emoji path encoding 和代理层兼容问题。

**涉及文件：**

- `backend/app/api/v1/server_channel_messages.py`
- `backend/app/schemas/server_channel_message_reaction.py`
- `backend/app/services/server_channel_message_reaction_service.py`

**验收标准：**

- [x] 公开 API 可添加当前用户 reaction
- [x] 公开 API 可取消当前用户 reaction
- [x] 目标 message 不在当前 channel 时返回 not found 或 bad request

---

## Phase 2: 建立 agent-facing reaction runtime tools

### 目标

让频道内 agent 可以用结构化 tool 对频道消息贴表情或撤销表情，并复用当前 channel tool 的 runtime scope 和 internal API 模式。

### 任务清单

#### 2.1 新增 backend internal channel runtime reaction API

**描述：** 新增 executor-manager 可调用的 internal API，通过 `session_id` 解析当前 agent runtime scope，并调用 reaction service。路径应与统一 channel runtime internal API 对齐；service 层仍保持 reaction 专属边界。

- `POST /api/v1/internal/channel-runtime/reactions/add`
- `POST /api/v1/internal/channel-runtime/reactions/remove`

请求 body：

```json
{
  "message_id": "00000000-0000-0000-0000-000000000000",
  "emoji": "👍"
}
```

**涉及文件：**

- `backend/app/api/v1/internal_channel_runtime.py`
- `backend/app/api/v1/internal_channel_message_reactions.py` - 如保留，只作为 runtime route 内部拆分文件
- `backend/app/api/v1/__init__.py`
- `backend/app/schemas/server_channel_message_reaction.py`
- `backend/app/services/server_channel_message_reaction_service.py`

**验收标准：**

- [x] internal API 只接受 internal token
- [x] actor identity 来自 session snapshot，不来自 body
- [x] 目标 message 必须属于当前 channel

#### 2.2 新增 executor-manager 统一 channel runtime 代理入口

**描述：** 按 `23-unified-channel-runtime-tools-plan.md` 的统一代理前缀，在 executor-manager 增加 reaction 代理路由，把 executor tool 请求转发到 backend internal API。不要再新增独立 `agent_channel_reactions.py` 作为长期入口；如果实现期为了文件拆分保留该文件，也应挂在统一 `/api/v1/agent-channel-runtime/*` 路径下。

建议路径：

- `POST /api/v1/agent-channel-runtime/reactions/add`
- `POST /api/v1/agent-channel-runtime/reactions/remove`

**涉及文件：**

- `executor_manager/app/api/v1/agent_channel_runtime.py`
- `executor_manager/app/api/v1/agent_channel_reactions.py` - 如保留，只作为 runtime route 的内部拆分文件
- `executor_manager/app/api/v1/__init__.py`
- `executor_manager/app/services/backend_client.py`

**验收标准：**

- [x] 代理请求自动带 internal token 到 backend
- [x] trace headers 按现有 `_trace_headers` 模式透传

#### 2.3 通过统一 channel runtime 注入 reaction MCP tools

**描述：** 在 executor 的统一 channel runtime tool surface 中增加 reaction tools。不要新增单独的 `__poco_channel_reactions` MCP server；如果当前实现还保留 `channel_tasks.py` / `channel_artifacts.py` 的分散文件结构，reaction 第一版也应通过 `ChannelRuntimeClient` facade 对外暴露，后续由统一 channel runtime plan 负责收敛文件布局。

建议工具：

- `add_channel_message_reaction(message_id: str, emoji: str)`
- `remove_channel_message_reaction(message_id: str, emoji: str)`

注入条件与 channel task/artifact tools 一致：`server_id && channel_id && agent_identity_id`。prompt appendix 增加简短约束：

- reaction 是轻量反馈，不等同于回复消息
- 只能对当前 channel 可见消息操作
- 不要声称已 reaction，除非 tool 调用成功

**涉及文件：**

- `executor/app/core/channel_runtime.py` - 新增或扩展统一 channel runtime client / MCP server
- `executor/app/core/channel_reactions.py` - 如保留，作为 runtime facade 内部子模块，不直接独立注入
- `executor/app/core/engine.py`
- `executor/app/api/v1/task.py`
- `executor/tests/test_engine_channel_reaction_tools.py`

**验收标准：**

- [x] channel-scoped run 自动注入统一 channel runtime MCP server
- [x] 非 channel run 不注入 reaction tools
- [x] tool 参数不包含 server/channel/agent 身份
- [x] executor 不新增独立 `__poco_channel_reactions` 注入 key

---

## Phase 3: 接入频道消息 UI 与乐观交互

### 目标

在频道消息列表、搜索/inbox 列表和 thread drawer 中展示 reaction groups，并支持用户通过消息按钮组添加或取消常用 emoji。

### 任务清单

#### 3.1 扩展前端 API 与类型

**描述：** 前端模型新增 reaction 类型，并在 `mapConversationMessage` 中映射后端 `reactions` 字段。新增 API 方法：

- `addMessageReaction(serverId, channelId, messageId, emoji)`
- `removeMessageReaction(serverId, channelId, messageId, emoji)`

**涉及文件：**

- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/api/servers-api.ts`

**验收标准：**

- [x] `ServerConversationMessage` 包含 `reactions`
- [x] API 方法不暴露后端 snake_case 给 UI 层

#### 3.2 在 MessageRow 渲染 reaction bar 与添加表情入口

**描述：** 在消息正文下方渲染 compact reaction bar：

- 已有 reaction group 显示为 `emoji + count`
- 当前用户已 reaction 的 group 使用 selected 状态
- 点击已选 group 取消，点击未选 group 添加
- hover / focus message action toolbar 增加一个“添加表情”的 icon button，优先使用项目现有 icon 体系中的 smile / reaction 图标
- emoji icon button 不显示文字，只通过 tooltip 和 aria-label 表达含义
- 点击 icon button 后，在该按钮组下方弹出一个轻量悬浮面板；面板相对按钮组定位，而不是相对页面居中
- 悬浮面板内展示预设 emoji 网格，每个 emoji 是固定尺寸 icon button
- 点击面板里的 emoji 后立即关闭面板，并触发对应 add/remove reaction 逻辑
- 点击面板外部、按 Escape、切换频道或打开其他消息的 picker 时关闭当前面板

第一版 emoji picker 使用固定常用集合，例如 `👍`、`✅`、`👀`、`❤️`、`🎉`、`🚀`。暂不做搜索、自定义 emoji、最近使用或肤色选择。所有按钮 aria-label 和 tooltip 文案走 i18n。

布局约束：

- reaction bar 位于消息正文下方，只有已经存在 reaction groups 时常驻展示
- 添加表情 icon 只属于消息 action toolbar，不在每条消息正文下方额外常驻一个“添加”按钮
- 悬浮面板宽度保持紧凑，避免遮挡消息正文；在窄屏下可自动贴边但仍锚定当前按钮组
- 面板层级应高于消息列表内容，但低于全局 modal / drawer
- thread drawer 内复用同一个组件和交互，不单独设计另一套 picker

**涉及文件：**

- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/features/servers/ui/message-reaction-picker.tsx` - 如拆分组件
- `frontend/features/servers/ui/conversation-panels.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [x] 主频道消息可以添加/取消 reaction
- [x] thread drawer 内消息可以添加/取消 reaction
- [x] search/inbox/saved 紧凑消息至少能显示 reaction groups
- [x] 消息 action toolbar 有添加表情 icon button，点击后 picker 悬浮在按钮组下方
- [x] picker 支持外部点击、Escape、选择 emoji 后关闭
- [x] 所有新增用户可见文案走 i18n

#### 3.3 增加乐观更新与刷新策略

**描述：** 点击 reaction 后先本地更新当前消息的 reaction groups，再调用 API；失败时回滚并 toast。当前频道消息数据仍由页面层统一持有，避免 `MessageRow` 自己维护服务器状态。

注意 thread drawer 与主列表可能同时持有同一条 root message，需要在页面状态里按 message id 合并更新，避免一个视图 stale。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/features/servers/lib/` - 如需要新增 reaction 更新 helper

**验收标准：**

- [x] reaction 点击后 UI 立即反馈
- [x] API 失败会回滚并提示
- [x] 主列表和 thread drawer 的同一消息 reaction 状态保持一致

---

## Phase 4: 补齐测试、迁移验证与体验收口

### 目标

用定向测试锁住后端契约、agent runtime tool 注入和前端静态质量，避免 reaction 聚合和权限出现回归。

### 任务清单

#### 4.1 后端测试

**描述：** 覆盖 model/service/API 的核心路径：

- 用户 add/remove 幂等
- private channel 权限
- root message 和 reply 都能 reaction
- list_messages / get_thread 返回 reaction groups
- agent internal API 使用 session scope，并拒绝跨 channel message

**涉及文件：**

- `backend/tests/test_server_channel_message_reaction_service.py`
- `backend/tests/test_server_channel_message_reaction_api.py`
- `backend/tests/test_internal_channel_message_reactions_api.py`
- `backend/tests/test_server_channel_message_service.py`

**验收标准：**

- [x] 新增后端定向测试通过
- [x] 现有 server channel message 测试不回归

#### 4.2 executor 与 executor-manager 测试

**描述：** 覆盖 MCP 注入、tool 参数校验和代理调用：

- `AgentExecutor` 只在 channel scope 注入统一 channel runtime MCP，并且其中包含 reaction tools
- prompt contract 包含 reaction tool 使用约束
- executor-manager 代理将 `session_id` 与 payload 转给 backend client

**涉及文件：**

- `executor/tests/test_engine_channel_reaction_tools.py`
- `executor_manager/tests/` - 如现有测试结构允许，新增 API/backend client 测试

**验收标准：**

- [x] executor channel runtime reaction tool 注入测试通过
- [x] executor-manager reaction proxy 测试通过

#### 4.3 前端质量门禁

**描述：** 完成前端类型、lint 和关键交互检查。

**涉及文件：**

- `frontend/features/servers/**`
- `frontend/lib/i18n/locales/**/translation.json`

**验收标准：**

- [x] `cd frontend && pnpm lint` 通过
- [x] 频道消息、thread drawer、search/inbox 紧凑消息没有布局溢出
- [x] reaction 文案在中英文 locale 下都有值

#### 4.4 迁移验证

**描述：** 使用 Alembic autogenerate 生成迁移后人工审查，确认约束、索引和降级逻辑合理。

建议索引：

- `ix_server_channel_message_reactions_message_id`
- `ix_server_channel_message_reactions_channel_id`
- `ix_server_channel_message_reactions_actor_user_id`
- `ix_server_channel_message_reactions_actor_agent_identity_id`
- unique constraint for one actor / one emoji / one message

**涉及文件：**

- `backend/alembic/versions/`

**验收标准：**

- [x] `cd backend && uv run -m alembic upgrade head` 通过
- [x] migration downgrade 不遗留表或索引

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| ---- | ---- | -------- |
| emoji path encoding 不稳定 | DELETE/PUT 路由可能在代理层或浏览器编码中出错 | 公开 API 优先使用 JSON body 传 `emoji` |
| reaction 聚合造成 N+1 查询 | 消息列表加载变慢 | repository 提供批量 `list_grouped_by_messages`，service 一次注入 |
| agent 伪造 actor 身份 | 权限和审计失真 | internal API 只从 `session_id` 的 config snapshot 解析 agent identity，不接受 body actor |
| message 与 channel 不匹配 | 可跨频道操作 reaction | service 每次校验 message.channel_id 等于当前 channel |
| 前端多个视图状态不一致 | 主列表和 thread drawer reaction 显示冲突 | 页面层提供按 message id 的统一 reaction patch helper |
| reaction actor preview 过重 | 消息列表响应膨胀 | actors preview 限制数量，完整 actor list 留给未来详情接口 |
| reaction picker 遮挡消息或在滚动容器中错位 | 用户难以确认 reaction 作用对象 | picker 锚定消息 action toolbar，滚动/切换消息时关闭，并在窄屏下贴边 |
| channel tools 注入继续分散 | executor MCP 注入层越来越难维护 | reaction tools 必须进入统一 channel runtime MCP server，不新增独立 reaction server key |

---

## 总结

这次改动的核心问题是：频道消息需要轻量反馈机制，而 reaction 是独立的多人/多 agent 关系，不应混进消息正文。实现上建议新增 `server_channel_message_reactions` 表来表达 `message x emoji x actor`，在人类 API 中按当前用户落库，在 agent runtime 中通过统一 channel runtime MCP tool 以当前 agent 身份落库。消息读取接口返回聚合后的 reaction groups，前端在 `MessageRow` 里展示 reaction bar，并在消息 action toolbar 的添加表情 icon 下方弹出预设 emoji picker。

## 验证记录

- 2026-05-08：`cd backend && uv run python -m unittest tests.test_server_channel_message_reaction_service tests.test_server_channel_message_reaction_api tests.test_internal_channel_message_reactions_api tests.test_server_channel_message_service` 通过。
- 2026-05-08：`cd executor && uv run python -m unittest tests.test_engine_channel_reaction_tools` 通过。
- 2026-05-08：`cd executor_manager && uv run python -m unittest tests.test_agent_channel_runtime_api` 通过。
- 2026-05-08：`cd frontend && pnpm lint` 与 `cd frontend && pnpm build` 通过。
- 2026-05-08：根据验收 diff comment 收口 reaction UI 细节；`cd frontend && pnpm lint` 通过，并用本地 Chrome / Computer Use 确认 picker 预设包含 `👀`。
- 2026-05-08：`cd backend && uv run -m alembic upgrade head` 通过；`downgrade -1 && upgrade head` 通过。
- 2026-05-08：`cd backend && uv run -m alembic check` 仍报告既有 schema drift（`activity_logs`、`workspace_issues`、`agent_assignments` 索引差异），不属于本 reaction 迁移。
- 2026-05-08：`cd frontend && pnpm test` 仍有既有失败：`features/projects/actions/project-actions.test.ts`、`features/task-composer/api/task-submit-api.test.ts` 的 `@/features` alias 解析失败，以及 `features/workspaces/lib/team-sections.test.ts` 的旧 invites 断言失败。
