# 后端启动期间 Builtin Skill 同步性能调研

## 元数据

| 字段 | 值 |
| --- | --- |
| 创建日期 | 2026-05-10 |
| 研究领域 | performance-investigation |
| 关联 spec | 无 |
| 状态 | open |

## 课题描述

Backend 服务每次冷启动时，`LifecycleBootstrapService.bootstrap_all` 会同步所有 builtin skill 资产到 S3。当前观察到从启动日志 `Starting application...` 到最后一个 skill 同步完成，耗时约 **2 分 26 秒**，其中绝大部分时间花在 skill 资产上传上。这导致开发环境每次重启都需要等待较长时间，影响迭代效率。

本次调研的目标是定位慢启动的根因，量化各阶段耗时，并评估可行的优化方向。

## 调研方法

- 代码审查：从 `lifespan.py` 入口逐层追踪启动链路
- 日志时间戳分析：根据结构化日志中的时间戳量化每个 skill 的同步耗时
- 代码路径分析：识别 I/O 瓶颈、串行化点和冗余操作

## 发现与分析

### 发现 1: 启动链路完全串行

启动链路为 `lifespan.py` → `run_in_threadpool(bootstrap_all)` → `SkillBootstrapService.bootstrap_builtin_skills`。虽然 `run_in_threadpool` 避免了阻塞 async 事件循环，但由于 `lifespan` 中 `await run_in_threadpool(...)` 后才 `yield`，**整个应用在 bootstrap 完成之前不会开始接收请求**。

在 `builtin_skills.py` 第 97-105 行，7 个 builtin skill 通过普通 `for` 循环逐个处理，无任何并发：

```python
for definition in BUILTIN_SKILLS:
    bundle = cls._build_bundle(definition)
    existing = SkillRepository.get_by_name_and_scope(...)
    cls._sync_bundle_assets(storage_service, bundle, existing)
    cls._ensure_builtin_skill(db, bundle)
```

三个 bootstrapper（skills、MCP servers、preset visuals）在 `bootstrap.py` 第 19-21 行也是串行调用，共享同一个数据库事务。

### 发现 2: 单个 skill 内部文件逐个上传

`S3StorageService.sync_directory`（`storage_service.py` 第 332-412 行）对源目录中的每个文件执行一次独立的 `upload_file` 调用。每次调用都是一个独立的 HTTP 请求到 S3 endpoint。对于 `minimax-docx`（75 个文件），这意味着 75 次串行 S3 PUT 请求。

同步完成后，还会调用 `list_objects` 列出 S3 上已有的 key，计算差集后逐批删除过期文件。这又引入了额外的 S3 LIST + DELETE 请求。

### 发现 3: 即使版本未变也会计算全量 hash

`_build_bundle`（第 193-225 行）在构建 bundle 时，**无论 skill 是否有变更**，都会调用 `_compute_asset_hash` 对整个资产目录计算 SHA-256。这个方法遍历目录中每个文件、读取其全部内容并更新到 hash digest 中（第 334-350 行）。对于 `minimax-docx` 的 75 个文件，这意味着启动时需要把所有文件内容读入内存。

虽然 `_sync_bundle_assets` 会对比版本并跳过未变更的 skill，但 hash 计算的开销已经产生。

### 发现 4: 各 skill 同步耗时与文件数强相关

从日志时间戳提取的耗时数据：

| Skill | 文件数 | 耗时（秒） | 备注 |
| --- | --- | --- | --- |
| gif-sticker-maker | 8 | ~9 | |
| minimax-docx | 75 | ~77 | 最大瓶颈 |
| minimax-multimodal-toolkit | 16 | ~16 | |
| minimax-pdf | 12 | ~13 | |
| minimax-xlsx | 25 | ~25 | |
| pptx-generator | 6 | ~6 | |
| **合计** | **142** | **~146** | 未计入 skill-creator |

每个文件的平均同步耗时约 1 秒，主要由 S3 PUT 请求的网络 RTT 决定。

