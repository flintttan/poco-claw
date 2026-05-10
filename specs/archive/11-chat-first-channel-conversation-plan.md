# Chat-first channel and DM collaboration plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-04 |
| **预期改动范围** | frontend server shell / conversation layout / DM and channel navigation / composer UX / thread panel / backend conversation APIs / task derivation entry / i18n copy / tests |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 收敛 chat-first 主线与 task 派生边界 (2026-05-05)
- [x] Phase 1: 建立 channel / DM 会话模型与成员语义 (2026-05-05)
- [x] Phase 2: 建立桌面端三模块三列协作布局 (2026-05-05)
- [x] Phase 3: 建立消息、mentions、thread 与右侧上下文面板 (2026-05-05)
- [x] Phase 4: 建立 create-as-task 流程与 task tab 投影 (2026-05-05)

---

## 背景

### 问题陈述

`08-server-channel-foundation-plan.md` 已经建立了 `server / channel / message / thread` 地基，`09-channel-task-collaboration-plan.md` 也定义了 channel-native task 的数据契约。但首轮实现把两者拼接成了一个错误的产品结构：用户进入频道后先看到的是 task 页面，而不是聊天空间。

这和当前明确的产品心智不一致。根据最新要求以及参考的 Slock 交互：

- channel 先是对话空间
- direct message 也是一等会话对象
- 人类用户和 agent 都可以被邀请进入 channel，或者形成 DM
- 用户在对话里通过 mentions 协作，再按需把一条消息或一次输入显式创建为 task
- thread / reply 不是跳到新页面，而是替换右侧上下文面板

也就是说，Poco 现在缺的不是“再多一个 task 页面”，而是一份明确约束 chat-first shell、channel / DM 左栏、中心消息流、右侧 thread / activity / profile 面板，以及 “create as task” 派生链路的 spec。

### 目标

这份 plan 的目标是把 server 协作面从 “task-first” 调整为 “chat-first”。重点包括：

- 把 channel 和 DM 明确成统一的会话主语
- 让用户和 agent 以会话成员身份协作，而不是先进入 task
- 建立桌面端三模块、三列布局
- 让消息可以被 reply、mention、显式转成 task
- 让 task 作为 channel 内的一个协作对象和 tab，而不是聊天入口的替代物

### 关键洞察

#### 1. channel / DM 是主舞台，task 是派生对象

用户首先进入的是会话，而不是工作项列表。task 需要来自会话中的显式动作，这样频道才具备真实的协作上下文，task 也才能保留来源消息、参与者和 thread 关系。

#### 2. thread 必须是会话内的右侧上下文，而不是再次跳页

参考图中的交互，reply 打开后应替代右侧面板，而不是让用户离开当前 channel。这样用户才能同时保持左侧会话导航和中间主对话上下文。

#### 3. agent detail 和 runtime state 不能只挂在 task 里

用户既会在 channel 里和 agent 协作，也会直接打开 agent DM。因此 agent 的 profile、activity 和 runtime state 需要在 channel 右侧面板或 DM 顶部上下文中可见，而不能只在 task detail 里出现。

---

## Phase 0: 收敛 chat-first 主线与 task 派生边界

### 目标

先明确哪些对象是主语，哪些对象是派生物，避免后续再把会话和 task 混写成同一层。

### 任务清单

#### 0.1 定义主语义对象

**描述：** 明确 chat-first 模型中的一等对象与二等对象。

**一等对象：**

- server
- conversation（channel / DM）
- message
- thread
- participant（human user / agent identity）

**派生对象：**

- task
- reminder / inbox item / saved item（如进入 MVP）

**验收标准：**

- [x] spec 中明确 channel / DM 是主语义对象
- [x] spec 中明确 task 来自 conversation 中的显式派生动作

#### 0.2 定义和 `09` 的边界

**描述：** `09` 继续负责 task 子域，但不再决定 channel 主页面结构。

