# Server agent 生命周期、重启停止与移除语义决策

## 元数据

| 字段 | 值 |
| --- | --- |
| **决策日期** | 2026-05-08 |
| **关联 spec** | `2026-05-04-server-channel-agent-persistence.md`、`2026-05-06-server-agent-observability-tasks-and-persistence.md`、`2026-05-08-persistent-agent-message-passing-and-tool-injection.md`、`20-channel-message-reactions-plan.md`、`23-unified-channel-runtime-tools-plan.md` |

## 决策摘要

Server agent 已经从一次性 preset 执行器升级为 server/channel 中的长期协作身份。这个身份会出现在历史消息、execution placeholder、reaction、published artifacts、private persistent state 和 colleague profile 中。因此，"从频道移除" 和 "从 server 移除" 不能再等价为物理删除 `agent_identity`。

最终决定：server agent 的正常移除采用软删除语义。`AgentIdentity` 是历史可追溯身份，不能因为离开当前 server/channel 就断开历史消息头像、reaction actor 或执行详情入口。Channel 级移除只影响当前 channel membership 和该 channel 队列；server 级移除会停止运行、取消所有待执行工作，并把 agent 标记为从 server 移除，但仍保留 identity、private state、历史消息和 reaction。

## 背景

频道内 agent 消息目前依赖当前 channel agent 列表反查头像和 profile。当 agent 被从 server 物理删除后，历史消息仍保留 `actor_label`、`agent_handle`、`agent_visual_key` 等快照字段，但前端无法再通过 `agent_identity` 获取完整身份，于是头像退化为首字母 fallback，点击头像也无法再进入详情查看过往工作输出。

Reaction 也暴露了同一类问题。Reaction 是 `message x emoji x actor` 的轻量互动关系。如果 agent identity 被物理删除，`actor_agent_identity_id` 级联删除会让这个 agent 贴过的 reaction 一起消失。这不符合协作产品的直觉：agent 离开频道或 server 不应改写历史互动记录；后续如果同一个 agent 又被拉回，也应该延续同一个身份历史，而不是创建一个断裂的新身份。

因此，需要把 agent 生命周期、运行控制和移除语义一起固化，避免后续实现继续把"停止运行"、"退出频道"、"从 server 移除"和"清除历史身份"混在一起。

## 最终决策

- **产品决策**：`AgentIdentity` 是 server 内的长期协作身份与历史锚点。正常业务流中的移除不物理删除 identity。
- **产品决策**：从 channel 移除 agent 只表示该 agent 不再是当前 channel 的 active member；不影响它在其他 channel、DM、历史消息、reaction 和 private state 中的身份。
- **产品决策**：从 server 移除 agent 表示该 agent 不再可被当前 server 使用、mention、分配或加入频道；但历史消息、reaction、execution 详情和 private persistent state 仍可追溯。
- **产品决策**：被移除的 agent 后续可以重新加入 server。重新加入应恢复同一个 identity，而不是创建一个新的同名 agent。
- **运行决策**：Restart 用于丢弃当前 active execution 并重置运行时状态，但不清空 queue 中仍然等待执行的任务。
- **运行决策**：Stop 用于丢弃当前 active execution 并把 agent 置为不可继续调度的 inactive 状态；后续是否恢复执行必须通过明确操作完成。
- **运行决策**：Remove from channel 清理当前 channel 中该 agent 的 queued work 和 execution placeholder，不影响其他 channel 的 queue。
- **运行决策**：Remove from server 立即停止该 agent 的 active execution，取消该 agent 在 server 范围内所有 queued work，并把相关 placeholder 标记为 canceled。
- **UX / UI 决策**：colleague profile 中的 server 级移除入口文案使用 `Remove`，并必须通过二次确认对话框展示影响范围。
- **UX / UI 决策**：channel 右上角成员管理中的移除入口只表达当前 channel 级移除，不能误导为 server 级移除。

## 设计约束与不变量

- `agent_identities` 的正常移除应采用 `removed_at` / `removed_by` 这类软删除字段，或等价的可审计状态字段。
- `lifecycle_state` 不应单独承担软删除语义。`inactive` 表示不运行或不可调度；`removed_at` 表示不再属于当前 server 的可用成员集合。
- 列表查询必须区分"可用 agent"和"历史 agent"：
  - mention 候选、channel add agent 候选、可分配 agent 默认排除 removed agent。
  - 历史消息、reaction actor、execution drawer、artifact owner 和 colleague 历史详情允许解析 removed agent。
- 历史消息头像渲染不能只依赖当前 channel active agent 列表。消息中存在 `agent_identity_id` 时应优先用 identity 解析；没有 identity 时才退回 `agent_handle` / `agent_visual_key` 快照。
- Agent reaction 不应因为 agent 从 channel 或 server 移除而消失。正常 remove flow 不删除 reaction。
- 如果未来存在物理清除 agent identity 的后台维护能力，它必须是单独的 owner/admin 高风险操作，并明确说明会破坏历史关联；不能复用普通 `Remove`。
- Restart 不改变 membership，也不清空 queue。
- Stop 不改变 membership，但会让新的自动调度停止，直到 agent 被显式恢复。
- Remove from channel 不改变 server identity，也不清理其他 channel 的 queued work。
- Remove from server 不物理删除 identity，但会使所有 channel membership 失效，并取消 server 范围内该 agent 的未执行工作。

