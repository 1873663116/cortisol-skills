# reportHTML References

这些文件是 `reportHTML` 的路由参考。它们帮助未来 agent 判断应该借用哪种方法论来生成 HTML 报告。

## 规则

- `external/` 中的文件来自 `npx skills use ...`，仅作为参考材料保存。它们没有被安装成独立用户级 skill。
- `local/` 中的文件来自本机已经安装的用户级 skill。它们是离线参考副本，不是权威源。权威源仍在对应的 `~/.agents/skills/<skill>/SKILL.md`。
- `reportHTML` 的主逻辑必须保持薄。不要把这些参考文件的大段内容复制回 `SKILL.md`。

## 外部参考

| 文件 | 用途 |
|---|---|
| `external/anthropics-frontend-design.md` | 视觉方向、版式、排版、避免模板感 |
| `external/vercel-web-design-guidelines.md` | Web UI 审查、可访问性和界面质量检查 |
| `external/anthropics-documentation.md` | 技术文档结构、读者路径、文档类型 |
| `external/anthropics-synthesize-research.md` | 从大量材料提炼主题、证据、建议 |
| `external/inference-data-visualization.md` | 图表选择、指标卡、数据可视化规则 |
| `external/html-report-builder.md` | 咨询式长报告结构、PDF 友好版式 |
| `external/anthropics-canvas-design.md` | 高度视觉化封面或静态视觉物 |

## 本地参考

| 文件 | 对应本地 skill |
|---|---|
| `local/theme-factory.md` | `~/.agents/skills/theme-factory/SKILL.md` |
| `local/web-artifacts-builder.md` | `~/.agents/skills/web-artifacts-builder/SKILL.md` |
| `local/playground.md` | `~/.agents/skills/playground/SKILL.md` |
| `local/playwright.md` | `~/.agents/skills/playwright/SKILL.md` |
