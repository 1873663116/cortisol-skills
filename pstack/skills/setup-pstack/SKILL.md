---
name: setup-pstack
description: "配置 pstack 各个角色所使用的模型。自动探测当前可用的模型，并生成覆盖技能默认配置的全局持久化规则。用于 /setup-pstack、“配置 pstack 模型”或调整 pstack 的模型选型。"
---

# 配置 pstack 模型（Setup pstack）

写入 `~/.cursor/rules/pstack-models.mdc` 规则文件（配置 `alwaysApply: true`），明确设定 pstack 各个工程角色绑定的模型。各技能会优先读取该规则；当某一角色未在该规则中声明时，自动平滑回退至该技能内置的默认模型。因此本配置仅为覆盖层，而非强制前置依赖。

## 执行步骤

### 1. 探测可用模型

枚举当前会话中可传递给 `Task` 工具的合法模型标识符（Model slugs），以此作为最权威的可用模型集合。若 Cursor 提供了列举用户已订阅/可用模型的 API 或 CLI，亦可结合使用以确保完备。若无法自动探测，提示用户输入其拥有的可用模型标识符。严禁写入未经确认可用的虚构模型标识符。别名 `inherit-parent` 与 `auto` 始终合法有效（即继承当前主会话模型）。

### 2. 加载当前配置状态

默认的角色到模型映射矩阵如下方第 5 步所示。若 `~/.cursor/rules/pstack-models.mdc` 已存在，读取并以其现有值作为当前配置基线；若不存在，则以默认矩阵作为初始基线。

### 3. 映射与确认

向用户逐一展示各个角色及其当前绑定的模型，对于未包含在已探测模型集合中的非法标识符明确标出。询问用户是直接原样采纳还是调整特定角色，提供探测到的合法模型列表以及 `inherit-parent` / `auto` 作为备选（两者均表示该角色直接继承主会话模型，使用 Auto 模式的用户以此保持 Auto 状态）。优先使用结构化单选/多选提问，避免自由文本。针对多模型评审席位角色（how critics、arena runners、architect runners、interrogate reviewers），其值为列表格式，每个列表项对应派发一个子 Agent（包含别名项），列表长度即决定了并发席位数量。`arena cross-judge pool` 亦为列表，Arena 会尽可能从中挑选一个与父代模型家族不同的模型担任裁判。`swarm workers` 为所有 Worker 的默认基准模型，除非竞速模式显式为各路分配了不同模型。

### 4. 校验有效性

写入规则中的每个真实模型标识符必须存在于已探测的合法集合中；`inherit-parent` 与 `auto` 始终通过校验。若用户选择的模型不可用，停步并重新确认。配置一个用户无权调用的模型会导致后续所有读取该规则的任务委派全部报错中断。

### 5. 写入规则文件

写入 `~/.cursor/rules/pstack-models.mdc`，配置 `alwaysApply: true`，每个角色单独一行，使用与 tomato-mode 一致的规范标签。完整覆写整个文件以保持幂等性。格式范例：

```markdown
---
description: pstack 各角色模型配置（覆盖技能默认配置）
alwaysApply: true
---
# pstack 模型配置矩阵。每行对应一个角色。删除某行则自动回退至技能内置默认值。
# 取值为 inherit-parent 或 auto 时，该角色直接使用主会话模型（派发 Task 时省略 model 字段）。评审席位列表中的别名项同样计入并发席位数。
feature, refactoring: cursor-grok-4.6-high
bug-fix: cursor-grok-4.6-high
perf-issue: cursor-grok-4.6-high
hillclimb: cursor-grok-4.6-high
judgment and prose: cursor-grok-4.6-high
hardest tasks: claude-fable-5-thinking-high
how explorer: gemini-3.7-flash-high
how explainer: cursor-grok-4.6-high
how critics: gemini-3.7-flash-high, gpt-5.6-luna-medium, cursor-grok-4.6-high
why investigators: gpt-5.6-luna-medium
why synthesizer: cursor-grok-4.6-high
reflect tooling: composer-2.5-fast
reflect judgment, divergent, synthesizer: cursor-grok-4.6-high
arena runners: gemini-3.7-flash-high, gpt-5.6-luna-medium, cursor-grok-4.6-high
arena cross-judge pool: claude-fable-5-thinking-high, cursor-grok-4.6-high
swarm workers: composer-2.5-fast
architect runners: claude-fable-5-thinking-high, claude-opus-5-thinking-high, cursor-grok-4.6-high
interrogate reviewers: claude-fable-5-thinking-high, claude-opus-5-thinking-high
```

### 6. 确认与生效

告知用户规则文件已成功写入，并将在新建的会话中正式生效。后续再次运行本技能可随时更新配置。

### 7. 主动提议生成验证技能（可选）

检查当前项目是否具备通过脚本驱动真实应用程序以证明改动有效的方法（即检查是否存在 `verify-*` 技能或现成的测试工装）。若均不存在，主动提议一次：“是否需要为当前项目生成专属的本地验证技能，以便 Agent 能够像真实用户一样驱动应用并证明改动有效？可通过 /create-verification-skill 生成。”若用户同意，唤起 `/create-verification-skill`；若拒绝，直接结束，不强推。
