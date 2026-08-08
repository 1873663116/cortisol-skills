---
name: agent-codex
description: 当用户提到 Codex、希望把编程任务委派出去、说「交给 Codex」「codex solve」「问 Codex」，或需要第二轮实现、排错、code review、架构分析、以及交给 OpenAI Codex 的独立编码子任务时使用。即使用户未显式说「Codex」，只要任务实质、自包含、且适合由独立 Agent 执行，也应触发本 skill。
---

# Agent Codex

将当前工作目录中的编码任务委派给 OpenAI Codex。

## 1. 选择角色

按任务选择最合适的角色：

| 角色 | sandbox | approval-policy | 适用场景 |
|------|---------|-----------------|----------|
| **explorer** | `read-only` | `untrusted` | 分析代码、审架构、解释流程、找 bug —— 不改文件 |
| **worker** | `workspace-write` | `on-failure` | 实现功能、修 bug、重构 —— 多数任务的默认 |
| **monitor** | `read-only` | `untrusted` | 轮询 CI、盯构建输出、等待部署 |

不明确时默认 **worker**。

## 2. 拆分任务

调用 Codex 之前，分析任务并决定如何拆分。拆分决策在本 skill 内完成 —— 调用方不必预先拆好。

**分析步骤：**
1. 识别请求中的独立子任务
2. 对每一对子任务判断：B 是否必须等 A 的产出才能开始？
3. 判断是否有两个子任务会写入同一批文件？

**决策规则：**
- 子任务彼此独立（无产出依赖、无写文件重叠）→ 并行
- 子任务彼此依赖产出 → 串行，各自一次独立的 Codex 调用
- 单一连贯任务 → 单次 Codex 调用

子任务上限 2–4 个。超过 4 个通常收益不大，且合并冲突风险升高。

**调用 Codex 前先展示拆分计划。** 每个子任务一行：名称、角色、为何独立或串行。便于调用方在开工前纠正误解。

示例输出：
```
拆分计划：
1. 审查认证架构 [explorer] — 只读，无依赖
2. 修复登录 bug [worker] — 文件独立（auth/login.ts）
→ 并行执行
```

若任务明显单一且简单，可跳过计划，直接执行。

## 3. 收集项目上下文

```bash
bash <skill-dir>/scripts/prepare-context.sh
```

将输出写入发给 Codex 的 prompt。Codex 不共享当前会话上下文 —— prompt 必须自洽。

## 4. 准备 Prompt

使用 XML 块结构，便于 Codex 稳定解析意图：

```
<task>
  需要完成什么（把用户请求改写清楚）。
  写上相关文件路径。
</task>

<project_context>
  prepare-context.sh 的输出（技术栈、约定、git 状态）。
</project_context>

<constraints>
  超出项目约定之外的规则（范围限制、避免改动的文件等）。
</constraints>

<verification_loop>
  实现后验证：跑测试、查错误、确认每条验收标准已满足。
  若失败，先修好再结束。
</verification_loop>
```

审查类任务：用 `<grounding_rules>` 替换 `<verification_loop>`：每条发现必须引用具体文件与行号，禁止臆造问题。

CLI 参考见 `references/codex-cli.md`。

## 5. 调用 Codex

### 若 MCP 工具 `codex`（或 `mcp__codex__codex`）可用：

```
codex(
  prompt: <准备好的 prompt>,
  cwd: <工作目录>,
  approval-policy: <来自角色>,
  sandbox: <来自角色>,
  developer-instructions: <项目约定>  // 可选
)
```

保存返回的 `threadId`，供后续续聊。

### 否则（CLI）：

```bash
# worker
codex exec -s workspace-write -a on-failure "<prompt>"

# explorer / monitor
codex exec -s read-only -a untrusted "<prompt>"
```

多 Agent 任务：并行调用，每个子任务各自角色与 prompt。

## 6. 后续跟进

### 若 MCP 可用：

```
codex-reply(threadId: <id>, prompt: "<后续指令>")
```

### 否则：

```bash
codex resume <session-id> "<后续指令>"
# 或续跑最近一次会话：
codex resume --last "<后续指令>"
```

## 7. 呈现结果

Codex 完成后：

- 列出改动的文件，以及修复/实现了什么
- **原样保留** Codex 的发现与表述 —— 不要改写，也不要悄悄「纠正」
- 审查类输出：先按严重程度呈现发现，然后**停住**。不要自行修、不要暗示马上要改。明确问用户要处理哪些问题（如果有），再动任何文件
- 失败或不完整：报告失败，询问是用 refined prompt 重试，还是发 follow-up

多 Agent 任务：合并各子任务结果，标出文件冲突，解决后再汇报。

## 8. 经 Subagent 救援

当主 Agent 卡住、需要更深诊断，或希望把实质任务交给 Codex 且不亲自编排时 —— 直接使用 `codex-rescue` subagent：

```
Agent(subagent_type: "codex:codex-rescue", prompt: "<任务描述>")
```

该 subagent 是薄转发层：一次 Codex 调用，输出原样返回。内部会用 `gpt-5-4-prompting` skill 收紧 prompt，再调用 Codex。

续跑行为：在 prompt 中带 `--resume` 以续最近 Codex 线程；带 `--fresh` 强制新开会话。
