# Agent persistent state bootstrap and maintenance plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-06 |
| **预期改动范围** | backend agent identity bootstrap / executor_manager agent state directory seeding / executor persistent runtime prompt assembly / server colleague detail semantics / tests |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 收敛持久状态 bootstrap 边界与非目标
- [x] Phase 1: 建立非空持久状态骨架与幂等 backfill
- [x] Phase 2: 建立 persistent runtime 下的维护提示词与写入约束
- [x] Phase 3: 补齐 owner 侧可见性、语义收口与验证

---

## 背景

### 问题陈述

`10-agent-persistent-state-runtime-plan.md` 已经把 `AgentIdentity / PersistentState / runtime` 的边界建立起来，当前代码里也已经存在 agent 私有持久目录和 `/agent_state` 挂载能力。但这套能力目前还停留在“目录存在”的层面，没有真正进入“长期状态入口可用”的层面。

当前最直接的问题有三个：

- `executor_manager/app/services/workspace_manager.py` 只是 `touch` 出 `MEMORY.md` 和 `profile.json`，导致它们默认是空文件
- owner 在 server colleague detail 中看到 `Persistent files`，但树里的关键文件往往没有任何内容，形成“已经支持长期记忆”的错觉
- executor 目前没有稳定提示词告诉 persistent runtime 里的 agent 应该如何维护这些文件，所以后续是否写、写什么、哪些字段不能动，全靠 prompt 偶然性

这会直接削弱后续两条能力线。一方面，agent 自己没有可解释的长期状态起点；另一方面，server UI 也无法把 private persistent state 和 published artifacts 清晰区分开。结果就是持久状态既不可信，也不稳定。

### 目标

这份计划的目标是把 agent 持久状态从“空目录壳子”升级为“非空、带契约、可维护的长期状态入口”。重点包括：

- 为每个 server agent 初始化一份非空的 persistent state bootstrap
- 明确 `MEMORY.md`、`profile.json`、`notes/`、`state/`、`artifacts/` 的职责边界
- 在 `agent_runtime_mode=persistent` 时注入稳定的持久状态维护提示词
- 建立幂等 backfill 机制，避免覆盖已有 agent 或用户已维护的内容
- 让 owner 在 UI 中看到的 private persistent files 具有稳定语义

### 关键洞察

#### 1. 持久目录存在，不等于长期状态能力已成立

如果系统只是创建了目录和空文件，后续无论是 owner 还是 agent，都无法从这些文件推断出“应该写什么”“什么时候写”“哪些内容不该写”。长期状态能力需要 bootstrap contract，而不仅仅是挂载目录。

#### 2. `profile.json` 和 `MEMORY.md` 必须区分所有权

`MEMORY.md` 更适合作为 agent 维护的长期自然语言记忆入口；`profile.json` 则必须保留系统真相，例如 identity、preset 绑定、runtime policy、路径契约。两者不能按同一种自由度处理。

#### 3. 维护协议必须在执行层统一注入

如果只在 channel trigger prompt 里补几句“你可以更新 memory”，那么 agent DM、session resume 和未来其他 persistent 入口都会出现行为不一致。persistent-state maintenance contract 应该由 executor 统一注入。

---

## Phase 0: 收敛持久状态 bootstrap 边界与非目标

### 目标

先把哪些文件必须初始化、哪些文件允许 agent 更新、哪些目录允许为空讲清楚，避免实现中继续混用“私有状态”和“共享成果”语义。

### 任务清单

#### 0.1 明确 persistent state 文件分层

**描述：** 固化以下最小目录契约，并明确各自职责：

```text
agents/<agent_id>/
  profile.json
  MEMORY.md
  notes/
    active-context.md
  state/
    task-state.json
  artifacts/
```

**涉及文件：**

- `specs/constitution/2026-05-06-server-agent-observability-tasks-and-persistence.md`
- `specs/draft/10-agent-persistent-state-runtime-plan.md`
- `executor_manager/app/services/workspace_manager.py`

**验收标准：**

- [ ] spec 中明确哪些文件必须非空初始化
- [ ] spec 中明确 `artifacts/` 可以为空且不承担 bootstrap 完整性职责

#### 0.2 明确所有权与可写边界

