# 临时 Agent 运行时与数字分身能力缺口调研

## 元数据

| 字段 | 值 |
| --- | --- |
| 调研日期 | 2026-05-10 |
| 关联模块 | Server collaboration, persistent agents, executor manager |
| 关联决策 | `specs/constitution/2026-05-04-server-channel-agent-persistence.md` |
| 文档性质 | 架构演进设想与产品能力缺口记录 |

## 背景

当前 server 中的 Agent 已经具备持久运行时语义。用户在频道中 `@agent`、向 Agent 发私信，或 Agent 之间通过协作工具发起请求时，后端都会创建一个带 `agent_identity_id` 的执行任务，并显式设置 `container_mode="persistent"` 与 `agent_runtime_mode="persistent"`。这意味着该 Agent 的 `/agent_state` 会以可写方式挂载，运行结果可能影响其长期状态。

代码层面已经存在临时运行时概念：`agent_runtime_mode` 支持 `"temporary"`。在 executor manager 中，temporary 模式会把 Agent 的真实状态目录复制成只读 snapshot，再挂载到容器的 `/agent_state`。这允许执行读取 Agent 的既有背景，但不会写回该 Agent 的长期状态。不过在当前 server agent 触发链路中，这个能力还没有作为产品功能暴露；server Agent 默认都按持久运行时执行。

这个缺口会在“添加数字分身”“临时邀请某个 Agent 参与讨论”“试跑一个不污染记忆的 Agent”等场景中变得明显。用户需要的是一个可复用 Agent 形象或能力模板，但不一定希望每次互动都改写真实 Agent 的长期记忆、运行状态或私有文件。

## 当前实现观察

当前系统同时存在三层持久性概念：

1. **Agent identity**：server 内的一等 Agent 身份，关联 preset、handle、display name、生命周期和 persistent state。
2. **Agent persistent state**：挂载到 `/agent_state` 的长期状态目录，包括 `MEMORY.md`、`profile.json`、`notes/`、`state/` 和预留的 `artifacts/`。
3. **Execution workspace/container**：一次 session/run 的 `/workspace` 与 executor 容器。`container_mode` 控制容器/工作区复用语义，`agent_runtime_mode` 控制 `/agent_state` 的读写语义。

在 server agent 触发路径中，频道 mention、Agent DM 和 Agent collaboration 当前都使用：

```text
container_mode = persistent
agent_runtime_mode = persistent
```

因此它们不是临时运行，也不是只读读取 Agent 背景。只要执行链路内的 Agent 写入 `/agent_state`，就会影响该 Agent 后续 session。

temporary 模式目前更像底层能力预留：

```text
agent_runtime_mode = temporary
真实 /agent_state -> 创建 snapshot -> 只读挂载到 /agent_state
```

它能解决“读取上下文但不写回”的问题，但尚未接入 server 产品对象和 UI。

## 产品缺口

### 1. 数字分身不是持久 Agent

“添加数字分身”可能更接近一个临时 actor，而不是 server 内长期成员。它需要具备 Agent 的人格、preset 和工具能力，但不一定应该成为可长期被 @ 的同事，也不应该默认写入某个真实 Agent 的 `/agent_state`。

如果直接复用 persistent agent，会出现两个问题：

- 多个用户或频道同时试用同一个数字分身时，可能争用同一份 persistent state。
- 试验性对话、角色扮演、一次性调研会污染长期记忆和私有状态。

### 2. 私信语义目前等于持久触发

当前 Agent 私信是 `trigger_type="agent_dm"`，但运行时仍然是 persistent。用户可能误以为私信只是一次临时聊天，不会影响 Agent 的长期状态。这个心智和实际实现不完全一致。

如果未来引入 temporary DM，需要明确区分：

- “和这个 Agent 私聊”：默认是否写入长期状态？
- “临时咨询这个 Agent”：只读状态、不写回。
- “让这个 Agent 记住这件事”：显式写入长期记忆。

### 3. `/agent_state/artifacts` 的价值边界不清

`/agent_state/artifacts` 当前是私有持久目录中的预留目录，但 prompt 没有明确驱动 Agent 使用它。长期来看，它更适合存放高价值、跨任务复用、无需频道共享的私有资产，而不是每次执行的普通产物。

