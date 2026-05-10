# Server channel collaboration foundation plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-04 |
| **预期改动范围** | backend collaboration models / backend APIs / frontend shell navigation / i18n copy / migration scripts / tests |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 收敛替换范围与命名边界 (2026-05-04)
- [x] Phase 1: 建立 `server / channel` 基础数据模型与 API (2026-05-04)
- [x] Phase 2: 建立 `message / thread` 协作基础层 (2026-05-04)
- [x] Phase 3: 切换前端导航与协作主入口 (2026-05-04)
- [x] Phase 4: 验收与旧入口收口 (2026-05-04, pending user acceptance)

---

## 背景

### 问题陈述

`2026-05-04-server-channel-agent-persistence.md` 已经把新的产品共识正式记录下来：Poco 的 MVP 主线不再维持 `workspace / board / issue` 作为外部协作语义，而是直接切换到 `server / channel / task / agent`。这意味着现有的 workspace/team 页面虽然仍可作为实现参考，但不再是未来协作面的命名和信息架构基线。

当前代码库里已经存在几类相关基础：

- `backend/app/models/workspace*.py`、`workspace_board.py`、`workspace_issue.py` 构成了旧的团队协作主干
- `backend/app/models/im.py`、`services/im.py` 提供了一套偏 IM 集成的 channel / event 基础设施
- `frontend/app/[lng]/(shell)/team/*` 与 `frontend/features/workspaces/*` 提供了旧 team shell 与看板页面

问题在于，这三套能力没有统一收敛成“产品主协作面”。如果直接开始写 task、agent identity、persistent runtime，而不先建立 `server / channel / message / thread` 的基础层，后续每一层都会被迫继续借用旧的 workspace/team 语义，造成实现时的双语义混用。

### 目标

这份 plan 的目标是建立新的协作基础层，并把它变成后续所有 task / agent 能力的稳定依赖。重点包括：

- 把 `server / channel` 明确成新的协作空间边界
- 把 `message / thread` 明确成新的交互基础层
- 在前端 shell 中让用户先感知到 server 和 channel，而不是旧的 workspace/team 入口
- 在当前未上线前提下，接受直接语义切换，而不是保留冗余向后兼容外壳

### 关键洞察

#### 1. 这次不是“给 workspace 起别名”，而是协作主线切换

如果只是把 `workspace` 在前端文案层改成 `server`，但数据模型、API 路径、页面组织、导航层级仍围绕旧心智，用户最终感知到的依然是旧产品。这份 plan 处理的是产品主线切换，不是文案替换。

#### 2. `message / thread` 必须早于 task 落地

新的任务语义不再是独立 issue 页面上的卡片，而是 channel 中可追踪的工作项。如果消息和 thread 还不存在，task 只能继续借旧 issue 模型生长，后续又要返工一次。

#### 3. 可以复用现有 IM 能力，但不能复用旧 IM 的产品语义

`backend/app/models/im.py` 和 `services/im.py` 已经提供了一部分事件、channel、通知和内嵌 backend 能力，这些在实现层可以借鉴；但产品层仍然需要新的 server/channel/message/thread 一致模型，不能继续沿用“外部 IM 适配层”的语义边界。

---

## Phase 0: 收敛替换范围与命名边界

### 目标

先明确这次 plan 到底替换哪些旧概念、保留哪些实现层资产，避免边做边猜。

### 新旧概念映射

| 旧概念 | 新概念 | 本计划中的处理方式 |
| --- | --- | --- |
| `workspace` | `server` | 新产品层以 server 作为协作空间、成员、邀请和默认个人容器的命名边界；旧 workspace 代码仅可作为迁移参考或内部兼容层。 |
| `workspace_member` | `server_member` | 成员角色仍保留 `owner / admin / member`，但新 API、schema、前端文案必须使用 server member。 |
| `workspace_invite` | `server_invite` | 邀请流程迁移到 server invite；旧 workspace invite 不再作为新增入口。 |
| `team` | server 下的协作导航 | 前端主导航不再暴露 Team 作为顶层心智，改为先选择 server，再进入 channel。 |
| `board` | task view（后续 spec） | 本计划不继续扩展 board 作为组织上下文，只允许旧 issues 页面在迁移期读取已有 board 数据。 |
| `issue` | task / message-thread 工作项（后续 spec） | 新协作面不再从 issue 第一视角扩展；任务创建与状态广播应落到 channel message / thread 基础层。 |
| IM `Channel` | 外部 IM 适配 channel | 保留为 IM 集成实现细节，不作为 Poco 产品层 channel 的数据模型或 API 命名来源。 |

