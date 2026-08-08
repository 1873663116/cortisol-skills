# Prompt 块

可复用的 Codex prompt XML 块。按任务类型组合使用。

## 任务定义

```xml
<task>
  [具体工作描述。包含：要做什么、相关文件路径；若为调试，含失败上下文。]
</task>
```

## 输出契约

```xml
<!-- 结构化（审查、分析） -->
<structured_output_contract>
  按严重程度返回发现列表（critical → high → medium → low）。
  每条发现：文件路径、行范围、可能出什么问题、具体修复建议。
  若无发现，明确说明。
</structured_output_contract>

<!-- 紧凑（状态、快速回答） -->
<compact_output_contract>
  最多一段。先给结论，再给支撑证据。
</compact_output_contract>
```

## 跟进策略

```xml
<default_follow_through_policy>
  若上下文足够，直接推进，不要追问。仅当缺失信息会实质改变方案时
  （例如未知目标环境、缺失 schema、成功标准含糊）再停下。
</default_follow_through_policy>
```

## 验证

```xml
<verification_loop>
  实现后：跑测试、检查类型/lint 错误、确认每条验收标准已满足。
  结束前修复一切失败。仍有错误时不要收尾。
</verification_loop>

<completeness_contract>
  在所有验收标准都有对应实现且验证通过之前，不要报告「完成」。
  部分实现应如实描述为部分实现。
</completeness_contract>
```

## Grounding

```xml
<grounding_rules>
  每条主张必须锚定在所提供的仓库上下文或工具输出上。
  引用具体文件与行号。不要臆造代码路径、文件或事件。
  若结论依赖推断，显式标注并给出置信度。
</grounding_rules>

<dig_deeper_nudge>
  定稿前检查二阶失败：空状态行为、重试路径、过期状态、回滚风险、
  竞态，以及设计权衡。
</dig_deeper_nudge>
```

## 安全

```xml
<action_safety>
  只修改任务直接需要的文件。不要在既定范围外重构、重命名、重排版或清理。
  若相关改进很明显，写在输出里但不要应用。
</action_safety>

<missing_context_gating>
  若所提供上下文不足以安全复现问题或实现功能，停下并精确列出缺失项。
  没有证据时不要猜测根因。
</missing_context_gating>
```

## 研究

```xml
<research_mode>
  下结论前先梳理代码库。把观察到的事实与推断分开列出。
  按置信度对建议排序。
</research_mode>

<citation_rules>
  每条建议必须链接到所提供上下文中的具体位置（文件、行、配置键）。
  允许外部引用，但必须标注为外部。
</citation_rules>
```
