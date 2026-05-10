# Channel shared context and published artifacts plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-05 |
| **预期改动范围** | backend channel shared context / published artifacts model and APIs / agent trigger context assembly / frontend conversation fourth drawer / file preview and grouped tree / permissions and visibility rules |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 固化共享边界与对象模型 (2026-05-06)
- [x] Phase 1: 建立频道公共成果树的后端模型与授权 (2026-05-06)
- [x] Phase 2: 建立右侧第四抽屉文件树与预览体验 (2026-05-06)
- [x] Phase 3: 把公共成果树接入 agent 可读上下文 (2026-05-06)
- [x] Phase 4: 补齐验证与风险收口 (2026-05-06)

## 实现记录

- 2026-05-06: 计划进入执行阶段并迁移到 `specs/active/`。
- 2026-05-06: 第一阶段默认只共享 `published artifacts`，不把 `session workspace`、`persistent state` 或 `local_mount` 本体直接暴露给频道。
- 2026-05-06: 默认自动公开的初始来源收紧为 `workspace export manifest` 中可见文件与后续显式发布入口；`MEMORY.md`、`notes/`、`state/`、`/agent_state` 与 raw `local_mount` 路径明确排除。
- 2026-05-06: Phase 3 的初始触发范围固定为频道 `@agent` 和 agent DM，不引入“所有频道消息都自动触发”。
- 2026-05-06: 已新增 `channel_artifacts` 后端模型、迁移、repository、service 和频道读取 API；workspace export ready 后会自动把当前 session 的可见文件索引同步到频道公共成果树。
- 2026-05-06: 前端频道页已新增 `Shared files` 第四抽屉，复用现有 `FileSidebar` 与 `DocumentViewer`，支持按 agent 分组浏览树形文件和预览公开材料。
- 2026-05-06: 已新增 `ChannelSharedContextService` 与 `ServerAgentTriggerService`；频道 `@agent` 和 agent DM 现会以 `persistent` runtime 模式复用现有 task enqueue/session queue 链路触发，并把公共成果树中的文本材料纳入共享上下文 prompt。
- 2026-05-06: 最终验证已完成：`cd backend && uv run -m alembic upgrade head`、`cd backend && uv run python -m unittest tests.test_server_channel_artifact_api tests.test_channel_artifact_service tests.test_server_channel_api tests.test_server_channel_message_api tests.test_server_channel_message_service tests.test_channel_shared_context_service tests.test_server_agent_trigger_service`、`cd frontend && pnpm lint`、`cd frontend && pnpm build`。

---

## 背景

### 问题陈述

当前 Poco 已经把团队协作主线切到 `server / conversation / task / agent`，频道中的人类和 agent 可以共享消息、thread 和任务流转。但系统仍缺少一个关键协作面：频道内的公共材料视图。

如果没有这层公共材料视图，频道协作会停留在自然语言层：

- agent A 生成的文件只能留在它自己的 session workspace 或私有状态里
- 人类或 agent B 即使知道“它生成了一份方案”，也没有稳定入口去读取
- 协作链路重新退化成贴文本、复制链接或人工转述

最直接的补法是“让整个频道共享一个文件系统”，但这会把 `session workspace`、`agent persistent state` 和 `local_mount` 混成一个公共边界，带来权限、冲突和隐私问题。根据最新讨论，当前阶段更合理的目标不是做共享可写底层盘，而是先做：

1. 频道共享上下文
2. 频道共享公共成果树

同时，用户还提出了一个很强的产品偏好：为了让 agent 之间真正协作，频道内的新材料应默认公开展示，并且能按 agent 清晰分组，供频道中其他 agent 直接读取和预览。

### 目标

这份 spec 的目标是为频道协作补齐“共享上下文 + 公共成果树”两层能力，重点包括：

- 频道内增加最右侧第四抽屉，展示公共成果树和文件预览
- 默认自动公开新的协作材料，并按 agent 分组展示
- 确保频道内其他 agent 能把这些公开材料作为可读上下文继续协作
- 明确 `session workspace / persistent state / local_mount / published artifacts` 的边界

### 非目标

以下内容不在本次范围内：

- 不引入频道共享可写文件系统
- 不把 local mount 本体升级成频道公共盘
- 不公开 agent 私有 `MEMORY.md`、notes、状态文件
- 不解决多 agent 对同一底层目录的并发写入问题

### 关键洞察

#### 1. 公共成果树是协作输入面，不是公共写盘

第一阶段最需要的是“别人能看见、能预览、能读取”，而不是“所有人都能直接写同一目录”。把公共成果树定义成只读协作输入面，可以在不破坏当前执行边界的情况下显著增强协作。

#### 2. 自动公开必须基于成果语义，而不是文件系统语义