### 发现 5: S3 连接配置对延迟有放大效应

`S3StorageService.__init__` 中配置了 `connect_timeout` 和 `read_timeout`，但 boto3 的标准重试策略 `mode: "standard"` 默认最多 3 次重试。在开发环境中，如果 S3 endpoint 延迟较高（如跨区域或使用 VPN），每次请求的尾部延迟会累加到 142 次请求的总耗时中。

## 结论与建议

### 短期优化方向

- **后台异步执行**：在 `lifespan.py` 中不 `await` skill 同步，而是将其作为后台任务，让应用立即开始接受请求。这是改动最小、收益最明确的方案。风险最低，不影响现有同步逻辑，仅改变执行时机。需要注意 skill 尚未同步完成时，如果已有请求访问该 skill 的 S3 资源，需要考虑降级行为。

- **并行化 skill 同步**：在 `bootstrap_builtin_skills` 中使用 `concurrent.futures.ThreadPoolExecutor` 并行处理多个 skill，理论上可将总耗时从 ~146 秒降低到 ~77 秒（受限于最慢的 skill）。需要注意 boto3 session 不是线程安全的，每个线程需要独立的 S3 client，数据库 session 也需要各自隔离。

- **跳过未变更 skill 的 hash 计算**：先从数据库读取已有 version，仅对 version 可能变更的 skill 计算 hash。需要一个轻量的"目录是否变更"检测机制（如比较 mtime 或文件清单）。

### 中期优化方向

- **并行化单 skill 内的文件上传**：在 `sync_directory` 内部使用线程池并行上传文件，将 `minimax-docx` 的 75 次串行 PUT 变为并发执行。与并行化 skill 同步一样，需要处理 S3 client 的线程安全问题。

- **引入 manifest 缓存**：将每个 skill 的文件清单和 hash 存储为本地缓存文件（如 `.sync_manifest.json`），启动时先比对缓存而非每次重新计算。需要处理缓存失效和一致性问题。

## 未解问题

- `bootstrap_on_startup` 设置为 `False` 时，是否有其他机制触发 skill 同步？如果没有，跳过启动同步是否会导致 S3 上的 skill 资产过期。
- 三个 bootstrapper 共享同一个数据库事务是否必要。如果 skill 同步失败但 MCP server 同步可以成功，当前设计会回滚所有操作。
- 生产环境的 S3 延迟是否比开发环境好。如果生产部署的 S3 endpoint 在同一内网，延迟可能不是问题，优化重点应放在 hash 计算和串行化上。

## 附录

### 相关代码文件

| 文件 | 职责 |
| --- | --- |
| `backend/app/lifecycle/lifespan.py` | FastAPI lifespan 入口，触发 bootstrap |
| `backend/app/lifecycle/bootstrap.py` | 编排三个 bootstrapper 的执行顺序 |
| `backend/app/lifecycle/builtin_skills.py` | Builtin skill 同步逻辑（hash 计算、S3 上传、DB upsert） |
| `backend/app/services/storage_service.py` | S3StorageService，底层文件上传/删除实现 |

### 原始启动日志

```
2026-05-09T12:14:18.937Z INFO Starting application...
2026-05-09T12:14:18.938Z INFO Database engine initialized
2026-05-09T12:14:27.338Z INFO builtin_skill_assets_synced file_count=8  skill_name="gif-sticker-maker"
2026-05-09T12:15:44.198Z INFO builtin_skill_assets_synced file_count=75 skill_name="minimax-docx"
2026-05-09T12:16:00.610Z INFO builtin_skill_assets_synced file_count=16 skill_name="minimax-multimodal-toolkit"
2026-05-09T12:16:13.013Z INFO builtin_skill_assets_synced file_count=12 skill_name="minimax-pdf"
2026-05-09T12:16:38.737Z INFO builtin_skill_assets_synced file_count=25 skill_name="minimax-xlsx"
2026-05-09T12:16:44.940Z INFO builtin_skill_assets_synced file_count=6  skill_name="pptx-generator"
```
