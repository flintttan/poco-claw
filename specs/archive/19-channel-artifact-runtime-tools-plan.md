# Channel artifact runtime tools plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-07 |
| **预期改动范围** | backend channel artifact runtime access service and API / executor tool injection and prompt contract / shared context wording / runtime tests |
| **改动类型** | feat |
| **优先级** | P0 |
| **状态** | review |

## 实施阶段

- [x] Phase 0: 固化运行时访问协议与边界
- [x] Phase 1: 建立 agent-facing artifact discovery and read APIs
- [x] Phase 2: 把 channel artifact tools 注入 executor 运行时
- [x] Phase 3: 收紧 prompt 与错误语义
- [x] Phase 4: 验证多 agent 读取共享材料链路

---

## 背景

### 问题陈述

`published artifacts` 已经在后端模型和前端第四抽屉中落地，频道成员可以看见共享文件，agent trigger prompt 也会带上最近消息和部分 artifact 内容摘要。但执行层仍缺少最后一层关键能力：agent 没有显式 tool 去发现、定位和读取这些共享文件。

这会导致一个典型退化行为：agent 知道某个共享文件存在，却只能把它的 `logical_path` 猜成容器内真实路径，直接尝试访问 `/workspace/...`。当该文件并不在当前 session workspace 中时，执行就会以 `File does not exist` 失败。这个问题不是“共享文件没有发布”，而是“共享文件没有被建模成运行时一等资源”。

如果继续只靠 prompt 内联更多文件内容，会带来两个问题：

- prompt 会随着 channel 活跃度和共享材料数量持续膨胀
- agent 仍然无法对未内联的共享文件做目录发现、按需读取和检索

因此，这次改动需要把“频道共享材料存在”升级成“频道共享材料可被 agent 通过稳定协议访问”。

### 目标

这份 spec 的目标是补齐 channel published artifacts 的 agent 运行时访问协议，至少包括：

- 为 agent 提供 `list/read/search` 三类只读 tool 能力
- 明确 `logical_path` 是共享材料标识，不是 `/workspace` 真实路径
- 让 prompt 从“尽量多塞文件内容”收紧为“说明共享边界与 tool 使用方式”
- 保持 `published artifacts`、`agent persistent state`、`session workspace`、`local_mount` 的边界不变

### 非目标

以下内容不在本次范围内：

- 不引入 channel 级共享可写文件系统
- 不支持 agent 直接修改或覆盖共享 artifact
- 不把私有 `agent_state`、raw `local_mount`、session workspace 全量暴露成公共读取面
- 不在第一版引入复杂全文检索引擎或向量索引

### 关键洞察

#### 1. 共享文件问题本质上是“操作面缺失”，不是“对象缺失”

当前系统已经有 `channel_artifacts` 表、公开规则、第四抽屉和 shared context prompt。真正缺的是 agent 可调用的运行时访问面。因此这次不是新建一套共享文件系统，而是给既有对象模型补一层执行协议。

#### 2. `logical_path` 必须从“像路径的提示词”升级为“受控资源标识”

只要 agent 还能把 `logical_path` 当成本地文件路径，它就会继续猜 `/workspace`。这次改动必须把 `logical_path` 明确成共享材料标识，要求 agent 通过 tool 完成“先发现、再读取”的流程。

#### 3. prompt 负责约束与摘要，tool 负责按需访问

prompt 仍然应该提供最近消息、少量高价值 shared artifacts 摘要和协作约束，但不再承担“模拟一个共享文件系统”的职责。真正的目录能力和读取能力要由运行时 tool 提供。

---

## Phase 0: 固化运行时访问协议与边界

### 目标

先把对 agent 暴露的共享材料访问契约写清楚，避免实现时继续在 prompt、workspace path 和 artifact id 之间混用语义。

### 任务清单

#### 0.1 定义三类核心操作

**描述：** 固化第一版最小可用协议：

- `list_channel_artifacts`
- `read_channel_artifact`
- `search_channel_artifacts`

并明确它们都是 channel-scoped、read-only 的运行时能力。

**涉及文件：**

- `specs/constitution/2026-05-05-channel-shared-context-and-artifacts.md`
- `specs/draft/19-channel-artifact-runtime-tools-plan.md`

**验收标准：**

