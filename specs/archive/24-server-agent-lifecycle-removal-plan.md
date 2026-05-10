# Server agent lifecycle and soft removal plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-08 |
| **预期改动范围** | backend agent identity/channel services, message hydration, frontend server conversation UI, Alembic migration |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 软删除数据模型与后端移除语义 (2026-05-08)
- [x] Phase 1: 历史消息 agent 身份解析与前端头像入口 (2026-05-08)
- [x] Phase 2: Server remove 确认弹窗与频道影响提示 (2026-05-08)
- [x] Phase 3: 验证、整理与提交 (2026-05-08)

---

## 背景

### 问题陈述

Server agent 当前被从 server 移除时会物理删除 `agent_identity`。这会破坏历史消息头像、agent reaction actor、execution/profile 入口，以及后续重新拉入同一 agent 的身份连续性。频道级移除和 server 级移除也需要在 UI 与服务层继续保持清晰的作用域边界。

### 目标

- 将 server 级 agent remove 改为软删除，保留历史身份和 persistent state。
- 保证被移除 agent 的历史消息仍能显示头像，并可点击进入历史详情。
- 保留 agent reaction，不因普通 remove 消失。
- 明确 restart、stop、channel remove、server remove 的运行和队列语义。
- 在 colleague drawer 中为 server remove 增加二次确认和影响说明。

### 关键洞察

`AgentIdentity` 已经是协作身份、persistent state、execution placeholder、reaction actor 的共同锚点。普通 remove 应改变"可用成员集合"，而不是删除历史身份行。可用列表和历史解析必须使用不同查询边界。

---

## Phase 0: 软删除数据模型与后端移除语义

### 目标

让 `AgentIdentity` 支持 server 范围软删除，并调整后端 remove/restart/stop/channel membership 逻辑。

### 任务清单

#### 0.1 增加软删除字段与迁移

**描述：** 为 `agent_identities` 增加 `removed_at`、`removed_by` 字段，普通业务 remove 不再物理删除 identity。

**涉及文件：**

- `backend/app/models/agent_identity.py` - 增加字段
- `backend/app/schemas/agent_identity.py` - API 返回 removed 状态
- `backend/alembic/versions/*.py` - 增加 Alembic migration

**验收标准：**

- [x] `AgentIdentityResponse` 能返回 removed 字段
- [x] migration 可升级/回滚字段

#### 0.2 调整 agent repository 与 service 查询边界

**描述：** 默认 list 只返回未 removed agent；历史解析通过 get by id 仍允许读取 removed agent。

**涉及文件：**

- `backend/app/repositories/agent_identity_repository.py`
- `backend/app/services/agent_identity_service.py`
- `backend/app/services/server_agent_trigger_service.py`
- `backend/app/services/server_channel_service.py`

**验收标准：**

- [x] mention/channel add/list 默认排除 removed agent
- [x] get agent 仍可返回 removed agent 用于历史详情

#### 0.3 调整 remove/restart/stop/channel remove 语义

**描述：** server remove 停止执行、取消 queue、取消 placeholder、软删除 identity，并将所有 channel membership 失效；channel remove 只影响当前 channel。

**涉及文件：**

- `backend/app/services/agent_identity_service.py`
- `backend/app/repositories/server_channel_agent_member_repository.py`
- `backend/tests/test_agent_identity_service.py`
- `backend/tests/test_server_channel_api.py`

**验收标准：**

- [x] server remove 不删除 agent identity/persistent state
- [x] server remove 后 channel list/mention 不再包含该 agent
- [x] restart 保留 queue，stop 不改变 membership
- [x] channel remove 只取消当前 channel queue

---

## Phase 1: 历史消息 agent 身份解析与前端头像入口

### 目标

历史消息即使对应 agent 已退出频道或 server，也能稳定展示头像并进入详情。

### 任务清单

#### 1.1 后端 message response hydrate author agent

**描述：** 对系统消息中的 `agent_identity_id` 或 agent 快照字段解析 `author_agent`，允许返回 removed agent。

**涉及文件：**

- `backend/app/schemas/server_channel_message.py`
- `backend/app/services/server_channel_message_service.py`
- `backend/app/services/callback_service.py`

**验收标准：**

- [x] agent session/result message 带稳定 `agent_identity_id`
- [x] list messages/thread 返回 `author_agent`

#### 1.2 前端消息渲染使用 author agent 快照

**描述：** 前端优先用 message `authorAgent` 渲染 agent 头像；点击 agent 头像打开 colleague detail，execution placeholder 保留打开 execution drawer 的行为。

**涉及文件：**

- `frontend/features/servers/model/types.ts`
- `frontend/features/servers/api/servers-api.ts`
- `frontend/features/servers/ui/conversation-message-row.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`

**验收标准：**

- [x] removed agent 的历史消息不退化成首字母用户头像
- [x] 普通 agent 历史消息头像可打开 agent detail

---

## Phase 2: Server remove 确认弹窗与频道影响提示

### 目标

把 colleague profile 中 server 级移除入口改成 `Remove`，并提供二次确认。

### 任务清单

#### 2.1 增加确认弹窗

**描述：** 在 colleague detail 中使用 AlertDialog 确认 server remove，文案说明会从相关频道中移除并取消未开始任务。

**涉及文件：**

- `frontend/features/servers/ui/colleague-detail.tsx`
- `frontend/lib/i18n/locales/en/translation.json`
- `frontend/lib/i18n/locales/zh/translation.json`

**验收标准：**

- [x] 按钮文案为 `Remove`
- [x] 弹窗包含取消/移除两个操作
- [x] 正文展示已知受影响频道名称

#### 2.2 维护频道 agent membership 预览

**描述：** 前端加载 server 时获取各频道 agent membership，用于确认弹窗影响范围和移除后的本地状态更新。

**涉及文件：**

- `frontend/features/servers/ui/server-conversation-page-client.tsx`

**验收标准：**

- [x] server remove 后当前频道和频道预览中的 agent 都被隐藏
- [x] channel remove 仍只影响当前 channel

---

## Phase 3: 验证、整理与提交

### 目标

完成后端与前端最小验证，更新 spec 状态，用 staged changes 生成 commit message 并提交。

### 任务清单

#### 3.1 运行验证

**涉及文件：**

- backend touched Python files
- frontend package

**验收标准：**

- [x] `uv run ruff check ...` 通过
- [x] `uv run python -m py_compile ...` 通过
- [x] 相关 backend unittest 通过
- [x] `pnpm lint` 通过
- [x] `pnpm build` 通过

#### 3.2 生成提交

**描述：** 使用 staged-commit-message skill 根据 staged diff 写入 `COMMIT.md` 并提交。

**验收标准：**

- [x] `COMMIT.md` 只反映 staged changes
- [x] git commit 成功

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 默认列表过滤遗漏 removed agent | 被移除 agent 仍可被 mention 或加入 channel | 在 repository/service 层集中提供 active 查询边界 |
| 历史消息缺少 agent_identity_id | 老消息无法完整打开详情 | 前端 fallback 使用 `agent_handle` / `agent_visual_key` 快照渲染头像 |
| Stop 与 remove 队列语义混淆 | 用户误以为 stop 清空任务 | spec 和 service 保持 stop 不改变 membership、不清 queue |
| 前端影响频道列表不完整 | 确认弹窗说明不准确 | 使用已知频道 membership 预览，未知时用保守泛化文案 |

## 总结

本计划把 agent remove 从"删除身份"改成"移出可用集合"，让历史协作记录保持稳定，同时补齐 restart/stop/remove 的操作边界和高影响 UI 确认。
