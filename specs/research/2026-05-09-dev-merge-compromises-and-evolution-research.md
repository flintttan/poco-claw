# dev 合并妥协与后续演进调研

## 元数据

| 字段 | 值 |
| --- | --- |
| 调研日期 | 2026-05-09 |
| 当前分支 | `feat/channel-shared-artifacts` |
| 待合入分支 | `dev` |
| 关联文档 | `specs/active/25-dev-merge-conflict-resolution-plan.md` |
| 文档性质 | 合并取舍记录与后续架构演进调研 |

## 背景

当前分支围绕 server channel、persistent agent、channel artifacts、channel runtime tools 和频道内协作执行体验做了大规模扩展。`dev` 分支则并行推进了认证模式、系统管理员、runtime env policy、run-scoped replay、移动端运行历史等基础设施能力。两条分支的冲突不是简单的文本冲突，而是多个模型在同一批入口文件中同时演进。

本次合并的目标不是重写架构，而是在保护当前分支频道协作主线的前提下，吸收 `dev` 已经形成的通用基础设施。换句话说，频道语义、频道消息投影和 persistent agent 的执行链路以当前分支为主；认证、管理员配置、运行记录和 runtime policy 等能力作为平台底座合入。

本文记录的是本次合并中的“迁就型设计”和后续可演进方向。它不是实施计划，也不要求在本次合并中完成架构重构。

## 合并原则

1. **频道协作主线优先保留当前分支。** 频道中的执行占位消息、运行状态同步、最终消息替换、artifact/runtime tool 注入和 persistent agent 语义，是当前分支的核心产品价值，不能在合并中退化。
2. **`dev` 的平台能力作为基础设施吸收。** `single_user` 认证模式、system admin、managed env vars、runtime env policy、run-scoped replay 和移动端 run history 应该尽量合入，避免当前分支继续停留在旧底座上。
3. **短期以兼容为主，长期再收敛模型。** 对于 system preset、workspace feature flag、callback projection 和 run replay 这些模型重叠处，本次先采用兼容策略，后续再通过独立演进清理边界。

## callback 与 AgentRun 的取舍

本次合并明确保留当前分支 callback 机制：executor 回调到 backend 后，`callback_service` 继续负责同步 server channel execution placeholder、更新频道中的运行状态，并在完成或失败时替换为最终消息。

`dev` 引入的 `AgentRun` 在本次合并中作为补充持久化目标：同一份 callback `state_patch` 需要同时写入 `AgentSession` 和 `AgentRun`。这样可以保留 `dev` 的 run-scoped replay、tool execution 归档和移动端运行历史能力，但不改变频道消息当前依赖 callback 副作用投影的事实。

这个选择的原因是风险控制。频道投影已经和当前分支的 placeholder、final message、agent trigger、channel artifact 和 persistent runtime 形成一条完整链路。如果在合并期间直接改为 `AgentRun` 驱动频道消息，容易同时破坏频道协作体验和 run replay 体验。短期兼容能让两套能力先共存。

长期更理想的方向是让 `AgentRun` 成为“一次执行”的事实源，channel message 只作为面向频道的展示投影。这样未来可以从 `AgentRun` 重建频道执行状态，也可以把 replay、workspace artifacts、tool executions 和最终消息统一绑定到同一个 run 维度。但这需要单独设计投影服务、回填策略和失败恢复语义，不适合塞进本次冲突解决。

## 其他迁就型设计

### 认证模式

合并后以 `dev` 的 `single_user | oauth_optional | oauth_required` 作为正式认证模型，同时兼容旧的 `AUTH_MODE=disabled`，将其视为 `single_user` 的别名。这样既能吸收 `dev` 的系统管理员和 Feishu/Lark OAuth 能力，也不会让当前分支或旧本地 `.env` 因模式名变化直接失效。

`workspace_features_enabled` 暂时继续放在 `/auth/config` 返回。这个字段严格来说不是认证语义，但当前分支的 workspace/server UI 可能依赖它做前端 gating。本次合并先避免扩大前后端改造面，后续再迁移到独立的产品配置接口。

登录页无可用 provider 的文案以“管理员配置”为主。这与 `dev` 的 setup-required 和 admin console 心智一致，也比让普通用户看到 backend env 提示更贴近产品化部署。

### Preset 可见性

System preset 与 workspace preset 本次采用过渡兼容：系统预设同时识别 `scope == "system"` 和 `user_id == SYSTEM_USER_ID`；workspace preset 继续按 workspace membership 判断可见性。

这不是最终最干净的模型。`scope` 更适合表达系统、用户、workspace 等产品语义；`SYSTEM_USER_ID` 更像历史实现细节。但为了合并 `dev` 已有系统预设逻辑，又不丢掉当前分支的 workspace scope，本次先允许两种系统预设判定方式共存。

### 模型与环境变量配置

managed system env vars 合并后应覆盖 `.env` 默认模型配置，并且普通任务与频道 persistent agent 保持一致。这样 admin/runtime env policy 的配置结果不会只影响普通任务，而漏掉频道触发的 persistent agent。

