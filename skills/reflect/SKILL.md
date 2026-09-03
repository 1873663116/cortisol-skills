---
name: reflect
description: "跨当前活跃会话记录并发派发三个独立视角的审查子 Agent，深度挖掘可沉淀的工程经验，并精准路由转化为对既有技能的确定性修改。当用户输入 reflect 或 /reflect 时使用。"
disable-model-invocation: true
---

# 会话反思与技能沉淀（Reflect）

深度挖掘当前会话中沉淀出的长效工程经验，并将其精准路由沉淀为对具体技能（Skill）的确定性更新与加固。

## 适用触发时机

- 用户显式输入“reflect”或“/reflect”。
- 刚干净利落地交付了一项复杂任务（包含 5 次以上工具交互），其解决路径与工程配方极具复用沉淀价值。
- Agent 在排查中曾踩入死胡同、最终找到了稳定可行的正确路径，且该解法具备通用性。
- 用户在任务执行中途对 Agent 的解题思路或工程方法进行了关键纠偏。
- 在任务中探索出了一套此前未被任何技能覆盖的非平凡工作流。

**跳过场景**：会话内容极其琐碎简单、偏离技术主题、或相关领域早已被既有技能完美覆盖且当前 Agent 已经完全严格遵守。偶发的一次性特例不属于应沉淀的长效经验。

## 执行流程

### 1. 定位当前会话的历史记录文件

主编排父代在并发派发前，率先在本地定位当前会话的物理记录文件。本地会话统一保存在 `~/.claude/projects/<slug>/<uuid>.jsonl`。严格限定在当前工作区对应的 `<slug>` 目录下检索，严禁使用通配符 `~/.claude/projects/*/` 以免跨工作区越界读取其他私有项目的历史记录。

```bash
ls -t ~/.claude/projects/<slug>/*.jsonl 2>/dev/null | head -10
```

`<slug>` 由工作区绝对路径编码生成（将 `/` 替换为 `-`；开头的根斜杠保留为前导 `-`）。当前工作区 `/Users/xiongzhipeng/.agents` 对应的标准目录为 `~/.claude/projects/-Users-xiongzhipeng--agents/`。

针对检索出的候选文件，从开头快速扫描至首个 `type` 为 `user` 的事件，核对 `message.content[0].text` 是否精准包含当前会话最初的用户 Prompt。若无法唯一定位文件路径，则提炼一份紧凑的会话摘要代入后续流程。

### 2. 并发派发三路独立审查者

查阅 **dispatch** 技能规范，并发派发三位审查者，分别承载互补的审视视角。审查者任务中必须显式注明 `Do not write or modify files`（只读审查，由主编排父代统一执行修改）：

| 审视视角 | 调度角色 | 基础 Prompt 模板 |
|---|---|---|
| **判断力（Judgment）** | `Judgment` 类别 | `references/judgment-reviewer.md` |
| **工具链（Tooling）** | `reflect tooling` 类别 | `references/tooling-reviewer.md` |
| **发散与盲区（Divergent）** | `Judgment` 类别 | `references/divergent-reviewer.md` |

将模板原样分发，并在对应占位符处填入会话记录文件的绝对路径或会话摘要。

### 3. 全局综合与置信度归类

查阅 **dispatch** 技能规范，选用其 `Judgment` 类别派发综合者 Agent。综合者任务中显式注明 `Do not write or modify files`。使用 `references/synthesizer.md` 模板，内联三位审查者的完整报告。综合者输出结构化的 **Accepted（采纳）/ Rejected（驳回）/ Backlog（待办）** 清单。

### 4. 机制化固化前置校验（Structural enforcement check）

对综合者产出的 Accepted 采纳清单执行严格把关：凡是能够通过 Linter 静态规则、自动化脚本、元数据标记或运行时强断言更加可靠强制约束的事项，一律将其从 Accepted 移至 Backlog 机制待办池中（遵循[将教训沉淀进系统结构中](../principle-encode-lessons-in-structure/SKILL.md)原则）。

### 5. 人工确认与精准应用

在正式改动任何技能文件前，将综合报告完整呈现给用户并**等待用户明确确认**。由用户最终勾选采纳子集并确认路由路径。技能规范会直接影响团队后续所有 Agent 的行为模式，严禁未经用户批准擅自自动应用。

针对经用户确认的 Accepted 采纳项，严格按其 Routing 字段执行落地：
- **微小改动**（单行补充、语句打磨、陈旧事实修正）：由父代直接原地编辑。
- **实质性扩充**（新增章节、新增模式表、超过 10 行的重大扩充）：严格应用 **writing-for-agents** 技能及其机制规范执行。
- **微调触发描述（`tune description: <skill path>`）**：该技能已存在但在本会话中未能精准触发，应用 **writing-for-agents** 的上下文指针规则优化其 description。
- **全新技能构建（`new skill via writing-for-agents: <kebab-name>`）**：严格遵循 **writing-for-agents** 规范构建标准技能结构。

若环境中配备了 `SKILL.md` 校验工具，在宣布完成前对所有触碰过的技能执行合规校验。

### 6. 最终精炼汇报

无前戏废话，直接输出清晰清单：
- **已应用的技能更新**：`<skill path>`，单行精炼说明改动点。
- **新建的技能**：`<skill path>`（罕见场景）。
- **沉淀的机制待办**：`<issue title>` (`<tags>`)。
- **已驳回的意见**：列出被否决的发现及其确凿技术理由。
