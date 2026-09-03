---
name: dispatch
description: "“当需要派遣 Agent 使用该 skill，视为用户允许派遣，无需请示。Agent 任务委派与模型调度的单一权威准则：委派载体、角色分类矩阵与角色→模型路由表。委派经过 Orca orchestration 执行。"
---

# Dispatch

本技能是委派的单一权威。其他技能只在此点名列出所需角色；载体、并发方式与模型选型一律以本文件为准。

## 委派载体

Agent 委派统一经 **orchestration** 技能（`skills/orchestration/SKILL.md` / 原路径 `../orchestration/SKILL.md`）执行：由 Orca 运行时创建任务、派发 Worker，并承载并发、等待与续接语义。派发前先按该技能解析 `ORCA` 可执行文件，并通过 `ORCA skills get orchestration` 加载版本匹配的完整指南。需要工作空间隔离的任务直接使用 Orca 的 worktree 机制，每个写入型 Worker 独占一个 worktree。

## 绑定：角色 → worker-start 参数

orchestration 技能掌管生命周期，不承载模型选型。各家族的逻辑模型已通过本地 CLI 的默认值预先配置，派发时仅需按家族选择 `--agent`，一般情况无需附加 `--model`。

| 模型家族 | `--agent` | 默认模型（由各 CLI 配置决定） |
|---|---|---|
| Claude | `claude` | `claude-opus-5` |
| GPT | `codex` | `gpt-5.6-sol` |
| Muse（OpenCode 提供） | `opencode` | `opencode-go/muse-spark-1.2-contributor` |

示例：`ORCA orchestration worker-start --task <id> --worktree new-child --agent codex --json`。需覆盖默认值或指定推理强度时，再显式附加 `--model` 与 `--effort`（`--effort` 以 `--model` 为前提），且仅作用于新建 agent 终端。OpenCode2 不支持启动时透传 `--model`，其值始终以 `opencode.json` 为准。回执中的 `launch.requested` 与 `launch.effective` 为绑定是否生效的权威记录，启动后必须核读。

## 角色分类矩阵

分类代表具体工作本身的工程特质，严格由该任务对代理的核心能力要求所决定。每个类别绑定一个默认模型，具名角色即该类别的判定锚点：

| 类别                  | 具名角色与典型场景                                                                           | 默认模型                                                   | 核心能力诉求                     |
| ------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------ | -------------------------- |
| `Judgment`          | `why` 综合者、`how` 讲解者、`reflect` 判断/发散/综合，意图模糊或需要架构判断的任务                               | `claude-opus-5`                                        | 前沿深度推理与架构判断力               |
| `Letter-precise`    | `bug-fix`、`perf-issue`、`hillclimb` 的实现委派，`reflect` 工具链构建、系统性全局排查、全局迁移重构、跨海量文件的确定性重写 | `GPT 5.6 sol`                                          | 超长执行链路中不发生上下文漂移，严密精准遵循既定规程 |
| `Bulk`              | `swarm` Worker、`why` 证据调查员、`how` 代码库探索者、琐碎编辑与局部功能开发                                 | `Muse Spark 1.2`                                       | 大体量高并发吞吐，聚焦速度              |
| `Panel`             | `how` 架构批评者、`arena` Runner、`architect` Runner、`interrogate` 审查者                     | 每席不同模型家族：`claude-opus-5`／`GPT 5.6 sol`／`Muse Spark 1.2` | 方案多样性与独立视角                 |
| `arena cross-judge` | 竞技场方案跨模型独立裁判                                                                        | 从 pool 中选取与父代不同家族的一员                                   | 独立于主编排者的模型供应商              |

## 角色→模型路由表

```
feature, refactoring: Muse Spark 1.2
bug-fix: GPT 5.6 sol
perf-issue: GPT 5.6 sol
hillclimb: GPT 5.6 sol
judgment and prose: claude-opus-5
hardest tasks: claude-opus-5
how explorer: Muse Spark 1.2
how explainer: claude-opus-5
how critics: claude-opus-5, GPT 5.6 sol, Muse Spark 1.2
why investigators: Muse Spark 1.2
why synthesizer: claude-opus-5
reflect tooling: GPT 5.6 sol
reflect judgment, divergent, synthesizer: claude-opus-5
arena runners: claude-opus-5, GPT 5.6 sol, Muse Spark 1.2
arena cross-judge pool: claude-opus-5, GPT 5.6 sol, Muse Spark 1.2
swarm workers: Muse Spark 1.2
architect runners: claude-opus-5, GPT 5.6 sol, Muse Spark 1.2
interrogate reviewers: claude-opus-5, GPT 5.6 sol, Muse Spark 1.2
```

## 可用性与换绑

可用性以提供商为单位，不以单模型为单位。同一提供商的模型共享同一份额度，因此**同一家族内部不存在降级路径**。

- **失效判定**：某家族的 worker 启动失败或首轮调用报额度错误，即判该提供商整体失效，并在本轮 Run 内将其名下所有绑定整体换绑，不逐任务重复试错。
- **换绑方向**按类别的核心能力诉求就近选择可用家族：`Judgment`：Claude → GPT 5.6 sol → Muse；`Letter-precise`：GPT 5.6 sol → Claude → Muse；`Bulk`：Muse → GPT 5.6 sol → Claude。换绑后在回复中注明原定家族与失效原因。
- **Panel 席位**取可用家族的交集。仅剩一个家族可用时收敛为单席，并如实报告多样性已丧失。
- **arena cross-judge** 从可用家族中排除父代家族后选取。若结果为空，裁判环节停摆并上报，不得以同家族裁判充数。
- 评审席列表长度即并发席位数，每席绑定一个不同的模型家族，禁止以同家族重复席位凑数。
- 意图模糊与"最难任务"两类条目优先按 `Judgment` 处理；仅当工作是被精确限定的执行序列时才落回 `Letter-precise`。