## 推荐数据语义

`agent_identities` 建议保留为历史身份主表，并增加软删除字段：

```text
agent_identities
  id
  server_id
  preset_id
  handle
  display_name
  visual_key
  lifecycle_state
  removed_at
  removed_by
```

语义区分如下：

| 字段 | 表达的问题 |
| --- | --- |
| `lifecycle_state = active` | agent 是可调度的长期协作成员 |
| `lifecycle_state = inactive` | agent identity 仍存在，但当前不应继续调度 |
| `removed_at is not null` | agent 已从当前 server 的可用成员集合中移除 |
| channel membership `status = active` | agent 当前属于这个 channel |
| channel membership `status = removed/inactive` 或记录删除 | agent 不再属于这个 channel |

`server_channel_message_reactions.actor_agent_identity_id` 在软删除模型下可以继续指向 `agent_identities.id`。因为 identity 不再被普通 remove 物理删除，reaction 不需要为了保留历史而复制一份 actor 快照。若后续引入物理清除，才需要额外的 archival snapshot 或 `ondelete = SET NULL` 策略。

## 操作语义

### Restart agent

Restart 是运行控制操作，不是成员管理操作。

- 丢弃当前 active execution。
- 重置 runtime/client/container 中与当前执行绑定的状态。
- 保留 queue 中尚未开始的任务。
- 保留 server/channel membership。
- 保留 private persistent state。
- 保留历史消息、reaction、artifact 和 execution 记录。

### Stop agent

Stop 是让 agent 暂停参与自动调度的操作。

- 丢弃当前 active execution。
- 将 runtime 状态置为 idle 或 stopped。
- 将 `lifecycle_state` 置为 inactive 或等价不可调度状态。
- 不删除 queue 数据，但调度器必须避免继续启动 inactive agent 的新执行，除非产品明确选择 Stop 时同步取消 queue。
- 不改变 server/channel membership。

如果 Stop 的产品语义未来希望"停止并清空待办"，应另设 `Cancel queued work` 或在确认对话框中明确展示，而不能和普通 Stop 混用。

### Remove from channel

Channel 级移除是当前频道范围内的成员管理操作。

- 只影响当前 channel 的 agent membership。
- 取消该 agent 在当前 channel 中尚未开始的 queued work。
- 将当前 channel 中相关 execution placeholder 标记为 canceled。
- 不影响其他 channel 的 membership 和 queue。
- 不影响 server 级 agent identity。
- 不影响历史消息、reaction、artifact 和 execution 详情。

### Remove from server

Server 级移除是高影响成员管理操作，但仍然不是物理删除。

- 停止该 agent 的 active execution。
- 取消该 agent 在 server 范围内所有 queued work。
- 将相关 execution placeholder 标记为 canceled。
- 让该 agent 在所有 channel 中不再是 active member。
- 标记 `agent_identities.removed_at` 和 `removed_by`。
- 将 `lifecycle_state` 置为 inactive 或等价不可调度状态。
- 从 mention 候选、channel add agent 候选、agent directory 默认视图中隐藏。
- 保留 private persistent state、历史消息、reaction、artifact 归属和 execution drawer 入口。

## UI 确认语义

Server 级 Remove 必须二次确认，因为它跨 channel 并会取消该 agent 的未执行工作。

建议文案：

- 按钮：`Remove`
- 标题：`确认将 {agentName} 从当前 server 移除吗？`
- 正文：`将会从 {channelNames} 等频道中移除，并取消尚未开始的任务。历史消息、表情互动和工作输出仍会保留。`
- 操作：`取消` / `移除`

Channel 级 Remove 的文案必须明确当前频道范围，例如：

- `Remove from channel`
- 正文说明只会影响当前频道，并取消当前频道中尚未开始的任务。

## 后续实现提示

- 后端 service 层应把 `remove_agent_from_server` 从 hard delete 改为 soft remove，并明确过滤默认列表查询。
- `list_channel_agents` 和 mention target 收集逻辑只返回 active membership 且未 removed 的 agent。
- 历史 message/reaction hydration 需要允许读取 removed agent。
- Colleague profile 可以在历史入口中展示 removed agent 的只读详情；Restart、Stop、Message 等动作应根据 removed 状态禁用或转为 `Restore`。
- 如果用户重新邀请同一个 removed agent，应优先恢复同一个 identity，并恢复必要的 channel membership，而不是创建重复 handle 的新 identity。

## 历史变更

| 日期 | 变更 | 说明 |
| --- | --- | --- |
| 2026-05-08 | 初次记录 | 固化 server agent 软删除、restart、stop、channel remove 与 server remove 语义 |