这个选择会让频道 agent 接入 `dev` 的后台配置能力，但也意味着 persistent agent 的模型来源不再只由当前分支的 config snapshot 或 `.env` 决定。后续需要在 UI 或审计信息里更清楚地展示实际生效的模型和 provider。

### 前端执行历史

执行 UI 采用 `dev` 的 run history pinned 行为：用户点击历史 run 后保持在历史视图，不因为最新 run 更新而自动跳回当前运行。当前分支的右侧面板状态和频道执行体验需要保留，但 run history 的交互心智以 `dev` 为准。

这样做的原因是 run-scoped replay 本身就是让用户检查某一次具体执行。如果用户主动进入历史 run，却被实时轮询拉回最新 run，会破坏回放和对比体验。

### task-submit-api 测试

`frontend/features/task-composer/api/task-submit-api.test.ts` 在当前分支中已被删除，本次合并保持删除。这个决策意味着不在冲突解决中恢复旧测试文件；如果后续发现 task submit API 缺少覆盖，应基于当前 API 重新补测试，而不是恢复已经被判定为 stale 的测试。

### quickstart 重试命令

`rustfs-init` 失败重试文案采用 `docker compose --profile init up -d rustfs-init`，并使用 `UI_LANG` 而不是 `LANG` 作为脚本内语言变量。`UI_LANG` 可以避免覆盖 shell locale；`up -d` 更贴近 compose service 生命周期。

## 后续演进方向

### 1. 抽出 channel projection

当前 channel message projection 嵌在 callback 处理链路里，短期有利于快速同步状态，但长期会让 callback service 同时承担持久化、运行状态转换和频道展示投影三种职责。后续可以抽出独立的 channel projection service，让 callback service 只发布执行事实或调用明确的投影接口。

演进目标不是立即删除 callback，而是让 callback 只负责接收和归档执行事件，频道消息由可测试、可重放的投影层生成。

### 2. 让 AgentRun 成为执行事实源

本次合并只把 `AgentRun` 当作补充持久化目标。后续可以逐步把 `AgentRun` 提升为一次执行的事实源：

- run status、state patch、tool executions、workspace export 和最终消息都按 run 聚合；
- channel execution placeholder 记录关联的 run id；
- 频道最终消息可以从 run outcome 投影生成；
- replay、artifact drawer、mobile timeline 和 channel message 使用同一套 run 数据。

这个方向能减少 `AgentSession`、callback side effect 和 channel message 之间的隐式同步关系。

### 3. 收敛 preset ownership 模型

过渡期同时支持 `scope == "system"` 和 `user_id == SYSTEM_USER_ID` 是为了合并安全。长期应该明确一个主模型。更推荐以 `scope` 表达产品归属，以 `user_id` 表达创建者或拥有者：

- `scope == "system"`：全局系统预设；
- `scope == "workspace"`：workspace 成员可见；
- `scope == "user"`：个人预设；
- `SYSTEM_USER_ID` 只作为系统创建者或迁移兼容字段，不再作为可见性的核心判定。

如果采用这个方向，需要补一次数据迁移或读取层兼容期，避免已有系统预设突然不可见。

### 4. 将 workspace feature flag 移出 auth config

`workspace_features_enabled` 暂留 `/auth/config` 是本次合并的低风险选择，但长期不应让认证配置承载产品功能开关。后续可以增加独立的 frontend/runtime config endpoint，用于返回 workspace、server collaboration、admin console、runtime policy 等产品能力开关。

这样前端可以先读取认证状态，再读取产品能力配置，减少 auth schema 因产品开关增长而变得臃肿。

### 5. 展示实际生效的 runtime 配置

managed system env vars 覆盖 `.env` 后，任务最终使用的模型、provider、env allowlist 和 runtime policy 可能来自后台配置，而不是用户提交时的显式字段。后续应考虑在 session/run 详情中展示实际生效配置，特别是 persistent agent 和频道触发任务。

这有助于排查“为什么这个 agent 用了某个模型”或“为什么某个 env 没注入”的问题。

## 风险与前提

- 本文假设频道协作体验是当前分支合并的首要保护对象，因此 callback projection 本次不重构。
- 本文假设 `dev` 的 auth/admin/runtime policy 是后续平台底座，合并时应尽量吸收而不是回退。
- 本文中的兼容策略会增加短期复杂度，尤其是 preset ownership 和 auth config 边界。后续需要用独立 spec 或 constitution 收敛这些模型。
- 如果后续产品方向决定所有执行展示都以 run 为核心，则 callback projection 需要重新设计为事件投影，而不是继续在 callback service 内部扩展。

## 小结

本次合并应采取“频道主线优先、平台底座吸收、冲突处短期兼容”的策略。最关键的取舍是：保留当前分支 callback 驱动的频道投影机制，同时把 `AgentRun` 作为 run replay 和后续演进的事实载体逐步接入。

这个策略能降低本次合并风险，也为后续把 channel messages、workspace artifacts、tool executions 和 run replay 统一到 `AgentRun` 维度留下清晰路径。
