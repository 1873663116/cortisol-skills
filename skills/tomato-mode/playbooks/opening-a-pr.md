### 开 PR（Opening a PR）

在所有其他开发类 Playbook 的收尾阶段被调用。

**Git Worktree 隔离机制。** 从 `main` 主分支拉出独立的 Git Worktree 进行开发。为每个并发写入者分配独立的 worktree，确保各自拥有独立的工作目录与分支；严禁将多个并发写入者指向同一目录。各分支产物不会自动合并，在合入前必须逐一严格审查。当工作分支受到污染、混入了无关改动时，将有效补丁导出，重新创建干净的 Worktree 并应用补丁。当 Worktree 冲突严重难以理清时，直接从 `main` 重新创建 Worktree，以最小必要改动重新实现。

**Commit 规范。** 开发过程中鼓励多提细粒度提交；在正式发起 PR 前，通过 rebase 整理为一系列清晰小巧且逻辑有序的 commit 链。每个 commit 都应具备独立合入主线的能力，其提交顺序本身应构成完整的推导演进线索。若追修完全属于前一个 commit，使用 amend 合并；若属于新的独立逻辑切片，则新开 commit。

**PR 提交与堆叠。** 提交 commit 前必须对 diff 应用 **unslop** 技能进行审查，发起代码评审前运行 `/no-comments`。PR 说明正文与 commit message 同样必须经过 **unslop** 去 AI 腔清洗。PR 规模必须保持精简，5 个聚焦的小 PR 远胜过 1 个臃肿的庞大 PR；后续改动基于此向上堆叠（stacked PR），仅有真正正交独立的工作才直接从 `main` 切新分支。堆叠 PR 使用团队现有的堆叠工具（如 Graphite），核心原则是将大任务切分为小巧有序的增量片段，并确保评审者能够清晰纵览整条 stack。在引用 PR 状态前先执行 `gh pr view <number>` 获取最新事实。在对 stack 开展实质性改动前，先基于 `main` 执行 rebase。小型精简 PR 严禁套用空洞的模板套话（如毫无增量信息的 `## Summary` / `## Test plan` 标题），commit 正文亦不得机械重复首行标题。完成 PR 提交后，启动 Cursor 内置的 **babysit** 技能；若自动化反馈偏离原始工程意图，必须明确据理驳回。

负责开 PR 的子 Agent 依次执行 `interrogate` 审查、应用 **unslop**、运行 `/no-comments`、返回生成的 PR URL 后即刻结束回合，不执行后续 Babysit 看护逻辑，控制权交回父 Agent。