如果简单按“所有文件都公开”来实现，会把 agent 私有状态与本地挂载目录一起卷进来。系统必须先判断什么算协作成果，再决定什么自动进入公共成果树。

#### 3. 右侧第四抽屉是最自然的承载位

当前 chat-first 结构已经稳定使用右侧抽屉承载 thread、agent、task detail。公共成果树作为更长期、更跨 agent 的协作对象，适合作为第四抽屉存在，而不是打散到消息流或 task tab 里。

---

## Phase 0: 固化共享边界与对象模型

### 目标

先把“共享什么、不共享什么”说清楚，避免实现时重新滑向共享底层文件系统。

### 任务清单

#### 0.1 定义四类边界

**描述：** 明确以下边界：

- `session workspace`：单次执行工作区
- `agent persistent state`：agent 私有长期状态
- `local_mount`：session 级本地目录授权
- `published artifacts`：频道共享成果树

**涉及文件：**

- `specs/constitution/2026-05-05-channel-shared-context-and-artifacts.md`
- `specs/active/14-channel-shared-context-and-published-artifacts-plan.md`

**验收标准：**

- [x] spec 明确四类边界的职责
- [x] spec 明确本次只新增 `published artifacts`

#### 0.2 定义“默认自动公开”的范围

**描述：** 约束自动公开只覆盖协作成果，至少不包括：

- `MEMORY.md`
- `notes/`
- `state/`
- local mount 原始目录本体

第一版默认公开的候选对象可包括：

- session workspace 中新增或更新的用户可见文件
- executor 导出的 artifacts
- 显式发布的文件或目录

第一阶段实现默认收紧为：

- 以 `workspace export manifest` 中可见文件为自动公开主来源
- 明确排除 `/agent_state`、`MEMORY.md`、`notes/`、`state/`
- 不把 local mount 原始目录直接纳入公共成果树，只允许其导出的结果被公开

**涉及文件：**

- `specs/active/14-channel-shared-context-and-published-artifacts-plan.md`

**验收标准：**

- [x] spec 明确自动公开的纳入与排除规则
- [x] spec 明确“公开的是成果，不是私有状态”

---

## Phase 1: 建立频道公共成果树的后端模型与授权

### 目标

建立公共成果树的数据模型、归属关系与访问授权，为前端第四抽屉和 agent 读取提供稳定后端契约。

### 任务清单

#### 1.1 建立公共成果模型

**描述：** 新增频道级共享成果对象，例如 `ChannelArtifact`，至少表达：

- `artifact_id`
- `server_id`
- `channel_id`
- `agent_identity_id | user_id`
- `source_session_id`
- `source_kind`
- `logical_path`
- `display_name`
- `mime_type`
- `storage_key | file_url`
- `is_previewable`
- `created_at`

**涉及文件：**

- `backend/app/models/` - 新增共享成果模型
- `backend/app/schemas/` - 新增成果响应 schema
- `backend/alembic/versions/` - 新增迁移

**验收标准：**

- [x] 后端存在频道共享成果模型
- [x] 归属关系能区分来源 agent 或来源用户

#### 1.2 建立自动公开采集入口

**描述：** 在 session 导出、artifact 生成或显式发布路径中，把符合规则的新材料写入频道公共成果表。第一版优先复用已有 workspace export / manifest 能力，而不是扫描整个底层文件系统。

**涉及文件：**

- `backend/app/services/callback_service.py`
- `backend/app/services/workspace_archive_service.py`
- 新增 `backend/app/services/channel_artifact_service.py`

**验收标准：**

- [x] 新材料可自动进入公共成果树
- [x] 不会自动采集 agent 私有状态目录

#### 1.3 建立频道级访问授权

**描述：** 公共成果树的读取授权基于频道成员身份，而不是 session owner。确保：

- 频道成员能读公共成果
- 同频道 agent 后续可被注入这些成果作为上下文
- 非频道成员不能读

**涉及文件：**

- `backend/app/api/v1/` - 新增 channel artifacts API
- `backend/app/services/` - 增加 channel membership 授权检查

**验收标准：**

- [x] 授权边界按 channel member 生效
- [x] 不再要求读取者必须是原 session owner

---

## Phase 2: 建立右侧第四抽屉文件树与预览体验

### 目标

把公共成果树接入频道 UI，形成可浏览、可预览、可按 agent 分组的第四抽屉。

### 任务清单

#### 2.1 定义第四抽屉结构

**描述：** 频道最右侧新增 `Shared files` / `Published artifacts` 抽屉，至少支持：

- 按 agent 分组
- agent 分组之间用视觉分隔区分
- 展示树形文件结构
- 当前文件预览

**涉及文件：**

