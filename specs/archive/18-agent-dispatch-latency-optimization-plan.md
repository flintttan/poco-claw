# Agent dispatch latency optimization plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-07 |
| **预期改动范围** | backend run enqueue and async notification / executor_manager internal notify endpoint and pull orchestration / executor Claude SDK client cache and lease model / observability and latency regression tests |
| **改动类型** | perf |
| **优先级** | P1 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 收敛延迟基线、实施边界与验证口径
- [x] Phase 1: 建立 backend 到 executor_manager 的推送通知链路
- [x] Phase 2: 收敛 executor_manager 的立即拉取语义与并发保护
- [x] Phase 3: 建立 executor 侧 ClaudeSDKClient 缓存与串行租约
- [x] Phase 4: 补齐观测、回归测试与灰度开关

---

## 背景

### 问题陈述

根据 `2026-05-07-agent-dispatch-latency-optimization.md` 的最新决策，当前频道 mention agent 的二次响应延迟主要集中在两个阶段：

- `executor_manager` 仍以 APScheduler 的固定间隔轮询方式发现新 run，默认 2 秒
- `executor` 每次执行都会重新创建 `AgentExecutor` 和 `ClaudeSDKClient`，导致 MCP 子进程与 Claude Code 连接重复初始化

这条链路在功能上已经成立，但对用户的主观体验仍然不够稳定。对于已经持有 persistent container 的 agent，用户期望的是“几乎立刻开始动”，而不是在容器明明还热着的情况下仍然等待数秒。

与此同时，`server conversation execution observability` 已经把 execution placeholder 建成了一等协作对象。现在如果调度和执行预热依然慢，频道里就会长期停在 `queued`，削弱 execution 可见性本应带来的信任提升。

### 目标

这份 spec 的目标是把热容器场景下的 dispatch latency 从“秒级可感知等待”收敛到“接近即时”，具体包括：

- 让 backend 在 run 成功落库后主动通知 `executor_manager` 立即尝试拉取
- 保留轮询机制作为兜底，不把系统改成必须依赖长连接的推送架构
- 在 `executor` 进程内缓存 `ClaudeSDKClient`，复用已启动的 MCP 子进程和 Claude Code 连接
- 明确缓存的串行租约模型，避免把单个 client 误当成可并发共享的连接池
- 补齐日志、开关和验证手段，确保这次优化可以测量、可回滚

### 非目标

以下内容不在本次范围内：

- 不改写 `executor_manager` 的整体调度架构为 WebSocket、SSE 或消息队列
- 不在这一轮解决 config resolve / staging 的全部串行耗时
- 不把 `ClaudeSDKClient` 设计成多 session 并发复用器
- 不改动现有 callback 协议、execution placeholder 数据结构和 channel task 协作协议

### 关键洞察

#### 1. 立即触发拉取比缩短轮询间隔更稳

把轮询从 2 秒调到 0.5 秒只能降低平均等待，并不能消除“正好错过上一轮 tick”的抖动。更直接的办法是让 backend 在 run 落库后主动打一次 `executor_manager`，把“发现任务”从被动等待变成立即尝试。

#### 2. `ClaudeSDKClient` 的收益来自复用已建立的本地连接，不来自并发共享

本地安装的 SDK 源码和官方 sessions 文档都说明 `ClaudeSDKClient` 是 stateful 的 multi-turn client，同时不能跨不同 async runtime context 随意复用。因此最稳妥的优化方向不是构建一个全局共享池，而是在单个 executor 进程内对单 agent active session 做串行复用。

#### 3. 第一阶段必须把“可回退”设计进去

这次优化会触碰 backend、executor_manager 和 executor 三个服务。无论是通知链路还是 client cache，都应该允许在配置层快速关闭，避免一旦出现死锁、僵尸 client 或重复拉取就只能回滚代码。

---

## Phase 0: 收敛延迟基线、实施边界与验证口径

### 目标

先把“优化前测什么、优化后怎么证明有效”说清楚，同时把各服务边界固定下来，避免后续实现时重新发散。

### 任务清单

#### 0.1 固化热容器延迟分段口径

**描述：** 明确至少三段关键时间点：

- run 落库完成时间
- `executor_manager` claim run 开始时间
- `executor` 开始第一次 `client.query()` 的时间

同时约定第一轮只关注 persistent container 的热路径，不把首次冷启动混入成功判定。

**涉及文件：**

- `specs/constitution/2026-05-07-agent-dispatch-latency-optimization.md`
- `executor_manager/app/services/run_pull_service.py`
- `executor/app/core/engine.py`
- `backend/app/services/task_service.py`

**验收标准：**

- [ ] spec 明确热路径 latency 的分段定义
- [ ] 各服务日志已有或规划了对应打点位置

#### 0.2 收敛开关与回退策略

**描述：** 为两类优化都预留配置开关：

- `backend -> executor_manager notify` 开关
- `executor SDK client cache` 开关

并明确任一优化关闭后，系统都必须回退到当前稳定路径。

**涉及文件：**

