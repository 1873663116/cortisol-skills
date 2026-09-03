---
name: skill-cleaner
description: "Codex 与 OpenClaw 技能审计：实时 Token 预算消耗、使用频次、重复技能识别、精简描述压缩。"
---

# 技能审计与精简（Skill Cleaner）

用于缩减技能注入的 Prompt Token 开销预算、识别重复技能、审计已启用/禁用的技能源路径，或决策应当清理卸载哪些冗余技能与插件。

## 标准工作流

1. 在技能目录或仓库根目录运行分析脚本：

```bash
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --months 3
```

常用参数变体：

```bash
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --no-logs
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --no-live --no-logs
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --months 6 --max-log-mb 800 --deep-logs
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --context-tokens 272000 --budget-percent 2 --no-logs
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --root ~/Dropbox/boxd/skills --no-logs
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --root ~/.agents/skills --root-only --no-logs
```

2. 依序查阅分析报告：
- `Skill Budget`：Codex 实时清单、2% 预算阈值、实际预算消耗及完整描述注入压力。
- `Description candidates`：描述过长、可通过精简文法有效节省 Token 的候选技能。
- `Duplicates`：跨 Codex 内置、插件缓存、仓库同级及个人根目录完全同名或描述/正文高度一致的重复项。
- `Unused candidates`：在近期 Codex/OpenClaw 日志中从未被用户提及且 `SKILL.md` 从未被读取过的冷门技能。
- `Root summary`：技能来源根路径以及配置中是否标记为禁用。

3. 在删除或编辑前严格核验：
- 确认拟保留的副本真实存在且能正常被系统加载。
- 当 Codex 系统内置能力已完全覆盖时，优先清理仓库本地或 `agent-scripts` 中的重复副本。
- 若仓库本地的 OpenClaw 维护者技能固化了仓库专属规范或实时运维流程，予以保留。
- 在精简描述时，完整保留触发词汇（名词实体：产品、工具、动作、对象）。

## 分析器机制备忘

- 默认情况下，通过 `codex debug prompt-input` 获取模型实际可见的精确技能列表、加载顺序、名称及别名路径；`--no-live` 则强制回退至全文件系统扫描模式。
- 文件系统扫描主要用于排查重复、禁用及归档缓存状态，不作为实际已加载的运行清单。
- 脚本模拟了 Codex 暴露给模型的结构：`- name: description (file: path)`。
- 遵循 Codex Frontmatter 解析规则：仅支持 YAML Frontmatter、默认名称取自父目录、单行清洗 `name` 与 `description`。
- 遵循 Codex `core-skills/src/render.rs` 调度逻辑：原始上下文窗口的 2% 预算，Token 消耗按 `ceil(utf8_bytes / 4)` 计算，优先加载完整描述 → 均匀截断描述 → 剔除最低行。别名表开销计入其中。
- 默认读取 `~/.codex/models_cache.json` 获取 GPT-5.5 的上下文窗口大小；默认兜底基线为 272,000 Tokens 和 2% 预算。
- 默认仅扫描常规 Codex/插件/仓库技能根目录；额外目录需通过 `--root <path>` 显式指定。
- `--root-only` 至少需要一个 `--root <path>` 参数，跳过 Codex 实时清单，仅扫描传入的根目录。
- 自动对真实路径（realpath）去重，确保软链接路径不会产生虚假重复报警。
- 针对同名技能计算描述/正文相似度，仅在正文高度雷同时提议删除。保留优先级默认顺序：Codex 系统内置技能 > Codex 直接技能 > 插件技能 > 个人/仓库本地副本。
- 默认扫描 `~/.codex/history.jsonl` 与近期 `~/.codex/sessions/**/*.jsonl`；加 `--deep-logs` 可深入扫描归档会话与 OpenClaw 日志。
- 使用证据采用启发式规则：用户 `$skill`/`use skill` 提及，以及工具调用参数中出现的路径。

## 产出规范

- 优先给出分析与清理提议；仅在用户明确授权后方可执行修改。
- 执行清理时，按类别提交小粒度 Commit：描述精简、文件删除、配置禁用。
- 严禁在未确认目标路径或未确认可丢弃的前提下，擅自删除未受版本控制（untracked）的技能目录。