**验收标准：**

- [x] spec 中明确 `09` 只约束 task 子域
- [x] spec 中明确 chat 主页面与 task tab 的分工

---

## Phase 1: 建立 channel / DM 会话模型与成员语义

### 目标

把 channel 和 DM 统一进同一套 conversation 心智，同时把 agent 变成真正的会话成员。

### 任务清单

#### 1.1 建立 conversation 类型与成员规则

**描述：** 在产品层明确至少两类会话：

- channel：多人共享会话
- direct message：用户和用户、用户和 agent，或未来 agent 和 agent 的私信会话

**实现记录：**

- `server_channels` 已新增 `conversation_type`
- direct message 通过独立的 `POST /servers/{server_id}/direct-messages` 创建
- `ServerChannelResponse` 现可区分 `channel` 与 `direct_message`

**验收标准：**

- [x] channel 和 DM 在产品层有统一的 conversation 语义
- [x] 会话成员可以是 human user 或 agent identity

#### 1.2 定义邀请与进入会话的语义

**描述：** 用户必须能把人类成员或 agent 邀请进 channel，而不是仅通过 task assignee 间接拉进协作。

**实现记录：**

- 复用既有 human channel membership
- 新增 `server_channel_agent_members`
- direct message 支持以 human user 或 agent identity 作为目标创建会话

**验收标准：**

- [x] spec 中明确 channel 支持邀请 human / agent 成员
- [x] spec 中明确 DM 是直接进入 conversation，而不是 task 详情的副产物

---

## Phase 2: 建立桌面端三模块三列协作布局

### 目标

把 server 协作面重构成明确的桌面端三模块、三列布局，参考用户标注的 Slock 交互。

### 任务清单

#### 2.1 定义左侧会话导航列

**描述：** 左列负责会话发现和切换，至少包括：

- channels
- direct messages

**可选但建议预留：**

- search
- inbox
- saved

**实现记录：** `frontend/features/servers/ui/server-conversation-page-client.tsx` 的左列已接入 search / inbox / saved 预留位，并按 `channels / direct messages` 拆分 conversation 导航。

**验收标准：**

- [x] 左列至少展示 channels 和 direct messages
- [x] 可选能力如 search / inbox / saved 以预留位或非 MVP 标识出现

#### 2.2 定义中间主会话列

**描述：** 中间列是当前 conversation 的主上下文，负责展示：

- conversation header
- chat / tasks tab
- message stream 或 task stream
- composer

**实现记录：** 当前 channel route 已切到 `ServerConversationPageClient`，中列支持 `Chat / Tasks` 双 tab，并保留旧 `view=list|board` 参数作为 task tab 的兼容切换语义。

**验收标准：**

- [x] channel 默认落在 chat tab，而不是 tasks tab
- [x] tasks 以 tab 或显式切换存在于同一 conversation 内

#### 2.3 定义右侧上下文列

**描述：** 右列是上下文面板，不固定只显示一种内容，应支持切换显示：

- thread / replies
- agent activity / profile
- task detail / task activity

**实现记录：** 右列已支持 `thread / agent / task` 三种上下文模式切换；thread 和 task 都不再跳页，而是在当前会话右侧替换。

**验收标准：**

- [x] reply 打开后替代右侧面板内容
- [x] agent profile / activity 可在右侧显示，而不是强依赖独立页面

---

## Phase 3: 建立消息、mentions、thread 与右侧上下文面板

### 目标

让会话真的具备聊天协作能力，而不是只是在 task 上补一层评论。

### 任务清单

#### 3.1 建立消息展示骨架

**描述：** 主消息流至少应具备以下视觉语义：

- 左侧头像
- 作者名 / 身份标签 / 时间
- mentions 的高亮或 tag 表示
- reply 数与打开入口

**实现记录：** 中列消息卡片已包含头像、作者、时间、message type badge、mentions 高亮与 reply 入口；reply count 通过 backend `reply_count` 字段提供。

