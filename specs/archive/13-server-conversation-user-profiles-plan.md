# Server conversation user profile presentation plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-05 |
| **预期改动范围** | backend auth / server member and message schemas / server conversation frontend / i18n-preserving UI wiring / backend tests / specs |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 固化公开用户资料设计与实施边界 (2026-05-05)
- [x] Phase 1: 扩展后端会话契约以返回公开用户资料 (2026-05-05)
- [x] Phase 2: 接入前端成员、消息和头像展示 (2026-05-05)
- [x] Phase 3: 完成验证并回写 spec 状态 (2026-05-05)

## 实现记录

- 2026-05-05: 已新增 `UserPublicProfileResponse` 与 profile resolver，`server members / channel members / conversation messages / thread responses` 现可返回公开用户资料。
- 2026-05-05: 已补 `backend` 定向用例，覆盖 server member、channel member 与 message author profile 的 API envelope 和 message service 返回结构。
- 2026-05-05: 前端 `servers` 数据模型已接入公开资料；members 面板、colleague detail、message row、search/filter 和 human mention label 已统一优先显示昵称，并在有头像时显示第三方头像。
- 2026-05-05: 最终验证已通过：`cd backend && uv run python -m unittest tests.test_server_api tests.test_server_channel_api tests.test_server_channel_message_api tests.test_server_channel_message_service` 与 `cd frontend && pnpm lint`。

---

## 背景

### 问题陈述

当前 OAuth 登录链路已经具备正确的基础建模：后端会把第三方返回的 `display_name` 和 `avatar_url` 写入 `users`，并用 `auth_identities` 记录 `provider` 与 `provider_user_id`。这意味着“第三方身份”和“平台内部用户”已经被分层管理。

但 server conversation 域没有消费这层资料。当前 `ServerMemberResponse`、`ServerChannelMemberResponse` 和 `ServerChannelMessageResponse` 只暴露 `user_id` 或 `author_user_id`，前端在 members 面板、右侧 colleague detail、message row、mention candidates 中也都直接显示内部 user id。结果就是：

- 第三方登录用户在“服务器”里看到的是内部 UUID，而不是昵称
- 会话消息作者名退化成内部 user id
- human member 没有头像来源，消息头像也无法显示第三方头像
- 当前认证模型看起来像“没有注册成功”，但真实问题其实是“展示域没接 profile”

### 目标

这份 spec 的目标是把 server conversation 域升级到“公开资料感知”状态：

- 保持现有 `users + auth_identities` 双层认证模型，不新增另一套第三方用户主表
- 为 server member、channel member、conversation message 增加稳定的公开用户资料载荷
- 前端成员列表、消息作者、头像和 human mention 候选统一使用公开资料
- 保持现有 UI 样式层级，不额外引入前端测试文件

### 非目标

以下内容不在本次范围内：

- 不新增非第三方登录机制
- 不重做 OAuth 合并策略
- 不把 `user_id` 替换成昵称作为内部主键
- 不为前端新增测试文件

### 关键洞察

#### 1. 这是展示契约缺失，不是认证建模错误

`users` 已经持有 `display_name` 与 `avatar_url`，`auth_identities` 也已经表达第三方身份。因此本次不需要重建用户表，只需要补一层“对会话域暴露的公开资料 DTO”。

#### 2. server conversation 需要稳定的公开资料子对象

单纯继续返回 `user_id` 会让前端在多个位置重复兜底逻辑，也无法为头像、昵称和未来 profile hover 保留一致接口。更稳妥的方式是新增统一公开资料模型，并挂到 members 与 messages 响应里。

#### 3. 展示名和 mention handle 需要分离

human 成员展示时应优先显示昵称，但 message mention 检测与输入替换暂时仍依赖稳定的 `user_id`。第一版不重做 mention 协议，只把展示 label 与 avatar 切到公开资料。

---

## Phase 0: 固化公开用户资料设计与实施边界

### 目标