**描述：** 明确 `profile.json` 为系统拥有核心字段、agent 只可更新受限子段；`MEMORY.md`、`notes/`、`state/` 允许 persistent runtime 维护；temporary runtime 保持 snapshot read-only。

**涉及文件：**

- `specs/constitution/2026-05-06-server-agent-observability-tasks-and-persistence.md`
- `executor/app/core/engine.py`
- `executor_manager/app/services/container_pool.py`

**验收标准：**

- [ ] `profile.json` 的系统字段和 agent 字段边界清晰
- [ ] persistent 与 temporary runtime 的写权限边界清晰

#### 0.3 明确非目标

**描述：** 当前阶段不做：

- 自动把 private persistent files 纳入 channel published artifacts
- 自动 merge temporary runtime 对长期状态的修改
- 让 agent 任意改写 `profile.json` 顶层结构

**验收标准：**

- [ ] 非目标写清楚，避免 scope 膨胀

---

## Phase 1: 建立非空持久状态骨架与幂等 backfill

### 目标

把“创建空文件”升级为“写入版本化 bootstrap 内容”，同时保证对已有 agent 的 backfill 幂等、安全。

### 任务清单

#### 1.1 引入 bootstrap writer

**描述：** 在 workspace manager 中新增类似 `ensure_agent_state_bootstrap()` 的能力，负责创建目录并写入默认内容，而不是只 `touch` 文件。

**涉及文件：**

- `executor_manager/app/services/workspace_manager.py`
- 如有需要：`executor_manager/tests/*`

**验收标准：**

- [x] 新 agent 创建后 `MEMORY.md` 默认非空
- [x] 新 agent 创建后 `profile.json` 默认非空且为合法 JSON
- [x] 重复执行 bootstrap 不会覆盖非空已有内容

#### 1.2 从 agent metadata 生成 profile seed

**描述：** `profile.json` 的种子内容应从 `AgentIdentity` 和 `AgentPersistentState` 元数据生成，而不是写死常量字符串。

**涉及文件：**

- `backend/app/services/agent_identity_service.py`
- `backend/app/schemas/agent_identity.py`
- `executor_manager/app/services/workspace_manager.py`

**验收标准：**

- [x] `profile.json` 包含 `schema_version`
- [x] `profile.json` 包含 handle、display_name、preset_id、runtime policy、persistent state contract

#### 1.3 建立已有 agent 的 backfill 策略

**描述：** 对现有已经存在的 agent 持久目录提供 backfill 路线。可以是 lazy self-heal，也可以是管理脚本，但必须避免覆盖已有人工内容。

**涉及文件：**

- `backend/app/services/agent_identity_service.py`
- `executor_manager/app/services/workspace_manager.py`
- 如有需要：新增 backfill 脚本或测试

**验收标准：**

- [x] 旧 agent 可补齐默认骨架
- [x] 非空 `MEMORY.md` / `profile.json` 不会被覆盖

### Phase 1 implementation notes

- backend 在 agent 创建链路里调用 `ensure_agent_state_bootstrap()`，会基于 `AgentIdentity` 与 `AgentPersistentState` 元数据写入非空 seed。
- executor manager 把原来的 `touch` 升级为 `ensure_agent_state_bootstrap()`，为旧目录提供 lazy self-heal，同时保持幂等。
- 当前 bootstrap 会初始化 `profile.json`、`MEMORY.md`、`notes/active-context.md`、`state/task-state.json`，`artifacts/` 保持空目录。

---

## Phase 2: 建立 persistent runtime 下的维护提示词与写入约束

### 目标

让 persistent runtime 中的 agent 始终知道如何维护长期状态文件，而不是靠业务 prompt 偶然提及。

### 任务清单

#### 2.1 在 executor 注入 persistent-state hint

**描述：** 在 `executor/app/core/engine.py` 中新增统一的持久状态提示词构造，仅在 `agent_runtime_mode=persistent` 时拼接到 prompt。

**涉及文件：**

- `executor/app/core/engine.py`
- 如有需要：`executor/tests/*`

**验收标准：**

- [x] persistent runtime 会收到 `/agent_state` 的维护提示
- [x] temporary runtime 不会收到鼓励写长期状态的提示

