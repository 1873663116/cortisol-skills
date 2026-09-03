# Code Archaeology

## 本数据源包含的资产

- Git 提交历史（Commit 信息、日期、作者、具体代码 Diff）
- PR 描述、代码评审讨论与审查意见流（通过 `gh` 获取）
- 代码内联注释、TODO、FIXME、废弃标记（Deprecation notes）
- 仓库内维护的 ADR 架构决策记录
- 测试用例（测试用例名称与断言往往直接固化了当初引发改动的极端边界条件）
- 在同一次提交中协同修改的关联文件（协同变更信号）
- 仓库内的 CHANGELOG 与 Release Notes
- 提交信息与 PR 正文中引用的工单/事故编号

这是最可信、与代码直接绑定且最完备的单一权威事实来源。所有合并入主干的内容均在此留痕。

## 常用检索手段

基于种子提交记录展开深入溯源：

```bash
# 跨重命名追踪文件的完整演进历史
git log --follow --oneline -- <file>

# Pickaxe 精准检索：找出添加或删除该确切代码文本的提交
git log -S '<exact_string_from_code>' -- <file>

# 正则模式检索：
git log -G '<regex>' -- <file>

# 行级追溯：每一行的作者与提交时间
git blame -L <start>,<end> <file>

# 查看特定提交的完整 Diff
git show <hash>

# 查看影响该文件的提交区间 Diff
git log <old>..<new> -p -- <file>
```

针对关键提交拉取对应的 GitHub PR 上下文：

```bash
# 从合并提交中提取关联的 PR 编号
git log -1 --format=%B <hash>

# 拉取 PR 完整详情：标题、正文、评审讨论、关联 Issue、文件列表等
gh pr view <number> --json title,body,author,createdAt,mergedAt,labels,closingIssuesReferences,comments,reviews,files
```

探查非内联的代码库文档与注释：

```bash
# 检索架构决策记录
rg -l -i 'architecture.decision' --glob '*.md'

# 检索目标代码周边的临时标记
rg -n -C2 '(TODO|FIXME|HACK|XXX|NOTE)' <target_file>

# 检索关联的测试用例（用例名称往往承载了为何如此设计的动因）
rg -l '<symbol>' --glob '*test*'
```

## 典型的高价值证据特征

- PR 描述中清晰阐述了所解决的根本痛点，而非只陈述改动本身（如“此改动修复了导致 X 故障的分页缺陷”）。
- 评审流程中就多种备选方案展开深度辩论的长篇讨论流。
- 目标代码行旁边解释非显而易见外部约束的内联注释。
- 名为 `test_handles_edge_case_when_X` 的针对性测试用例。
- 引用了特定线上事故编号或工单 ID 的提交说明。
- CHANGELOG 中面向用户视角的动因摘要。

## 常见陷阱与注意事项

- **Squash 合并导致分支细节丢失**：若项目采用 Squash 策略，分支内的细粒度提交信息会被抹平，此时应重点转向 PR 正文与评审讨论流。
- **误导性的敷衍提交说明**：“小重构”有时掩盖了重大的行为变更，务必以实际代码 Diff 为准，而非轻信提交说明。
- **盲目复制粘贴的既有模式**：作者可能只是照搬了旧代码的写法而并不理解其动因。检查该模式最早由哪次提交引入，并深挖那次最初的提交。
- **自动化机器人提交**：Dependabot、Renovate 或自动同步工具的提交通常不承载业务设计动机，分析意图时可直接略过。
- **将代码自身作为意图的证据**：代码形态本身不是其为何存在的证据。不要将“函数命名为 X”作为证明设计意图的依据。

## 输出要求

返回与核心问题相关的所有提交、PR 与注释，包含：
- 精确的引用文本（原文摘录）
- Commit Hash / PR 编号 / 文件行号
- 作者与提交日期
- 标明属于直接证据还是间接旁证