### 禁止双语义区

从本计划开始，新增产品层代码不得继续引入以下命名作为主语义：

- 新 public API 路径不得新增 `/workspaces`、`/workspace-*`、`/team` 作为 server/channel foundation 的入口。
- 新前端页面、导航、i18n key 不得继续把协作空间称为 workspace/team；与 sandbox 文件系统相关的 workspace 术语不在本禁区内。
- 新业务 schema、service、repository 不得以 workspace/team 命名承接 server/channel 能力。
- 旧 workspace/team/board/issue 模块在迁移期只允许作为兼容读写或实现参考，不继续承载 task、agent identity、persistent runtime 的新能力。

### 直接切换原则

当前 Poco 尚未上线，本计划按“直接语义切换”执行：

- server/channel foundation 使用新的 public API、schema 和前端入口，不为旧 workspace/team 命名保留长期双入口。
- 已存在的 workspace 数据迁移到 server 表结构时，可以保留一次性 Alembic 迁移、数据 backfill 脚本和短期内部适配代码。
- 迁移脚本的职责只限于把已有个人/共享空间、成员、邀请关系搬到新模型；新功能完成后不得继续把旧表当作写入源。
- 外部 IM 集成的 channel 表保持原职责，后续如果需要与产品层 channel 关联，应通过显式映射字段或独立关联表完成，不能共享同一张表混用语义。

### 任务清单

#### 0.1 定义新旧概念映射与禁止双语义区

**描述：** 明确哪些概念被新主线接管，哪些旧概念只能保留在实现内部，不得继续出现在新的产品层 API、页面和文案中。

**需要明确的映射：**

- `workspace` → `server`
- `team` → `server` 下的成员与导航语义
- `board` → 不再作为组织上下文主对象，后续下沉为 task view
- `issue` → 不再作为新协作面的第一视角

**非目标：**

- 不在此阶段定义 task 字段和 agent runtime 规则
- 不处理 daemon / local runner

**验收标准：**

- [x] spec 中明确列出新旧概念映射
- [x] spec 中明确哪些旧语义不得继续出现在新页面和新 API 中

#### 0.2 定义本次直接切换的迁移原则

**描述：** 当前系统尚未上线，因此本计划接受直接切换 public API / frontend route / i18n 语义，而不是为旧命名保留长期双入口。

**验收标准：**

- [x] spec 中明确“未上线前提下允许直接切换，不保留长期双入口”
- [x] spec 中明确实现过程中哪些脚本或一次性迁移仍然需要存在

---

## Phase 1: 建立 `server / channel` 基础数据模型与 API

### 目标

把 server 和 channel 作为新的协作空间边界建立起来，先于 task 和 agent 语义落地。

### 任务清单

#### 1.1 建立 server 与成员模型

**描述：** 引入 `server`、`server_member`、`server_invite` 等新模型，承接旧 `workspace / workspace_member / workspace_invite` 的协作边界职责。

**涉及文件：**

- `backend/app/models/workspace.py` — 评估直接重命名或拆分迁移
- `backend/app/models/workspace_member.py`
- `backend/app/models/workspace_invite.py`
- `backend/app/repositories/workspace_repository.py`
- `backend/app/repositories/workspace_member_repository.py`
- `backend/app/repositories/workspace_invite_repository.py`
- `backend/app/schemas/workspace.py`
- `backend/app/schemas/workspace_member.py`
- `backend/app/schemas/workspace_invite.py`
- `backend/app/api/v1/workspaces.py`
- `backend/app/api/v1/workspace_members.py`
- `backend/app/api/v1/workspace_invites.py`
- `backend/alembic/versions/`