- `backend/app/core/settings.py`
- `executor_manager/app/core/settings.py`
- `executor/app/core/` - 新增或修改 cache settings

**验收标准：**

- [ ] spec 明确两个开关的默认值与回退行为
- [ ] 关闭任一开关不会破坏当前功能闭环

---

## Phase 1: 建立 backend 到 executor_manager 的推送通知链路

### 目标

在 run 落库成功后主动通知 `executor_manager`，把“等待下一轮轮询”改成“立即尝试拉取”。

### 任务清单

#### 1.1 新增 backend 侧 notify client

**描述：** 基于 backend 已有的 `executor_manager_url` 配置增加内部通知客户端，负责向 `executor_manager` 发起 best-effort HTTP 通知。

**涉及文件：**

- `backend/app/core/settings.py`
- `backend/app/services/` - 新增 `executor_manager_notify_service.py` 或扩展现有 client

**验收标准：**

- [ ] backend 有稳定的 notify 封装，不把裸 `httpx` 调用散落到业务代码
- [ ] notify 失败不会抛回用户请求主链路

#### 1.2 在 enqueue 成功后异步触发 notify

**描述：** 在 `TaskService.enqueue_task()` 或更上层 async API 边界中，对 `accepted_type="run"` 的新 run 触发异步通知。通知 payload 至少包含：

- `run_id`
- `schedule_mode`
- 可选的 `session_id`

**涉及文件：**

- `backend/app/services/task_service.py`
- `backend/app/services/server_agent_trigger_service.py`
- `backend/app/api/v1/` - 若需要在请求边界注入 background task

**验收标准：**

- [ ] immediate run 创建成功后会触发 best-effort notify
- [ ] queued query、scheduled run 等分支的行为被明确约束

#### 1.3 定义 notify 的认证与幂等要求

**描述：** 这条内部接口必须复用现有 internal token 或同等级认证，且允许重复通知而不造成错误副作用。

**涉及文件：**

- `backend/app/services/`
- `executor_manager/app/api/v1/`
- `executor_manager/app/core/settings.py`

**验收标准：**

- [ ] notify 接口有内部认证
- [ ] 重复发送同一 run 的 notify 不会导致重复 dispatch

---

## Phase 2: 收敛 executor_manager 的立即拉取语义与并发保护

### 目标

让 `executor_manager` 能安全处理 notify 触发的立即拉取，同时保持 APScheduler 轮询兜底不变。

### 任务清单

#### 2.1 新增内部 notify endpoint

**描述：** 在 `executor_manager` 增加内部端点，例如 `POST /api/v1/internal/runs/notify`，接收 backend 的通知并触发一次 `poll(schedule_modes=[...])`。

**涉及文件：**

- `executor_manager/app/api/v1/` - 新增 internal notify route
- `executor_manager/app/schemas/` - 新增 notify request schema

**验收标准：**

- [ ] endpoint 只承担触发 poll，不直接修改 run 状态
- [ ] endpoint 响应快速，不在请求中等待完整 dispatch 完成

#### 2.2 保留轮询兜底并避免重复 dispatch

**描述：** notify 与 APScheduler 可能同时触发拉取，因此要明确以下保护：

- 同一个 run 被重复 claim 时不会重复 dispatch
- poll 中已有的 inflight run 保护继续生效
- 当前容量已满时 notify 可以安全返回，交由后续轮询兜底

**涉及文件：**

- `executor_manager/app/services/run_pull_service.py`
- `executor_manager/app/services/backend_client.py`

**验收标准：**

- [ ] notify 不会破坏现有 inflight 去重语义
- [ ] 容量打满时不会因 notify 产生异常或忙等

#### 2.3 补齐调度链路日志

**描述：** 为 notify 到 claim 的关键路径增加结构化日志，至少能区分：

- 轮询触发的 pull
- notify 触发的 pull
- notify 到达但未实际 claim 到 run

**涉及文件：**

- `executor_manager/app/services/run_pull_service.py`
- `executor_manager/app/api/v1/`

**验收标准：**

- [ ] 日志中可区分 poll 触发来源
- [ ] 可以从日志直接观察 notify 是否缩短了 claim 延迟

---

## Phase 3: 建立 executor 侧 ClaudeSDKClient 缓存与串行租约

### 目标

在不破坏当前执行语义的前提下，复用 persistent runtime 中已经建立好的 `ClaudeSDKClient`。

### 任务清单

#### 3.1 引入 client cache 与 lease 抽象

**描述：** 新增进程级 cache 层，负责：

- 按 `agent_identity_id` 或更细 key 保存 client
- 记录 client 当前是否被占用
- 管理 TTL、健康状态和销毁

推荐把缓存与租约逻辑从 `AgentExecutor` 中抽离，避免执行流程类过度膨胀。

**涉及文件：**

- `executor/app/core/` - 新增 `client_pool.py` 或同等级模块
- `executor/app/core/engine.py`

**验收标准：**

- [ ] executor 有独立的 client cache / lease 抽象
- [ ] 同一 client 在任一时刻只能被一个执行持有

#### 3.2 把 `ClaudeSDKClient` 生命周期从方法级提升到进程级

