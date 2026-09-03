### Worktree 与模拟器清理（Worktree and simulator cleanup）

**对磁盘空间回收与数据安全闸门负全责。** 清理已合并或已废弃的 Git Worktree 以及过期的 iOS 模拟器以回收磁盘空间。删除操作具有物理不可逆性，因此每一步必须严密防范两类重大风险：误删正在使用中的工作空间，以及误删仍包含未提交有效改动的工作空间。

1. **状态快照与自动化审计。** 先记录执行前的 `df -h /`，随后运行 `scripts/worktree-audit.sh`（遵循**打造杠杆工具**原则）。该脚本严格从 `git worktree list` 读取实际物理路径，严禁手动输入（因为手动输入诸如 `myrepo-worktrees/x` 极易漏掉位于 `.claude/worktrees/x` 的隐藏 Worktree，遵循**将教训沉淀进系统结构中**原则）。脚本会根据磁盘占用大小、创建时长、分支合并状态、未提交改动情况、PR 状态以及最近触碰该 Worktree 的会话记录对各 Worktree 进行分类，并给出建议归类桶。扫描历史会话耗时较长，放入后台执行。
2. **审计归类仅供参考，绝非删除授权。** 处于置顶（Pinned）状态与活跃进行中的会话才是真正的权威凭据（遵循**用实际运行证明有效**原则）。从用户或界面侧边栏获取当前活跃会话集合，逐一交叉核对每个候选对象。历史上自动化工具曾错误将用户置顶的 Worktree 标记为 `safe`（安全可删），因此以人工置顶/活跃会话集合为最高准绳。
3. **删除前必须深度核验实际占用状态。** 针对审计输出中标记为 `verify-recent-chat` 的所有行以及任何存疑项目，扇出子 Agent 检索分析会话历史，核实该会话是否已被置顶或仍在活跃运行，以及它触碰了哪些 Worktree（遵循**守卫上下文窗口**原则，会话日志属于 Bulk 大体积数据）。置顶会话往往会通过后台子 Agent 向同级 Worktree 派生 Arena 方案比选或复现环境，此类 Worktree 即便名字从未出现在侧边栏中，亦属于高频使用中的受保护对象。
4. **遇不可逆数据丢失风险立即暂停。** 标记为 `wip:N` 表示包含 N 处已被 Git 跟踪的未提交改动。必须先将具体 diff 完整呈现给用户并由用户明确做出决策，因为删除干净的 Worktree 仍可从对应分支恢复，而未提交的代码一旦删除将永久丢失。标记为 `scratch:N` 表示未被 Git 跟踪的临时生成文件，可安全清理，但须在报告中列出具体文件名。遵循 Autonomy 准则：干净、已合并且未在使用中的 Worktree 直接推进清理；存在 `wip` 未提交改动或处于使用中的 Worktree 必须暂停请示。
5. **执行清理并完成物理剪除。** 针对确认无误的路径，执行 `git worktree remove --force <path>`；若目录由于存在受忽略的构建产物残留未能自动移除，执行 `rm -rf` 强制清除，随后运行 `git worktree prune`。分支引用仍保留在本地，因此不会丢失任何历史 commit。执行 `df -h /` 确认释放效果并重新列出当前 Worktree 列表。
6. **清理 iOS 模拟器与其他系统缓存。** 模拟器通常是收益极其显著的空间回收大户：执行 `xcrun simctl --set testing delete all`（清理 XCTestDevices 测试克隆体）、`xcrun simctl delete unavailable`（删除不可用模拟器），以及执行 `xcrun simctl runtime list` 随后对陈旧运行时执行 `runtime delete <id>`。若需要进一步释放空间，可清理：Xcode `DerivedData` 与 `iOS DeviceSupport`；`~/Library/Application Support/Cursor`（如 `state.vscdb.backup`，以及在以打开过的工作区命名的 `snapshots/roots/<root>` 发生异常膨胀时按需清理）；包管理器本地缓存（pnpm、uv、brew、yarn 等，仅清理用户未明确要求保留的缓存）。

本 Playbook 是唯一一个在缺乏代码评审机制兜底的情况下物理删除用户本地状态的流程，因此上述安全闸门本身即充当了最严格的审查把关。

**最终回复要求：** 清理前后的 `df -h /` 磁盘对比与实际释放的空间量、已成功清理的 Worktree 路径清单，以及每个被保留暂缓清理的 Worktree 的单行保留理由（被具体哪个会话占用，或包含具体的未提交改动）。