- [x] spec 明确三类 tool 的职责边界
- [x] spec 明确这些 tool 不提供写入能力

#### 0.2 固化资源标识语义

**描述：** 明确共享材料读取只接受 `artifact_id` 或 `logical_path` 这类受控标识，不接受把 `/workspace/...` 当作共享 artifact 读取入口。

**涉及文件：**

- `specs/constitution/2026-05-05-channel-shared-context-and-artifacts.md`
- `executor/app/core/engine.py`

**验收标准：**

- [x] spec 明确 `logical_path != local filesystem path`
- [x] prompt contract 明确禁止把共享 artifact 逻辑路径映射为 `/workspace`

---

## Phase 1: 建立 agent-facing artifact discovery and read APIs

### 目标

在现有 `channel_artifacts` model、repository 和 service 之上补一层稳定的 agent-facing 访问面，供 executor tool 调用。

### 任务清单

#### 1.1 建立 list/read/search service contract

**描述：** 在现有 `ChannelArtifactService` 基础上补充适合 agent 运行时调用的方法，至少表达：

- list 返回的 artifact metadata 结构
- read 返回的文本内容截断策略、二进制文件 metadata 表达、错误语义
- search 的最小匹配维度（文件名、逻辑路径、来源 agent、基础文本匹配）

**涉及文件：**

- `backend/app/services/channel_artifact_service.py`
- `backend/app/schemas/channel_artifact.py`
- `backend/app/repositories/channel_artifact_repository.py`

**验收标准：**

- [x] backend 有可复用的 list/read/search service contract
- [x] 文本与二进制 artifact 的返回语义清晰区分

#### 1.2 暴露 executor 可消费的内部 API 或等价入口

**描述：** 选择最贴合现有执行架构的接入方式，为 executor 暴露 channel-scoped artifact 访问入口。第一版优先复用现有内部服务与鉴权模型，不重新发明 channel 文件网关。

**涉及文件：**

- `backend/app/api/v1/server_channel_artifacts.py`
- `backend/app/services/channel_artifact_service.py`
- 视方案可能新增 `backend/app/api/v1/internal_*`

**验收标准：**

- [x] executor 能通过稳定接口获取 artifact list/read/search 结果
- [x] 授权继续基于 channel membership 和当前运行时上下文

#### 1.3 明确返回大小限制与错误码

**描述：** 约束读取大文本、二进制文件、缺失 artifact、无权限 artifact 的行为，避免 tool 返回语义模糊。

**涉及文件：**

- `backend/app/services/channel_artifact_service.py`
- `backend/app/core/errors/`
- `backend/tests/`

**验收标准：**

- [x] 对大文件有明确截断或 metadata-only 规则
- [x] 对 not found / forbidden / unsupported preview 有稳定错误语义

---

## Phase 2: 把 channel artifact tools 注入 executor 运行时

### 目标

让 agent 在运行时真正拿到 channel artifact tool，而不是继续只看到 prompt 中的共享文件提示。

### 任务清单

#### 2.1 设计 tool 注入方式

**描述：** 参考当前 channel task MCP 的注入思路，为 server/channel 场景补充 channel artifact tool 集。第一版可以是单独 tool，也可以是统一 namespaced tool，但必须对模型暴露清晰能力边界。

**涉及文件：**

- `executor/app/core/engine.py`
- `executor/app/core/` 下的 tool / plugin 注入相关模块
- `backend/app/services/server_agent_trigger_service.py`

**验收标准：**

- [x] channel 场景下 agent 能拿到 artifact runtime tools
- [x] 非 channel 场景不会无谓注入这组 tool

#### 2.2 绑定运行时上下文

**描述：** tool 调用需要自动绑定当前 `server_id`、`channel_id`、`agent_identity_id` 或等价上下文，避免模型手动拼接授权参数。

**涉及文件：**

- `backend/app/services/server_agent_trigger_service.py`
- `executor/app/core/engine.py`
- `executor/app/schemas/` 或相关 tool config schema

**验收标准：**

- [x] tool scope 自动继承当前 channel execution context
- [x] 模型不需要自己声明或猜测 server/channel 身份

#### 2.3 补测试覆盖

**描述：** 为 executor 注入、tool 调用和典型共享材料读取链路增加自动化测试。

**涉及文件：**