**验收标准：**

- [x] 后端存在 server 级实体和成员关系
- [x] personal / shared 语义在新模型中有明确承接
- [x] server CRUD、成员管理、邀请流程具备明确 API

#### 1.2 建立 channel 与频道成员模型

**描述：** 为每个 server 建立 channel 容器，支持至少 `public / private` 两种 MVP 类型，并预留后续 thread 和 task 的归属边界。

**涉及文件：**

- `backend/app/models/` — 新增 channel、channel_member 等模型
- `backend/app/repositories/`
- `backend/app/schemas/`
- `backend/app/api/v1/` — 新增 channels 相关入口
- `backend/alembic/versions/`

**验收标准：**

- [x] 一个 server 下可创建多个 channel
- [x] channel 具备成员可见性与归属边界
- [x] channel 的归档、加入、离开语义被明确定义

#### 1.3 明确 personal server 的默认初始化

**描述：** 每个用户在新主线下如何获得个人协作空间，必须在这一阶段定死，避免后续 task 和 agent identity 都依赖一个模糊的个人容器语义。

**验收标准：**

- [x] spec 中明确 personal server 的创建时机和默认 channel
- [x] spec 中明确 personal channel 默认不是团队公共可见频道

**实现记录：** `ServerService.ensure_personal_server()` 在用户首次读取 server 列表时创建 personal server，并同步创建 `Personal` private channel；创建 shared server 时同步创建 `general` public channel。

---

## Phase 2: 建立 `message / thread` 协作基础层

### 目标

在 channel 之上建立消息和 thread 能力，为后续 task、system message、agent progress message 提供统一承载层。

### 任务清单

#### 2.1 定义 message 主表与 thread 关系

**描述：** 建立 channel 内消息主表，支持普通消息、system message、后续 task message 扩展，并定义 thread root / reply 关系。

**涉及文件：**

- `backend/app/models/im.py` — 评估复用与迁移边界
- `backend/app/models/` — 新增或重构 message / thread 相关模型
- `backend/app/repositories/im.py`
- `backend/app/schemas/im.py`
- `backend/app/services/im.py`
- `backend/app/services/im_streams.py`
- `backend/app/api/v1/im.py`
- `backend/alembic/versions/`

**验收标准：**

- [x] channel 内存在统一 message 模型
- [x] thread 关系可以表达“主消息 + 回复流”
- [x] system message 与普通消息可区分

**实现记录：** `server_channel_messages` 是产品层 channel 消息主表，`message_type` 区分 `user / system / task`，`thread_root_message_id` 表达主消息与回复流。

#### 2.2 建立 history / send / pagination 基础 API

**描述：** 在当前 MVP 中优先保证消息读写、历史查询、分页和 thread 读取，而不把实时推送作为前置。

**验收标准：**

- [x] 存在 message send / read / thread history API
- [x] 前端可以按 channel 读取消息流
- [x] 当前阶段不要求 WebSocket 成为必选前置

#### 2.3 定义 system message 的职责边界

**描述：** 把 task 创建、认领、状态变更、agent 运行状态这类广播行为预先留给 system message，而不是让它们零散散落在各业务表中。

**验收标准：**

- [x] spec 中明确哪些事件必须落成 system message
- [x] spec 中明确 system message 不是 task 的替代物，而是协作广播层

**system message 边界：**

- task 创建、认领、取消、状态变更必须写入 `message_type = "system"` 的 channel message。
- agent 开始运行、等待用户输入、完成、失败、重试必须写入 `message_type = "system"` 的 channel message。
- system message 只负责广播协作事实和提供 thread 锚点，不替代 task 主表、agent run 主表或权限判断。

---

## Phase 3: 切换前端导航与协作主入口

### 目标

让用户在 shell 中先进入 `server / channel` 语义，而不是继续从旧的 `/team` 结构理解产品。

### 任务清单

#### 3.1 重构 shell 侧边栏与顶层入口

**描述：** 调整 `frontend/components/shell/*` 和 team 路由，使 server / channel 成为新的主导航单元。

**涉及文件：**