#### 2.2 约束长期状态写入内容

**描述：** 提示词至少要收紧这些规则：

- `MEMORY.md` 适合长期稳定事实、偏好、协作约束
- `state/*.json` 适合结构化运行状态
- `profile.json` 的系统字段不可覆盖
- 不要把临时任务噪音写进长期记忆
- 不要把 private state 误当成 shared artifacts

**涉及文件：**

- `executor/app/core/engine.py`
- `specs/constitution/2026-05-06-server-agent-observability-tasks-and-persistence.md`

**验收标准：**

- [x] 提示词覆盖写什么、不写什么、哪些字段不能动
- [x] 提示词不和 channel shared context prompt 互相冲突

#### 2.3 为 task 能力和长期状态建立最小衔接

**描述：** 提示词中应明确：如果执行中形成长期有价值的结论，可以更新 `MEMORY.md` 或 `state/`；如果形成可共享材料，应走 workspace export / published artifacts 链路。

**涉及文件：**

- `executor/app/core/engine.py`
- `backend/app/services/channel_artifact_service.py`

**验收标准：**

- [x] private state 与 published artifacts 的边界在执行层被明确说明

### Phase 2 implementation notes

- executor 抽出了 `_compose_user_prompt()`，把输入提示、persistent-state contract、通用 prompt appendix 和 workspace scope hint 收敛到一处组装。
- `agent_runtime_mode=persistent` 时会额外注入 `/agent_state` 维护契约，覆盖 `MEMORY.md`、`state/*.json`、`notes/`、`profile.json` 和 published artifacts 的边界。
- `agent_runtime_mode=temporary` 时不会收到鼓励写长期状态的提示，保持 snapshot read-only 心智。

---

## Phase 3: 补齐 owner 侧可见性、语义收口与验证

### 目标

让 server colleague detail 中展示的 private persistent files 语义稳定，且有基础调试信息可用。

### 任务清单

#### 3.1 收口 `Persistent files` 的产品语义

**描述：** 在前端 colleague detail 中明确这块展示的是 private persistent state，而不是 shared files 或 channel artifacts。

**涉及文件：**

- `frontend/features/servers/ui/colleague-detail.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [x] UI 文案不再和 shared artifacts 混淆
- [x] owner 能稳定区分 private state 与 shared artifacts

#### 3.2 补充可见元信息

**描述：** 如果实现成本可控，补充轻量元信息，例如 bootstrap schema version、是否为系统种子内容、最后更新时间。

**涉及文件：**

- `backend/app/api/v1/server_agents.py`
- `backend/app/services/agent_state_browser_service.py`
- `frontend/features/servers/api/servers-api.ts`
- `frontend/features/servers/ui/agent-persistent-files-panel.tsx`

**验收标准：**

- [x] 至少有一条稳定元信息帮助判断 bootstrap 是否成功

#### 3.3 完成验证与回写 spec

**描述：** 为 bootstrap、prompt 注入和 UI 语义补齐测试与验证说明。

**涉及文件：**

- `backend/tests/*`
- `executor_manager/tests/*`
- `frontend/*`（如需）
- `specs/draft/15-agent-persistent-state-bootstrap-and-maintenance-plan.md`

**验收标准：**

- [x] 有定向验证覆盖非空 bootstrap 与幂等 backfill
- [x] spec 回写实际实现记录和状态

### Phase 3 implementation notes

- colleague detail 中的 `Persistent files` 已收口为 `Private state files / 私有状态文件`，并补充了“不是 shared artifacts”的说明文案。
- owner 侧新增了轻量元信息展示，当前会显示 state contract version 和 runtime status，便于快速判断当前私有状态契约是否已经接入。
- persistent files 空态文案不再复用 shared artifacts 文案，避免把 private state 和 published artifacts 混成同一语义。

## 验证记录

- backend: `uv run python -m unittest tests.test_agent_state_bootstrap_service tests.test_agent_identity_service`
- executor_manager: `uv run python -m unittest tests.test_agent_state_bootstrap`
- executor: `uv run python -m unittest tests.test_engine_persistent_state_hint`
- frontend: `pnpm lint`
- frontend: `pnpm build`