**描述：** 当前 `async with ClaudeSDKClient(...) as client` 的生命周期包在一次 `execute()` 里。优化后需要把 connect / disconnect 生命周期移动到 cache 层，由 lease holder 复用。

同时必须保持：

- 同一 async context 内使用
- 当前 run 完成后释放 lease，而不是立刻销毁 client

**涉及文件：**

- `executor/app/core/engine.py`
- `executor/app/api/v1/task.py`

**验收标准：**

- [ ] 热路径下重复执行不会每次重建 `ClaudeSDKClient`
- [ ] 执行结束后 client 可继续留在 cache 中待复用

#### 3.3 明确 session 传递与 active session 约束

**描述：** 复用路径必须改用 SDK 已存在的 `client.query(..., session_id=...)` 语义，而不是在 `query()` 层假设 `resume` 参数。

同时明确第一阶段只优化：

- 同一 persistent agent 的连续任务
- 单 active session 的串行执行

若遇到 client 正忙或 session 语义不匹配，应回退到等待或重建，而不是强行并发复用。

**涉及文件：**

- `executor/app/core/engine.py`
- `executor/app/schemas/request.py`
- `backend/app/services/session_queue_service.py`

**验收标准：**

- [ ] executor 通过 `session_id` 驱动连续 query
- [ ] 不会把同一个 cached client 并发复用到多个 inflight execution

#### 3.4 增加健康检查与淘汰策略

**描述：** cache 层需要处理：

- MCP 子进程已退出
- Claude Code 连接断开
- client 长时间空闲
- executor 关闭时统一清理

**涉及文件：**

- `executor/app/core/client_pool.py`
- `executor/app/core/lifespan.py` 或同等级启动/关闭入口

**验收标准：**

- [ ] 坏 client 会被识别并重建
- [ ] executor 进程退出时不会遗留 client 资源

---

## Phase 4: 补齐观测、回归测试与灰度开关

### 目标

让这次性能优化具备可测量性、可回归验证和可灰度回滚能力。

### 任务清单

#### 4.1 增加端到端延迟日志与指标

**描述：** 在 backend、executor_manager、executor 三侧补齐统一 trace 维度的 timing log，至少覆盖：

- run materialized
- notify sent / notify received
- run claimed
- executor accepted
- first query issued

**涉及文件：**

- `backend/app/services/task_service.py`
- `executor_manager/app/services/run_pull_service.py`
- `executor/app/api/v1/task.py`
- `executor/app/core/engine.py`

**验收标准：**

- [ ] 同一 run 的关键耗时节点可串起来看
- [ ] 可以直接比较优化前后的热路径分段耗时

#### 4.2 补齐单测与集成测试

**描述：** 至少覆盖：

- backend notify 失败不影响 enqueue 成功
- executor_manager notify endpoint 会触发一次受控 poll
- client cache 在串行复用时命中
- client busy / unhealthy 时会回退或重建

**涉及文件：**

- `backend/tests/`
- `executor_manager/tests/`
- `executor/tests/`

**验收标准：**

- [ ] 三个服务都有与本次优化直接相关的测试
- [ ] 不依赖真实 Claude Code 进程也能覆盖主要分支

#### 4.3 定义灰度与回滚步骤

**描述：** 明确上线顺序建议：

1. 先灰度启用 notify
2. 观察重复 claim / dispatch 风险
3. 再灰度启用 client cache
4. 观察 client 泄漏、卡死和异常重建

**涉及文件：**

- `specs/draft/18-agent-dispatch-latency-optimization-plan.md`
- 相关服务 settings 文档或 README

**验收标准：**

- [ ] spec 明确建议的 rollout 顺序
- [ ] 任一阶段发现问题都可通过配置关闭对应优化

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| ---- | ---- | -------- |
| backend notify 与轮询并发触发导致重复 dispatch | 可能出现同一 run 多次下发 | 复用现有 claim/inflight 去重语义，并在 notify 路径补充测试 |
| `ClaudeSDKClient` 被误当成可并发共享对象 | 会话串线、连接错误、不可预测异常 | 引入显式 lease，限制单 client 同时只允许一个 holder |
| cached client 进入坏状态但未被及时淘汰 | 后续热路径全部失败或卡住 | 每次租用前做健康检查，并在异常时强制重建 |
| 性能优化难以量化，争议停留在体感层面 | 无法证明收益或定位回归 | 预先定义分段 timing log 和热路径验证口径 |
| 新链路在生产异常时难以快速止损 | 影响 mention 响应稳定性 | 为 notify 与 cache 各自提供独立开关，允许单独回滚 |

---

## 总结

这份 spec 承接 `2026-05-07-agent-dispatch-latency-optimization.md` 的决策，把“推送通知 + SDK 缓存”拆成了可执行的两条优化线。整体策略是先用最小改动消除 `executor_manager` 的轮询等待，再在 executor 内引入受控的 `ClaudeSDKClient` 串行复用，同时从一开始就把开关、日志和回退能力做进去，确保这次性能优化不是一次性冒险改动，而是可观测、可灰度、可回滚的演进。