明确会话域应该返回哪些公开资料字段，以及前后端各自如何消费，避免实现中重新发散到登录机制重构。

### 任务清单

#### 0.1 定义公开用户资料模型

**描述：** 为 server conversation 相关接口统一引入 `UserPublicProfile` 概念，最小字段集为：

- `user_id`
- `display_name`
- `avatar_url`

显示策略：

- UI 展示名优先 `display_name`
- 若为空，则回退 `user_id`

**涉及文件：**

- `backend/app/schemas/` - 新增公开用户资料 schema
- `frontend/features/servers/model/types.ts` - 扩展前端数据模型
- `specs/active/13-server-conversation-user-profiles-plan.md` - 固化边界

**验收标准：**

- [x] spec 明确存在统一公开资料 DTO
- [x] spec 明确展示名回退顺序

#### 0.2 定义本次 API 扩展面

**描述：** 第一版只扩展以下响应：

- `GET /servers/{server_id}/members`
- `GET /servers/{server_id}/channels/{channel_id}/members`
- `GET /servers/{server_id}/channels/{channel_id}/messages`
- `POST /servers/{server_id}/channels/{channel_id}/messages`
- `GET /servers/{server_id}/channels/{channel_id}/threads/{thread_root_message_id}`

第一版不修改创建请求体，也不修改 `auth/me`。

**涉及文件：**

- `backend/app/schemas/server_member.py`
- `backend/app/schemas/server_channel.py`
- `backend/app/schemas/server_channel_message.py`
- `frontend/features/servers/api/servers-api.ts`

**验收标准：**

- [x] spec 明确需要扩展的响应面
- [x] spec 明确不改请求体和登录流程

---

## Phase 1: 扩展后端会话契约以返回公开用户资料

### 目标

让 server member、channel member 和 conversation message 都能返回统一公开资料，并用后端测试锁定契约。

### 任务清单

#### 1.1 新增后端公开资料 schema

**描述：** 在后端 schema 层新增公开资料响应模型，集中表达会话域允许暴露的用户字段。

**涉及文件：**

- `backend/app/schemas/user_profile.py` - 新增 `UserPublicProfileResponse`

**验收标准：**

- [x] schema 仅暴露 `user_id / display_name / avatar_url`
- [x] schema 可从 `User` 模型稳定构造

#### 1.2 扩展 member 与 message 响应模型

**描述：** 将公开资料挂载到以下响应：

- `ServerMemberResponse.user`
- `ServerChannelMemberResponse.user`
- `ServerChannelMessageResponse.author_user`

**涉及文件：**

- `backend/app/schemas/server_member.py`
- `backend/app/schemas/server_channel.py`
- `backend/app/schemas/server_channel_message.py`

**验收标准：**

- [x] 三类响应都包含公开资料字段
- [x] system / task message 的 `author_user` 允许为空

#### 1.3 在 service 层补 profile 装配

**描述：** service 不再只做 `model_validate(membership)`，而是基于相关 user id 批量查询 `users`，组装带公开资料的响应对象。保持接口行为不变，只补充资料载荷。

**涉及文件：**

- `backend/app/repositories/user_repository.py` - 增加批量按 id 查询能力
- `backend/app/services/server_member_service.py`
- `backend/app/services/server_channel_service.py`
- `backend/app/services/server_channel_message_service.py`

**验收标准：**

- [x] members 列表返回 user profile
- [x] messages / thread 返回 author profile
- [x] 不引入额外鉴权变化

#### 1.4 更新后端测试

**描述：** 为新增公开资料字段补测试，重点覆盖 API envelope 和 service 返回结构，不额外扩散到无关模块。

**涉及文件：**

- `backend/tests/test_server_api.py`
- `backend/tests/test_server_channel_message_api.py`
- `backend/tests/test_server_channel_message_service.py`
- 如需要：`backend/tests/test_server_channel_api.py`

**验收标准：**

