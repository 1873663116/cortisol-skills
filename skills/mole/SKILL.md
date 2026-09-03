---
name: mole
description: "安全驱动已安装的 Mole CLI (`mo`)，涵盖机器可读的系统状态、分析诊断、操作历史记录以及 Dry-run 演练接口。在用户的 Mac 上执行 `mo` 前使用。非用于编辑或审查 Mole 自身的源码。"
disable-model-invocation: true
---

# 在 Agent 中安全使用 Mole

Mole (`mo`) 用于清理、卸载、分析、优化以及监控 Mac 系统。它是一个在用户活跃机器上执行文件删除的系统工具，因此 Agent 使用它的方式必须与人类不同：**严禁猜测、严禁交由交互式 TUI 界面决定、且在用户亲眼确认候选清理清单前，严禁执行任何破坏性命令**。

## 核心安全准则

1. **删除前必须先演练预览（Dry-run），无一例外**。所有破坏性命令均支持 `--dry-run` 选项。先执行 Dry-run，读取输出结果，向用户展示即将清理删除的内容清单，待用户确认后方可执行真实清理。若 Agent 未经 `mo clean --dry-run` 演练就直接执行 `mo clean`，等于剥夺了用户唯一的一票否决权。
2. **破坏性命令原则上由用户亲手执行**，除非用户在当前轮次中明确授权要求你直接执行。“帮我清理 Mac”属于明确授权；“为什么我的磁盘满了”绝不属于授权。
3. **严禁解析 TUI 界面输出**。交互式的 `mo analyze` 与依附终端的 `mo status` 是全屏渲染的 Go 语言 TUI 程序，其输出是屏幕重绘而非线性文本流。应改用 `mo analyze --json`、`mo status --json` 或 `mo status --watch`。
4. **严禁凭空捏造命令行参数**。命令接口紧凑明确，下表已全量列出；若某项功能未在本文档提及，先运行 `mo <command> --help` 查看说明，切勿主观臆测存在 `--yes` 或 `--force` 等参数。
5. **保护项使用白名单机制**。若用户希望保留某项缓存，应使用 `mo clean --whitelist`，而非手工写脚本用 `find` 过滤。严禁使用原生的 `rm` 暴力绕过 Mole 的安全防护层。

## 场景与命令速查

| 用户诉求 | 推荐命令 |
|---|---|
| “是什么占满了我的磁盘空间？” | `mo analyze --json`（全盘分析）或 `mo analyze <path> --json` |
| “帮我释放磁盘空间” | `mo clean --dry-run` → 用户审查 → `mo clean` |
| “彻底卸载这个应用程序” | `mo uninstall --dry-run` → `mo uninstall` |
| “我的 Mac 感觉变卡了” / 缓存可能异常 | `mo optimize --dry-run` → `mo optimize` |
| “清理我旧项目遗留的构建产物” | `mo purge --dry-run` → `mo purge` |
| “清理下载目录里的安装包” | `mo installer --dry-run` → `mo installer` |
| “Mole 之前删除了哪些东西？” | `mo history --json --limit 20` |
| 获取单次 CPU / 内存 / 磁盘 / 网络快照 | `mo status --json` |
| 用于诊断的短期指标时序监控 | `mo status --watch --interval 1s`（NDJSON 格式；采集足量样本后主动终止） |

## 机器可读接口规范

以下四个机器可读接口是专为 Agent 设计的标准 API，其余交互界面均面向人类：

- **磁盘使用分析**：`mo analyze --json` 输出单行 JSON 对象，包含 `path`、`overview` 以及由 `{name, path, size, is_dir, insight}` 构成的 `entries[]` 列表（`size` 单位为字节；`insight: true` 标记了 Mole 判定为值得关注的异常项，如庞大的 iOS 备份或失控的缓存）。支持传入路径限定范围：`mo analyze ~/Library --json`。
- **清理历史追溯**：`mo history --json [--limit N]`（N 取值 1-200）输出 `logs`（操作日志与删除日志路径）以及包含 `command`、`started_at`、`items`、`size` 和动作细分统计（removed / trashed / skipped / failed）的 `sessions[]` 列表。通过查询删除日志中的具体路径，可以确定性地回答“Mole 是否误删了我的文件”，无需凭空猜测。
- **演练路径清单（Dry-run）**：`mo clean --dry-run` 会在终端输出摘要，并将所有拟删除的候选路径完整写入 `~/.config/mole/clean-list.txt`。当需要精确分析或向用户完整呈现拟删除清单时，请直接读取该文件，而非解析终端摘要输出。注意：此机制仅针对 clean；`mo purge --dry-run` 与 `mo installer --dry-run` 直接将候选列表打印到终端，不写入文件。
- **系统状态监控**：`mo status --json` 输出单次系统性能指标快照。当 stdout 非 TTY 时会自动切换为 JSON，但在脚本中建议显式传递 `--json`。`mo status --watch --interval 1s` 每秒输出一行完整的 JSON 对象。**务必限定监控时长或采样条数，在收集到足够证据后立即主动终止进程**，严禁让后台监控任务无休止持续挂起。

## 关键命令注意事项

- `mo clean` 会同时扫描已被用户删除的应用所残留的孤儿配置；它不会触碰已安装的应用（卸载应用请使用 `mo uninstall`）。
- `mo clean --external <path>` 用于清理外接磁盘卷上的 macOS 隐藏元数据。
- `mo purge` 专门清理可随时重新生成的项目构建产物（`target/`、`build/`、`dist/`、`.next/`）。它刻意不触碰依赖网络拉取的目录（`node_modules/`、`Pods/`、`venv/`），因此 purge 清理后的项目始终支持本地重新构建恢复。`mo purge --paths` 可配置扫描目录；`--include-empty` 可显示零字节候选项。
- `mo optimize` 负责刷新系统缓存并重启系统服务。它是少数几种效果不是“删除文件”的系统级命令，在运行前应明确向用户告知其具体影响。
- `mo update` 用于自我更新；`mo update --nightly` 用于安装未发布的 `main` 分支。未经用户明确要求，切勿擅自运行升级命令。
- 任何命令加上 `--debug` 均会打印详细的操作日志。仅在命令未产生任何效果且需要排查原因时使用，日常使用切勿开启。

## 异常与兜底机制

**`mo clean` 的清理删除默认是永久性的**。缓存清理会直接物理删除文件，而不会移入废纸篓，因此通常无法直接恢复。这正是“准则 1（演练预览即撤销防线）”必须严格执行的根本原因。`mo uninstall` 是例外：它会将应用及其关联残留移入废纸篓，因此在清空废纸篓前尚可恢复。

Mole 具备完整的审计记录。`mo history --json` 会标明删除日志文件的路径，每笔删除操作都会以制表符分隔的一行记录存盘：时间戳、模式、大小、状态、路径。当用户询问“Mole 是不是删了我的某文件”时，直接读取该日志以事实作答。若需长期保护该文件，将其加入白名单（`mo clean --whitelist`），以便后续清理自动跳过。