对于 temporary runtime，这个目录应当只读可见或来自 snapshot，避免临时执行生成的中间产物污染真实 Agent 状态。

## 可选设计方向

### 方案 A：显式“临时咨询”模式

在 Agent DM 或频道 @ 时增加一个运行模式选择：

```text
持久参与：写入该 Agent 的长期状态
临时咨询：读取该 Agent snapshot，不写回长期状态
```

技术上对应：

```text
container_mode = ephemeral 或 persistent
agent_runtime_mode = temporary
```

优点是模型简单，能直接复用现有 temporary snapshot 机制。缺点是需要清晰 UI 提示，否则用户可能不理解“临时但仍能读 Agent 背景”。

### 方案 B：数字分身作为派生 actor

把数字分身建模为从某个 preset 或 Agent identity 派生出来的临时 actor。它有单独的 session/run，但没有自己的长期 persistent state。必要时可以读取源 Agent 的只读 snapshot。

这适合“邀请一个临时专家加入讨论”“让某个角色模拟评审”等场景。它不会成为 server 的长期成员，执行完成后只留下普通消息、workspace artifact 和 run 记录。

优点是不会污染真实 Agent 状态，也不会增加 server 成员管理复杂度。缺点是如果用户希望这个分身逐渐成长，需要另一个“保存为持久 Agent”的转化流程。

### 方案 C：持久 Agent + 可控写回

允许执行先以 temporary runtime 运行，结束时由用户选择是否把部分结果写回真实 `/agent_state`。例如保存为：

- 长期记忆片段
- 私有 artifact
- 频道共享 artifact
- 新 Agent 的初始 profile

这个方向更符合“先试用，再沉淀”的体验，但实现复杂度更高，需要设计 writeback diff、用户确认、权限和冲突处理。

## 建议方向

短期建议优先采用 **方案 A + 方案 B 的组合**：

- Server 中现有 Agent 继续默认 persistent，保持当前“同事 Agent 会记住工作”的产品心智。
- 在私信或 @ 入口增加“临时咨询”能力，使用 `agent_runtime_mode="temporary"`。
- “添加数字分身”不要直接创建 persistent Agent，而是先创建 temporary actor/run；用户确认需要长期保留时，再转化为 Agent identity。

这个组合能最大化复用现有底层能力，同时降低状态污染风险。

## 技术边界建议

- `agent_runtime_mode="persistent"`：真实 `/agent_state` 以 `rw` 挂载，允许写回长期状态。
- `agent_runtime_mode="temporary"`：真实 `/agent_state` 先复制 snapshot，再以 `ro` 挂载；执行不得写回真实 Agent 状态。
- `container_mode` 不应单独承担“是否会污染长期状态”的语义；真正控制 Agent 私有状态写回的是 `agent_runtime_mode`。
- 频道共享 artifacts 继续来自 workspace export 和 `channel_artifacts` 索引，不应直接扫描 `/agent_state/artifacts`。
- 如果 temporary run 需要产物，产物应进入该 run 的 workspace export，而不是写入真实 Agent 私有 artifacts。

## 需要进一步调研的问题

- temporary actor 是否需要在频道成员列表中短暂出现，还是只作为消息作者/执行来源展示？
- temporary DM 是否复用当前 direct message channel，还是创建一次性 conversation/run？
- 用户如何把 temporary run 的结果“保存为长期 Agent 记忆”？
- 多个 temporary run 是否允许读取同一个 Agent 的 snapshot，snapshot 创建时机是触发时还是调度时？
- 是否需要在 UI 上标注“本次不会写入长期状态”，避免用户误以为 Agent 已记住结论？

## 小结

当前系统已经具备 temporary runtime 的底层基础，但 server agent 产品路径尚未使用它。这个缺口可以演进成“临时咨询”和“数字分身”能力：前者让用户在不污染长期状态的情况下调用已有 Agent，后者让用户创建一次性或可转正的临时 actor。

关键原则是区分 `/workspace` 的任务产物、`channel_artifacts` 的共享索引，以及 `/agent_state` 的身份级长期状态。临时能力应默认保护真实 `/agent_state`，只有在用户明确确认时才把高价值结果沉淀回持久 Agent。