- `frontend/components/shell/app-shell.tsx`
- `frontend/components/shell/sidebar/main-sidebar.tsx`
- `frontend/components/shell/sidebar/sidebar-content.tsx`
- `frontend/components/shell/sidebar/hooks/*`
- `frontend/app/[lng]/(shell)/layout.tsx`

**验收标准：**

- [x] shell 中存在 server / channel 导航入口
- [x] 用户可以先选 server，再进入 channel
- [x] 旧 team 导航不再是产品主入口

**实现记录：** shell 顶层导航已从 Team 切换到 Servers，新增 `/servers` 页面先展示 server 列表，再展示所选 server 下的 public/private channel。

#### 3.2 重构 team 路由到新的 server / channel 页面骨架

**描述：** 原 `frontend/app/[lng]/(shell)/team/*` 与 `frontend/features/workspaces/*` 将不再承担最终产品语义，需要逐步让位给新的协作页骨架。

**涉及文件：**

- `frontend/app/[lng]/(shell)/team/layout.tsx`
- `frontend/app/[lng]/(shell)/team/page.tsx`
- `frontend/features/workspaces/*`
- 新的 `frontend/features/servers/*`、`frontend/features/channels/*`（如采用）

**验收标准：**

- [x] 新页面骨架围绕 server / channel 组织
- [x] 旧 team 页面仅作为迁移过渡，不再继续扩功能

---

## Phase 4: 验收与旧入口收口

### 目标

在 foundation 层完成后，确保旧入口不会继续作为新功能默认落点。

### 任务清单

#### 4.1 收口旧 workspace/team public 入口

**描述：** 保留一次性数据迁移和内部兼容代码可以接受，但新的产品层文案、导航和默认 API 入口必须切换完成。

**验收标准：**

- [x] 新增功能不再继续落到旧 workspace/team 命名下
- [x] 旧入口的剩余职责被文档化，避免后续继续扩散

**旧入口剩余职责：**

- `/team` 与 `features/workspaces` 暂时保留为旧 workspace/team/issue 迁移过渡入口，不再作为新协作主入口继续扩展。
- 新增协作基础能力统一落在 `/servers`、`/servers/{server_id}/channels`、`server_*` schema/service/repository/model 命名下。
- `workspace` 术语仍可用于 sandbox 文件系统、旧数据迁移和历史 workspace/team 兼容代码，不用于新的产品层协作入口。

#### 4.2 补齐测试与文档引用

**描述：** 为新的 server/channel foundation 补齐模型、API 和前端导航层的基础测试，并在 spec / constitution 间建立引用关系。

**验收标准：**

- [x] 基础模型与 API 测试存在
- [x] 关键页面路由与导航有 smoke 覆盖
- [x] 本 spec 与 constitution 互相引用清晰

**验证记录：**

- `cd backend && uv run python -m unittest tests.test_server_api tests.test_server_service tests.test_server_channel_message_api tests.test_server_channel_message_service`
- `cd backend && uv run alembic heads && uv run alembic current`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`

**关联决策：** 本 spec 以 `specs/constitution/2026-05-04-server-channel-agent-persistence.md` 为产品命名与持久化主线依据；后续 task/agent/runtime spec 应引用本 foundation 层，不再从旧 workspace/team 语义扩展。

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 直接切换语义导致旧 draft spec 互相打架 | 团队不知道该继续跟哪套主线 | 明确本 spec 作为新的 foundation 主线，并在后续 spec 中引用它 |
| `im.py` 与新 channel/message 模型职责重叠 | 后端出现两套消息体系 | 在 Phase 2 显式定义复用边界，避免继续平行扩展 |
| 前端仍习惯在 `/team` 下继续开发 | 新旧主入口长期并存 | 在 Phase 3 明确 shell 导航切换，旧 team 页面停止扩功能 |

---

## 总结

这份 spec 的作用不是直接实现 task 或 agent，而是先把新的协作地基搭好。只有 `server / channel / message / thread` 成为明确的一致主线，后续 task 工作流、agent identity、persistent runtime 才不会继续长在旧的 workspace/team 语义之上。
