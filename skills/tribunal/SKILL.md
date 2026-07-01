---
name: tribunal
description: 三段式对抗审计 plan、spec、PRD、设计方案、技能或流程文档。
disable-model-invocation: true
---

# tribunal

对 plan、spec、PRD、设计方案、技能或流程文档执行三段式对抗审计：审计方找问题，辩护方审视问题本身，裁决方在隔离上下文中裁定。

`tribunal` 是审计协议，不绑定单一运行时。可用实现限于两条路由：Claude Code Workflow 和 Codex Multi-Agent。

## 路由

先判断当前宿主能力。

- **Claude Code Workflow**：当前宿主提供 `Workflow()`、`agent()` 和 `parallel()` 原语时，读取 `references/orchestrate.js`，注入 `args` 后运行 `Workflow({ script, args })`。
- **Codex Multi-Agent**：当前宿主提供 Codex Multi-Agent 能力时，读取 `references/codex-multi-agent.md`，由主 Agent 派发 challenge、dedup、defense 和 judge subagent。
- **无可用路由**：当前宿主不具备以上能力时，停止并说明当前宿主无法运行 `tribunal`。

## 上下文

- **`target`**：被审对象全文，或被审对象文件的绝对路径。传路径时，执行方必须先读取文件全文，再审计文件内容。
- **`contextMap`**：可选的核实入口，包括相关文件、架构背景、skill 路径、MCP 工具和验证命令。
- **`lenses`**：审计立场数组。常用立场包括实现者、维护者、唱反调者和外部新人。每条意见必须带证据。
- **`defensePrompt`**：辩护提示词。辩护方判断问题是否误读、已覆盖、证据不足或严重度夸大；确实成立的问题要承认。
- **`judgePrompt`**：裁决提示词。裁决方逐条给出 `confirmed`、`rejected` 或 `uncertain`。
- **`seededDefects`**：可选种子缺陷，用于测试裁决方能否顶住似是而非的反驳。

## 输出

最终输出保持同一形状：

- **`confirmed`**：裁决方确认的问题，按严重度排序。每条应包含 `issueId`、`title`、`severity`、`reasoning` 和 `action`。
- **`rejected`**：裁决方驳回的问题，并说明驳回理由。
- **`uncertain`**：裁决方认为证据不足或需要用户拍板的问题。
- **`stats`**：原始问题数、去重后问题数、辩护后问题数和种子缺陷数。
- **`seededRecall`**：可选召回信号，只统计被裁为 `confirmed` 的种子缺陷。

## 边界

- 主 Agent 组织流程。裁判职责属于隔离的裁决方。
- 各阶段用 `issueId` 追踪问题。不要依赖标题匹配。
- judge 只接收被审对象、去重问题、辩护意见和必要上下文；不接收 challenge 原始全文或主 Agent 的额外判断。
- 子 Agent 不默认继承主 Agent 已读上下文。需要的文件路径、skill、MCP 工具和工作目录由主 Agent 显式传入。
- 如实呈现分歧。主 Agent 保留裁决方原意。