- `backend/tests/test_channel_artifact_service.py`
- `backend/tests/test_channel_shared_context_service.py`
- `backend/tests/test_server_agent_trigger_service.py`
- `executor/tests/`

**验收标准：**

- [x] 有测试覆盖 list/read/search 基本行为
- [x] 有测试覆盖 channel trigger 后 agent 可使用 artifact tools 的运行时契约

---

## Phase 3: 收紧 prompt 与错误语义

### 目标

把 prompt 从“补很多 artifact 内容”收紧成“说明共享边界、列出高价值索引、明确 tool 使用方式”，同时减少模型的错误路径假设。

### 任务清单

#### 3.1 调整 shared context prompt wording

**描述：** 更新 `ChannelSharedContextService` 生成的 prompt，保留必要摘要，但明确：

- channel published artifacts 是共享只读资源
- 共享文件的逻辑路径不是 `/workspace` 真实路径
- 当需要更多内容时，先 `list` / `search`，再 `read`

**涉及文件：**

- `backend/app/services/channel_shared_context_service.py`
- `executor/app/core/engine.py`

**验收标准：**

- [x] prompt 不再暗示 artifact 可直接通过本地文件 IO 访问
- [x] prompt 明确共享材料应通过 runtime tools 读取

#### 3.2 降低 prompt 内联负担

**描述：** 重新审视当前 artifact inline 策略，保留少量高价值内容，但避免把 prompt 继续堆成大段文件正文。

**涉及文件：**

- `backend/app/services/channel_shared_context_service.py`
- `backend/tests/test_channel_shared_context_service.py`

**验收标准：**

- [x] prompt 仍能提供高价值摘要
- [x] prompt 不依赖大规模内联来弥补 tool 缺失

---

## Phase 4: 验证多 agent 读取共享材料链路

### 目标

验证“一个 agent 发布文件，另一个 agent 通过 runtime tools 读取并继续工作”的完整协作链路。

### 任务清单

#### 4.1 覆盖跨 agent 协作场景

**描述：** 用端到端或高层服务测试覆盖以下链路：

1. agent A 在 channel 中发布 artifact
2. artifact 进入 `channel_artifacts`
3. agent B 被触发
4. agent B 可列出、检索、读取该 artifact，而不是访问 `/workspace/...`

**涉及文件：**

- `backend/tests/`
- `executor/tests/`
- 如有需要补充 `executor_manager/tests/`

**验收标准：**

- [x] 有用例覆盖跨 agent 共享材料读取
- [x] 失败日志中不再出现把 logical path 误当本地路径的默认行为

#### 4.2 校验权限和回归风险

**描述：** 重点验证非 channel 成员、无关 session、私有 `agent_state`、raw `local_mount` 不会被新 tool 误暴露。

**涉及文件：**

- `backend/tests/test_server_channel_artifact_api.py`
- `backend/tests/test_channel_artifact_service.py`
- 其他相关权限测试

**验收标准：**

- [x] 非成员无法读取 channel artifacts
- [x] 私有状态和 local mount 仍不在 tool 暴露范围内

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| ---- | ---- | -------- |
| 继续沿用 prompt-only 思路，tool 设计被弱化 | agent 仍会猜路径，问题不能根治 | 在 constitution 和 prompt 中明确“共享材料访问必须走 tool” |
| tool 返回语义不稳定 | 模型难以形成正确使用习惯 | 统一 list/read/search 返回结构、错误码和 metadata-only 规则 |
| search 设计过重 | 首版开发成本膨胀 | 第一版只做文件名、逻辑路径、来源和轻量文本匹配 |
| 误暴露私有状态或本地目录 | 权限边界被破坏 | 复用 `channel_artifacts` 作为唯一读取源，不从 `workspace` 或 `agent_state` 直接兜底 |
| prompt 仍然内联过多内容 | token 成本和噪音上升 | 把 prompt 限定为摘要与约束，按需读取交给 tool |

---

## 总结

这次改动不是重做 channel shared artifacts，而是给已存在的共享成果补齐 agent 运行时操作面。核心做法是把 `published artifacts` 从“prompt 中被提到过的共享上下文”升级为“agent 可通过 `list/read/search` 调用的一等只读资源”。这样可以直接消除模型把逻辑路径误判为 `/workspace` 本地路径的缺陷，同时继续保持私有状态、临时工作区和共享成果三者的边界稳定。
