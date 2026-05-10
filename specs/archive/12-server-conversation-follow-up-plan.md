# Server conversation follow-up polish plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-05 |
| **预期改动范围** | frontend conversation shell / mentions UX / tasks workspace / channel settings and members modals / i18n copy |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | implemented |

## 实施阶段

- [x] Phase 0: 收敛当前标注问题与范围
- [x] Phase 1: 修复主内容区模式切换与导航细节
- [x] Phase 2: 完善聊天输入与消息动作体验
- [x] Phase 3: 重做 tasks workspace 结构与交互
- [x] Phase 4: 增补 channel / members 管理弹窗

## 实现记录

- 2026-05-05: 已按本 spec 完成 server conversation follow-up polish。`Inbox / Saved / Search` 从 channel route 切回 server-level 主区渲染，`Tasks` 进入 channel task workspace 并保留 `Board / List` 切换。
- 2026-05-05: 已补 textarea `@` candidates，候选来源为当前 channel agents 与可见 human message authors / channel creator。
- 2026-05-05: 已把 message row 的 `Reply / Save` 从正文下方收敛到 hover 后右上角 icon，并在 reply icon 上显示回复数。
- 2026-05-05: 已补 channel settings modal 与 members modal，并补齐主干后端闭环：channel name / description update、delete channel、list / add human channel members、archive channel。前端设置保存、删除和 add member 已改为真实 API 调用。

---

## 背景

### 问题陈述

当前 `servers` 和 `channels` 已经进入统一的 chat-first shell，但根据最新一轮浏览器标注，仍有一批关键问题没有收口：

- `Inbox` 与 `Saved` 需要确认主内容区真实渲染，而不是只切左侧选中态
- 顶部 channel header 仍有冗余按钮和信息
- `@` 输入还没有出现 channel 内 human / agent 候选列表
- `Tasks` workspace 还需要进一步贴近参考图里的四列竖排排版
- `channel` 管理和 `members` 管理需要明确的 modal 交互

这批问题已经超过单纯的样式修边界，需要单独沉淀一个后续 spec，避免继续和当前 conversation 壳子的重构混在一起。

### 目标

这份 spec 的目标是承接当前会话壳子的第二轮完善，重点包括：

- 确保 `Inbox` / `Saved` 的主内容模式稳定可用
- 为 textarea 增加 channel participants 的 `@` 候选列表
- 去除冗余 header 按钮和文本
- 把 `Tasks` workspace 调整到更接近参考图的四列 kanban 风格
- 为 channel 编辑和 members 管理补齐 modal

### 关键洞察

#### 1. 当前问题是“收口交互”，不是“推翻结构”

三段默认布局、reply 右抽屉和会话主线已经成立。这一轮只需要在现有壳子上补交互和 polish，不需要再重做架构。

#### 2. 需要明确区分“直接修复”与“完整功能”

像 `Inbox / Saved` 主区切换、header 精简、tasks 四列是直接修复；而 `@` 候选列表、channel 设置 modal、members modal 则需要更完整的数据和交互方案，必须显式进入 spec。

---

## Phase 0: 收敛当前标注问题与范围

### 目标

先把本轮标注拆成几个可以独立落地的子问题，避免继续边改边扩。

### 任务清单

#### 0.1 归类当前问题

**直接修复：**

- 去掉 channel header 中冗余的 server 字体
- 去掉顶部 `TASKS` tab
- 去掉 header 中不需要的第一个按钮
- 让 `Search / Tasks / Inbox / Saved` 更像现有 sidebar item
- 确保 `Inbox / Saved` 在主内容区真实展示
- 把消息 item 动作改成 hover 右上角 icon
- `Tasks` workspace 改成四列竖排

**后续完整能力：**

- textarea `@` 候选列表
- channel 编辑 modal
- members / add member modal

**验收标准：**

- [x] 每条标注都归入明确阶段
- [x] 直接修复与后续完整能力分离

---

## Phase 1: 修复主内容区模式切换与导航细节

### 目标

确保 `Search / Tasks / Inbox / Saved` 都能正确驱动主内容区，并统一左侧导航样式。

### 任务清单

#### 1.1 修复 `Inbox / Saved` 主内容区

**描述：** 点击 `Inbox / Saved` 时，右侧主内容区必须真实切换到对应 feed，而不是只改变左侧选中态。

**验收标准：**

- [x] `Inbox` 展示 inbox feed
- [x] `Saved` 展示 saved feed

#### 1.2 收口左侧模式导航样式

**描述：** `Search in server / Tasks / Inbox / Saved` 之间不要额外卡片留白，样式应和现有 sidebar item 更接近。

**验收标准：**

- [x] item 之间不再显得像独立卡片
- [x] active / hover 态与现有项目风格一致

---

## Phase 2: 完善聊天输入与消息动作体验

### 目标

把消息 item 和 textarea 的交互收口到真实协作面。

### 任务清单

#### 2.1 `@` 候选列表

**描述：** 在 textarea 输入 `@` 后，显示当前 channel 内的 human / agent 候选列表。第一版可以先做简单列表，不要求完整 slash/autocomplete 体系。

**验收标准：**

- [x] 输入 `@` 能弹出列表
- [x] 列表至少包含当前 channel 内 human / agent

#### 2.2 消息动作改成 hover icon

**描述：** `Reply / Save` 不再常驻正文下方，而是在 hover 后显示到消息头部右上角，用 icon 表示；若有 replies，显示对应数字。

**验收标准：**

- [x] 默认正文下方不再常驻 `Reply / Save`
- [x] hover 后右上角显示 icon 动作
- [x] 回复数以数字形式跟随 reply 动作显示

---

## Phase 3: 重做 tasks workspace 结构与交互

### 目标

让 `Tasks` workspace 更接近参考图中的四列竖排 kanban。

### 任务清单

#### 3.1 固定四列竖排

**描述：** `todo / in_progress / in_review / done` 应直接以四个竖列展示，而不是列表式展开。

**验收标准：**

- [x] board 模式为四列竖排
- [x] 每列有状态名、数量和空态

#### 3.2 保留 channel 切换与 board/list 切换

**描述：** 顶部保留 channel selector 与 `Board / List` 切换，交互方式参考给出的 Slock 任务页。

**验收标准：**

- [x] 顶部保留 channel selector
- [x] `Board / List` 切换可用

---

## Phase 4: 增补 channel / members 管理弹窗

### 目标

把 header 里的管理动作变成明确的 modal 交互。

### 任务清单

#### 4.1 channel 编辑 modal

**描述：** 点击设置按钮后，用 modal 展示：

- 名称
- 描述
- 保存修改
- archive
- delete

**验收标准：**

- [x] spec 中明确 channel 编辑 modal 的结构和动作

#### 4.2 members modal

**描述：** 点击成员数按钮后，用 modal 展示：

- agents
- humans
- add member 按钮

参考用户给出的 Slock 图。

**验收标准：**

- [x] spec 中明确 members modal 的结构
- [x] add member 作为底部主按钮存在

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 继续把小修和新能力混做 | conversation shell 再次失控 | 明确直接修复和后续能力分阶段 |
| `@` 列表一次做过重 | scope 膨胀 | 第一版只做简单候选列表 |
| tasks workspace 继续保留列表心智 | 无法对齐参考图 | 固定四列竖排作为 board 主视图 |

---

## 总结

这份 spec 用来承接当前 server conversation shell 的第二轮完善。它不再改主结构，而是集中修复：模式切换、hover 动作、mention 列表、四列 tasks workspace，以及 channel / members 管理弹窗。
