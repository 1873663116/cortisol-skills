---
name: reportHTML
description: Explicit-only router for creating visual HTML reports from engineering evidence, diffs, docs, audits, plans, or decisions. Use only when the user explicitly invokes reportHTML or $reportHTML.
disable-model-invocation: true
---

# reportHTML

`reportHTML` 是一个显式触发的薄路由 skill。它把工程材料转成可视化 HTML 报告，但它本身不试图成为大型报告生成器。

只在用户明确写出 `reportHTML`、`$reportHTML`，或明确要求“用 reportHTML 做报告”时使用。不要因为用户只是要求“写报告”“做网页”“总结 diff”而自动触发。

## 目标

把复杂工程材料变成一个可验收的单文件 HTML 报告。常见输入包括：

- git diff、PR、commit、review 结果；
- ADR、contract、spec、测试策略、架构说明；
- 调研结论、候选方案、验收结果；
- 文档变更、概念映射、状态机、测试矩阵；

报告必须帮助读者更快判断：

- 本轮变化是什么；
- 哪些文件、模块或概念受影响；
- before / after 有什么语义差异；
- 哪些事实已经验证，哪些仍是假设；

## 工作原则

1. **证据先行**。先读真实文件、真实 diff、真实命令输出或用户提供的材料。不要凭记忆编造文件、变更、数字或结论。
2. **先综合，再视觉化**。先提炼读者需要理解的结构，再决定用矩阵、流程图、状态机、时间线、卡片、before / after、diff block 还是指标卡表达。
3. **视觉承载结构**。颜色、布局和图形必须表达含义。不要只做装饰。
4. **报告不是权威源**。HTML 报告是阅读辅助。报告中必须标明权威来源仍然是原始 Markdown、代码、ADR、contract、issue、PR 或用户提供材料。
5. **默认单文件**。默认输出一个静态 HTML 文件，内联 CSS 和少量 JS。只有需要复杂交互、路由、状态管理或 shadcn/ui 时，才转向复杂 artifact。
6. **验收闭环**。报告生成后必须用浏览器或截图方式检查首屏、关键图表、diff 区域、移动端或窄屏风险。至少检查横向溢出和关键可视化是否渲染。

## 路由表

根据任务需要，发挥判断和决策能力，使用以下参考能力

| 需求 | 默认路线 | 参考文件 |
|---|---|---|
| 报告信息架构、技术叙事、读者路径 | 借用 technical documentation 方法 | `references/external/anthropics-documentation.md` |
| 从大量材料中提炼主题、证据、建议 | 借用 research synthesis 方法 | `references/external/anthropics-synthesize-research.md` |
| 视觉方向、版式、排版、避免模板感 | 借用 frontend design 方法 | `references/external/anthropics-frontend-design.md` |
| Web UI 质量检查、可访问性、界面规则 | 借用 web design guidelines 方法 | `references/external/vercel-web-design-guidelines.md` |
| 图表类型、数据可视化、指标卡 | 借用 data visualization 方法 | `references/external/inference-data-visualization.md` |
| 咨询式长报告版式、PDF 友好结构 | 借用 html report builder 方法 | `references/external/html-report-builder.md` |
| 高度视觉化封面或静态视觉物 | 借用 canvas design 方法 | `references/external/anthropics-canvas-design.md` |
| 主题与色彩套件 | 使用本地 `theme-factory` | `references/local/theme-factory.md` |
| 复杂交互式报告 | 使用本地 `web-artifacts-builder` | `references/local/web-artifacts-builder.md` |
| 参数探索、交互 playground | 使用本地 `playground` | `references/local/playground.md` |
| 浏览器验收、截图、溢出检查 | 使用本地 `playwright` 或可用浏览器工具 | `references/local/playwright.md` |

## 默认报告结构

根据材料选择删减，但默认从这些区块开始：

1. **首屏结论**：一句话说明报告要解决的问题；配 3 到 5 个指标卡。
2. **证据来源**：列出读取的文件、diff、命令、用户材料和验证边界。
3. **影响地图**：展示新增、修改、删除、归一化、风险或未验证内容。
4. **文件 / 模块影响矩阵**：横向是概念或能力域，纵向是文件、模块或决策。
5. **语义 Diff**：用 before / after 卡片说明概念变化，而不只是展示文字差异。
6. **关键 Diff 片段**：用红绿块展示会影响实现判断的具体变更。
7. **流程图 / 状态机 / 依赖图**：用 Mermaid 或手写 HTML/CSS 表达关系。
8. **风险与验证状态**：区分已验证、理论验证、未验证、待真机、待用户确认。
9. **下一步入口**：列出最自然的后续工程任务、文档任务或验收任务。

## 可视化组件

优先使用这些组件，而不是长段落：

- metric cards；
- file impact cards；
- before / after panels；
- red / green diff blocks；
- impact matrix；
- testing funnel；
- route map；
- timeline；
- swimlane；
- Mermaid flowchart；
- compact evidence table；
- risk badges；
- sticky navigation；
- color legend。

颜色必须绑定含义。推荐默认语义：

- 绿色：新增、通过、可进入下一步；
- 蓝色：现有内容更新、信息入口；
- 紫色：术语统一、抽象关系；
- 黄色：风险、未验证、待确认；
- 红色：删除、旧口径、阻塞或错误；
- 灰色：背景事实、上下文、未命中。

## 设计约束

- 页面第一屏必须说明“为什么读这个报告”。
- 读者必须能在一分钟内知道主要变化。
- 复杂图必须搭配解释，不让读者猜图意。
- 不要让 Mermaid 成为唯一表达。必要时用 HTML 卡片和矩阵补足。
- 文本不要过短，造成内容空洞；但也不能过长，造成字符堆砌。
- 页面不使用装饰性渐变球、空泛 hero、营销式文案或无法解释的插画。
- 如果报告面向工程变更，视觉风格应该偏工作台、分析台、审阅台，而不是宣传页。

## 文件落点

如果用户没有指定路径：

- 项目内报告写到该项目合适的 `docs/visual/`、`reports/`、`output/` 或临时目录；
- 若报告只是一次性审阅，不应污染仓库，写到 `$TMPDIR/reportHTML-<timestamp>.html`；
- 若报告用于随文档一起评审，可以写入项目文档目录，但必须说明它不是权威契约。

## 验收清单

完成前至少检查：

- HTML 可以打开；
- 首屏有明确结论；
- 目录或导航可用；
- 颜色图例存在，且颜色含义一致；
- 关键 diff 片段可见；
- 视觉效果正常渲染；
- 桌面宽度没有横向溢出；
- 文本无重叠；
- 报告写明权威来源仍是原始文件。

如果环境允许，使用浏览器自动化截图验证。若无法运行浏览器，说明未验证项。

## 交付

最终回复中只说最重要的结果：

- HTML 报告路径；
- 使用了哪些输入证据；
- 做过哪些验收；
- 有哪些未完成或未验证项。

不要把整份报告内容复制到聊天里。