- [x] 相关测试覆盖新增字段
- [x] 后端测试通过且无前端测试新增

---

## Phase 2: 接入前端成员、消息和头像展示

### 目标

把前端会话壳子从“显示 user id”切到“显示公开资料”，同时保持当前布局和样式节奏。

### 任务清单

#### 2.1 扩展前端 server conversation 类型与 API 映射

**描述：** 在 `servers-api` 中接收新增 profile 字段，并把前端类型扩展为可直接供 UI 使用的结构。

**涉及文件：**

- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/api/servers-api.ts`

**验收标准：**

- [x] member 与 message 前端模型具备公开资料字段
- [x] 旧字段如 `userId / authorUserId` 继续保留给逻辑使用

#### 2.2 更新成员列表与详情展示

**描述：** humans colleagues 区域、detail 面板和相关展示位优先展示昵称，并在有头像时显示头像；保持当前 spacing、边框和层级，不新造视觉语言。

**涉及文件：**

- `frontend/features/servers/ui/colleagues-panel.tsx`
- `frontend/features/servers/ui/colleague-detail.tsx`
- 如需要：`frontend/features/servers/ui/server-conversation-page-client.tsx`

**验收标准：**

- [x] human member 优先显示昵称
- [x] 有头像时显示头像，无头像时保持现有 fallback 风格
- [x] 样式与现有 conversation 面板对齐

#### 2.3 更新消息作者与 human mention 候选

**描述：** 消息作者名、消息头像和 human mention candidates 改用公开资料展示，但不改现有 mention handle 解析逻辑。

**涉及文件：**

- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/features/servers/lib/server-conversation-view.ts`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`

**验收标准：**

- [x] user message 作者名优先展示昵称
- [x] 消息行头像优先展示第三方头像
- [x] mention 候选 label 使用昵称，handle 仍保持稳定 id

---

## Phase 3: 完成验证并回写 spec 状态

### 目标

完成命令验证、更新 spec 阶段状态，并确保本次实现与 spec 保持一致。

### 任务清单

#### 3.1 运行最小必要验证

**描述：** 本次以后端测试和前端静态检查为主。遵守用户要求，不为前端新增测试文件。

**建议验证：**

- `cd backend && uv run pytest backend/tests/test_server_api.py backend/tests/test_server_channel_message_api.py backend/tests/test_server_channel_message_service.py`
- `cd frontend && pnpm lint`

如局部命令路径需要按仓库实际结构调整，以实际可运行命令为准。

**涉及文件：**

- 无代码文件新增，仅执行验证

**验收标准：**

- [x] 后端相关测试通过
- [x] 前端 lint 通过或记录真实阻塞

#### 3.2 回写 spec 状态

**描述：** 每完成一个阶段后勾选对应 Phase；全部完成后把文档状态改为 `review` 或 `completed`，并补实现记录。

**涉及文件：**

- `specs/active/13-server-conversation-user-profiles-plan.md`

**验收标准：**

- [x] spec 反映真实完成情况
- [x] 不留下占位描述

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 继续把展示名和内部 user id 混为一体 | mention、鉴权和展示语义再次耦合 | 保留 `user_id` 作为逻辑标识，仅新增 profile 展示层 |
| 在多个 service 中重复 profile 拼装逻辑 | 维护成本上升 | 优先抽出统一的 profile 映射辅助逻辑 |
| 前端头像替换破坏现有对齐 | 会话列表和消息流视觉跳动 | 复用现有 Avatar / fallback 结构，不改尺寸和 spacing |
| 扩大到登录机制重构 | 范围失控 | 在 spec 中明确非目标，不改非第三方登录 |

---

## 总结

这份 spec 解决的是“第三方登录资料已经存下来了，但 server conversation 没有正确展示”的断层问题。核心思路不是重做注册登录，而是基于现有 `users + auth_identities` 模型，为会话域补统一公开资料 DTO，并把成员、消息、头像和昵称展示全面接到这层资料上。