- `frontend/features/servers/ui/` - 新增第四抽屉组件
- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/api/servers-api.ts`

**验收标准：**

- [x] 第四抽屉能列出按 agent 分组的共享材料
- [x] UI 中 agent 分组清晰可辨

#### 2.2 复用现有文件预览能力

**描述：** 尽量复用现有 chat artifacts/document viewer，而不是重写一套预览引擎。共享成果树只需要接入新的数据源和权限路径。

**涉及文件：**

- `frontend/features/chat/components/execution/file-panel/`
- `frontend/features/servers/ui/`

**验收标准：**

- [x] 文本、Markdown、图片等常见文件可预览
- [x] 不引入第二套独立预览体系

#### 2.3 明确“默认公开”的前端表达

**描述：** 在 UI 文案和交互上明确：

- 这些文件是频道共享材料
- 默认对当前频道公开
- 来源 agent / user 可见

**涉及文件：**

- `frontend/lib/i18n/locales/*/translation.json`
- `frontend/features/servers/ui/`

**验收标准：**

- [x] 用户能明确知道这是频道公共材料
- [x] 来源归属和公开语义有明确文案

---

## Phase 3: 把公共成果树接入 agent 可读上下文

### 目标

确保频道中的其他 agent 不只是“看见有文件”，而是能在后续被触发时把这些共享材料读进上下文继续协作。

### 任务清单

#### 3.1 定义 shared context 组装规则

**描述：** 被频道 mention 或 DM 触发的 agent，在组装上下文时可读取：

- 最近消息
- 当前 thread
- channel summary
- 公开成果树索引
- 相关公开文件内容（按大小和数量做限制）

**涉及文件：**

- 新增 `backend/app/services/channel_shared_context_service.py`
- agent 触发链路相关 service

**验收标准：**

- [x] shared context 规则对 agent 可解释
- [x] 公开成果可被纳入后续运行上下文

#### 3.2 建立共享材料读取限制

**描述：** 读取公共成果树时要限制：

- 单次注入文件数量
- 单文件大小
- 二进制文件处理方式
- 顺序与优先级

**涉及文件：**

- `backend/app/services/channel_shared_context_service.py`

**验收标准：**

- [x] 不会因共享材料无限扩张上下文
- [x] 文本类文件优先可读，二进制类可回退为元信息

#### 3.3 约束 local mount 和私有状态不可被共享读取

**描述：** 即使 agent 本次运行使用了 local mount 或自己的 persistent state，其他 agent 也只能读取被纳入公共成果树的材料，不能越权直接读取底层私有路径。

**涉及文件：**

- `backend/app/services/channel_shared_context_service.py`
- 相关权限与材料采集逻辑

**验收标准：**

- [x] 共享读取只发生在 published artifacts 边界内
- [x] private state 和 local mount 本体不会被跨 agent 直接读取

---

## Phase 4: 补齐验证与风险收口

### 目标

在正式实现前明确验证面、主要风险和收口方式。

### 任务清单

#### 4.1 验证面设计

**描述：** 至少覆盖：

- 公共成果自动入树
- 频道成员读取授权
- 第四抽屉树形展示和预览
- 不同 agent 读取已公开材料
- 私有状态未泄露

**涉及文件：**

- backend tests
- frontend 手工验证脚本或既有 lint/build 流程

**验收标准：**

- [x] spec 明确主要验证面
- [x] spec 明确私有状态泄露属于高优先级回归风险

#### 4.2 风险收口

**描述：** 收敛以下高风险点：

- 自动公开误把私有文件纳入公共树
- 频道公共树无限膨胀
- 多 agent 读取到过期材料
- UI 第四抽屉与现有三列结构冲突

**涉及文件：**

- `specs/draft/14-channel-shared-context-and-published-artifacts-plan.md`

**验收标准：**

- [x] spec 中对主要风险都有缓解策略

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 自动公开误纳入 `MEMORY.md` 或状态文件 | 泄露 agent 私有长期记忆 | 以成果采集规则为准，不扫描私有状态目录 |
| local mount 被错误视为频道公共盘 | 暴露用户真实本地目录 | local mount 保持 session-scoped，只公开导出的成果 |
| 公共成果树随运行无限增长 | 抽屉难以使用，上下文成本失控 | 引入分组、排序、分页和上下文注入上限 |
| 不同 agent 读取到旧材料 | 协作继续基于过期上下文 | 记录来源 session、更新时间和归属 agent |
| 第四抽屉破坏现有 conversation 壳子 | UI 复杂度上升 | 保持前三列不变，把共享成果树作为明确的第四抽屉能力 |

---

## 总结

这份 spec 解决的是“频道里如何共享协作材料”而不是“如何共享底层可写文件系统”。核心思路是先做两层共享：共享上下文、共享公共成果树。新材料默认自动公开到频道公共成果树，并按 agent 分组展示，供频道中人类和 agent 读取与预览；但 agent 私有持久状态、本地挂载目录和临时状态快照继续保留各自边界，不直接变成频道公共盘。