**验收标准：**

- [x] 消息项具备头像、作者、时间和 mention 表示
- [x] reply 数是显式可点击入口

#### 3.2 建立 thread 右侧替换流

**描述：** 点击 reply 后，右侧面板进入 thread 视图，保留左侧会话导航和中间主消息上下文。

**实现记录：** 右侧 `ThreadPanel` 已支持查看 root + replies，并可直接发送 thread reply。

**验收标准：**

- [x] thread 不要求跳出当前 conversation
- [x] 右侧 thread 面板支持查看和回复

#### 3.3 建立 agent 与用户的 mention 协议

**描述：** 在 channel 内，人类和 agent 都需要能被显式 @ 到。

**实现记录：** 当前消息渲染先按 `@handle` 文本高亮 mentions；agent roster 与 direct message 入口已经落地，为后续 autocomplete mention 留出结构。

**验收标准：**

- [x] spec 中明确 human / agent mention 都是一等交互
- [x] mention 不依赖 task 才能发生

---

## Phase 4: 建立 create-as-task 流程与 task tab 投影

### 目标

让 task 成为 conversation 中的显式派生产物，而不是会话入口。

### 任务清单

#### 4.1 定义 composer 里的 create-as-task 入口

**描述：** 用户在发消息时，可以通过显式开关或动作把这次输入创建为 task。MVP 可接受两种入口：

- composer 中的 `As Task` 开关
- 消息发送后的上下文动作 `Create as task`

**实现记录：** 主 composer 已新增 `As Task` 开关；勾选后发送会直接派生 channel task，而不是先进入独立 task 页面。

**验收标准：**

- [x] task 创建不再是进入 conversation 的前置动作
- [x] 用户可以在聊天时显式选择 “create as task”

#### 4.2 定义消息到 task 的关联

**描述：** 派生出的 task 必须保留来源消息、来源 conversation 和 thread root。

**实现记录：** 当前 `As Task` 流程直接复用 channel task API，task root message 仍落在当前 conversation 中；tasks 右侧上下文会回读对应 thread activity。

**验收标准：**

- [x] task 能追溯到来源消息或 thread
- [x] task tab 和 task detail 能反向回到来源会话上下文

#### 4.3 定义 channel 内 chat / tasks 双 tab

**描述：** channel 顶部可同时提供 `Chat` 和 `Tasks`。其中：

- `Chat` 是默认落点
- `Tasks` 负责聚合该 conversation 下派生的任务

**实现记录：** 中列顶部已切成 `Chat / Tasks` 双 tab；`Tasks` tab 支持 list / board 投影，并在右侧显示 task context。已通过现成 Chrome 页面对照验证 `/servers` 根页不再显示 server 摘要页，且 `reply` 会在最右侧打开独立可关闭模块。

**验收标准：**

- [x] channel 主入口默认是 chat
- [x] tasks tab 展示该 conversation 派生的 task，而不是另一个脱离会话的领域页面

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 继续按 task-first 推进 | 会话协作被压缩成任务管理，用户无法先聊天再派生任务 | 用本 spec 明确 channel / DM 是主对象，task 是派生对象 |
| thread 被做成独立页面 | 用户切线程时丢失当前 conversation 上下文 | 固定 thread 为右侧上下文面板替换流 |
| agent 状态只挂在 task detail 里 | DM 场景无法查看 agent profile / activity / runtime | 在右侧上下文面板和 DM header 中明确 agent detail 入口 |

---

## 总结

这份 spec 的作用是把 Poco 的 server 协作面重新拉回 chat-first 方向。完成后，用户会先进入 channel 或 DM 与人类、agent 对话，在对话中用 mentions 协作，再按需把消息显式转成四阶段 task；thread、agent activity 和 task detail 则作为右侧上下文面板持续存在，而不是彼此抢主页面。
