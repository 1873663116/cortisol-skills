---
name: dispatch
description: 如何把工作交给另一个 Agent，启动任何委派或评审组之前阅读。
disable-model-invocation: true
---

# Dispatch

委派通过 codeg 的 MCP 工具 `delegate_to_agent` 完成，除非另有说明。

`delegate_to_agent` 只接受三个参数：
- `agent_type`，取值为 `claude_code`、`codex`、`grok`、`cursor`、`open_code` 之一。
- `task`，完整的提示词。
- `working_dir`，绝对路径。

## `delegate_to_agent`

**没有模型或努力度参数** 两者都存放在各 CLI 自己的配置中；
**冷启动** 被委派代理看不到你对话的任何内容。把完整提示词作为 `task` 传入，使用绝对 `working_dir`，用指针指向文件而不是内联文件内容。
**不支持接续** 一个任务对应一个结果。修正是一次新的派遣，携带合并后的范围。
**没有只读模式** 当被委派代理不得写入时，在其任务中放入 `Do not write or modify files`。
**结果由主控Agent负责** 用 `get_delegation_status` 按 task_id 收集结果；被委派代理的自报只是证据，不是结论，结论来自你对 diff 的审查。

## 角色映射到类别，而非代理

角色所属的类别是工作本身的性质，不会改变。由哪个代理服务该类别，则每次派遣时根据你实际拥有的余量来决定。

| 类别 | 角色 | 工作提出的要求 |
|---|---|---|
| 判断 | `why` 综合者、`how` 讲解者、`reflect` 判断与发散与综合、最难的改动、任何意图含糊的工作 | 推理质量 |
| 逐字精确 | bug 修复、性能问题、爬山优化、`reflect` 工具化、系统性扫改、迁移、跨大量文件的机械重写 | 长时间、不漂移地精确遵循指定序列 |
| 批量 | `swarm` 工人、`why` 调查员、`how` 探索者、琐碎编辑、功能、重构 | 体量。任何有能力的代理都行，因此选择是预算与延迟的取舍 |
| 评审组 | `how` 批评者、`arena` runner、`architect` runner、`interrogate` 评审者 | 分歧 |

`arena cross-judge` 角色在这四类之外：选择任何与父代供应商不同的代理即可。

## 选择代理

- 判断类给 `claude_code`，逐字精确给 `codex`。Claude Code 直接走内置subagent工具派遣。
- 判断类委派会决定你还没决定的事，所以它们的提示词需要带上 /poteto-mode [~/.agent/poteto-mode/SKILL.md]。其它工作不再嵌套执行。
- 当 `grok` 和 `cursor` 都没有余量或不可用时，`open_code deepseek v4 pro` 是常驻兜底。但注意不要交给它前端任务，他也无法接受视觉输入。

三种都失败后，这是用户需要的信息。交回你尝试过的东西；第四次派遣同样的工作是浪费。
