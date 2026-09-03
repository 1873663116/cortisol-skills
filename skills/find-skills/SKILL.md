---
name: find-skills
description: "帮助用户发现并安装 Agent Skills。当用户提出“如何做 X”、“帮我找一个关于 X 的技能”、“是否有技能可以实现……”或希望扩展 Agent 能力时使用。适用于探索可通过安装既有技能来解决任务的场景。"
disable-model-invocation: true
---

# Find Skills

本技能用于在开放的 Agent 技能生态中检索、评估并安装符合需求的技能包。

## 技能生态与 CLI 概述

Skills CLI（`npx skills`）是开源 Agent skill 生态的标准包管理器。

**核心命令：**
- `npx skills find [query] [--owner <owner>]`：通过关键词交互式检索技能，支持限定 GitHub 组织/用户。
- `npx skills add <package>`：从 GitHub 或指定源安装技能包。
- `npx skills check`：检查已安装技能的最新版本更新。
- `npx skills update`：一键升级全部已安装的技能。

**技能生态官方主页：** https://skills.sh/

## 推荐与安装执行流程

### 第 1 步：洞察真实需求

当用户提出诉求时，迅速提炼：
1. **技术领域**（例如 React、自动化测试、UI 设计、发布部署）。
2. **具体任务**（例如编写用例、实现交互动效、审查 PR）。
3. **通用性评估**（该任务是否足够通用，大概率已有现成社区技能）。

### 第 2 步：优先检索官方榜单

在执行本地 CLI 检索之前，先查阅 [skills.sh 排行榜](https://skills.sh/)，了解该领域是否已有经过社区广泛实战检验的知名标杆技能。榜单按总安装量排序，能迅速筛选出高可靠性方案。

例如前端工程领域的标杆技能包括：
- `vercel-labs/agent-skills`：涵盖 React、Next.js 与 Web 设计最佳实践（10 万+ 安装量）。
- `anthropics/skills`：涵盖前端交互设计、文档处理等（10 万+ 安装量）。

### 第 3 步：精准检索技能

若排行榜未直接覆盖特定需求，运行检索命令：

```bash
npx skills find [query] [--owner <owner>]
```

检索示例：
- 用户问“如何优化 React 应用性能？” → `npx skills find react performance`
- 用户问“能否帮我审查 PR？” → `npx skills find pr review`
- 用户问“需要自动生成发布变更日志” → `npx skills find changelog`

### 第 4 步：质量严审后再行推荐

**严禁仅凭搜索结果就盲目向用户推荐技能**。必须严格核验：
1. **Install count**：优先推荐安装量 1K+ 的成熟技能，对于低于 100 次安装的新技能保持审慎。
2. **Source reputation**：官方组织（`vercel-labs`、`anthropics`、`microsoft` 等）发布的技能通常具备更高的质量与维护保障。
3. **GitHub Star**：查阅源仓库 Star 规模，对于 Star 低于 100 的个人仓库需审慎评估。

### 第 5 步：协助执行安装

若用户确认安装，可直接协助执行命令：

```bash
npx skills add <owner/repo@skill> -g -y
```

其中 `-g` 表示全局用户级安装，`-y` 自动跳过交互式确认。

## 常见技能分类与检索词

| 分类 | 推荐检索关键词 |
|---|---|
| Web 前端开发 | react, nextjs, typescript, css, tailwind |
| 自动化测试 | testing, jest, playwright, e2e |
| 运维与部署 | deploy, docker, kubernetes, ci-cd |
| 文档与规范 | docs, readme, changelog, api-docs |
| 代码质量审计 | review, lint, refactor, best-practices |
| UI/UX 设计 | ui, ux, design-system, accessibility |
| 研发效能与工作流 | workflow, automation, git |

## 未检索到匹配技能时的应对

若当前生态中确实缺乏对口技能：

1. 如实告知用户当前未找到现成的专门技能。
2. 主动提议直接基于自身的大模型通用工程能力协助解决当前任务。
3. 若该任务是用户日常高频操作，建议其通过 `npx skills init` 初始化定制专属于自己的技能包。
