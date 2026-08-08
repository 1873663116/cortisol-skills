---
name: gpt-5-4-prompting
description: 在 codex-rescue 内，为编码、审查、诊断与研究任务收紧 Codex prompt 的内部指引
user-invocable: false
---

# GPT-5.4 Prompting

当 `codex-rescue` 需要在唯一一次 CLI 调用前，把用户请求收紧为更好的 Codex prompt 时使用本 skill。这是 subagent 侧唯一允许的额外工作。

## 核心规则

把 Codex 当作业器（operator）来提示，而不是协作者：
- 写清任务、输出契约，以及少数真正重要的约束
- 每次 Codex 运行一个清晰任务 —— 无关请求拆成多次运行
- 告诉 Codex「完成」长什么样；不要假设它会自行推断终态
- 用 XML 标签保持稳定内部结构
- 宁可更紧的 prompt 契约，也不要更长的自然语言解释

## 默认 prompt 配方

```
<task>
  具体工作，以及相关仓库或失败上下文。
</task>

<structured_output_contract>
  响应的确切形状、顺序与简洁要求。
</structured_output_contract>

<default_follow_through_policy>
  默认应继续推进什么，而不是就例行问题来回询问。
</default_follow_through_policy>
```

按任务类型追加块：

| 任务类型 | 追加这些块 |
|-----------|-----------------|
| 编码 / 调试 | `<completeness_contract>`、`<verification_loop>`、`<missing_context_gating>` |
| 审查 / 对抗式审查 | `<grounding_rules>`、`<structured_output_contract>`、`<dig_deeper_nudge>` |
| 研究 / 建议 | `<research_mode>`、`<citation_rules>` |
| 可写任务 | `<action_safety>` —— 保持范围收窄，避免无关重构 |

## 关键块

**`<verification_loop>`** — 用于实现与调试：
```
实现后验证：跑测试、检查类型错误、确认每条标准已满足。
结束前先修复失败。仍有错误时不要收尾。
```

**`<grounding_rules>`** — 用于审查与研究：
```
每条发现必须引用所提供上下文中的具体文件与行号。
不要臆造仓库中不存在的文件、代码路径或事件。
若结论是推断，须明确说明。
```

**`<action_safety>`** — 用于可写任务：
```
只修改任务直接需要的文件。
不要在任务范围外重构、重命名或清理代码。
```

**`<missing_context_gating>`** — 用于调试：
```
若无法用已提供上下文复现问题，如实说明并列出缺失信息。
没有证据时不要猜测根因。
```

## Prompt 组装检查清单

1. 在 `<task>` 中定义确切任务与范围
2. 选择仍可用、但尽量小的输出契约
3. 决定 Codex 默认应继续推进，还是缺信息时停下
4. 仅在任务需要处加入验证、 grounding 或安全块
5. 发送前删掉冗余指令

## 参考

- `references/prompt-blocks.md` —— 可复用块模板
- `references/codex-prompt-recipes.md` —— 端到端 prompt 示例（若仓库中存在）
- `references/codex-prompt-antipatterns.md` —— 常见失败模式（若仓库中存在）
