# Assessment

## 派生考核

在准备实现、阶段结束或 Thread 结束时，或用户主动要求考核时，若 Ledger 中存在值得检验的材料，或 Wiki 中存在与当前目标相关的 Cognitive Debt，使用 `fork_thread` 从当前 Thread 分叉一个认知考核 Thread，让项目主 Thread 继续执行。

派生时标记当前 Ledger 为认知考核 Thread 独占的 Checkpoint；项目主 Thread 停止写入它，之后只有再次进入认知协作状态时才惰性创建新 Ledger。Checkpoint 只保存本次考核所需的运行状态和相关 Cognitive Debt 链接，不复制债务正文。

考核 Thread 不允许创建 Ledger。

考核在不读取 Model 的情况下，请用户从项目情境中完整重建关键概念、因果、适用边界和判断依据；然后才按完成可靠比较所需的范围读取现有 Model。先盲测避免现有表述暗示答案，后读 Model 用于比较、去重和结构校准。

用户的参与有限且可撤回。考核结果仍只有已理解、尚未理解和未回答；未回答不产生新的 Cognitive Debt，也不清除已有 Cognitive Debt。追问服务于获得可靠判断，并随用户退出而收束。

## 比较与收束

考核结束后，认知考核 Thread 只依据用户实际回答和已有明确证据处理：

1. **已理解**：把用户完整重建的理解按照 Wiki 规则形成或实质更新 Model，并在写入核对成功后清除对应 Cognitive Debt。
2. **尚未理解**：保留或更新对应 Cognitive Debt，依据回答调整后续学习方向。即使本轮随后完成教学，债仍等待未来独立考核；没有相关 Model 时也继续独立存在。
3. **未回答**：不新增债；已有债继续保留，未形成债的待检验信号按用户意愿保留或丢弃。

获得所需确认后，认知考核 Thread 按照 Wiki 的 `AGENTS.md` 修改 Wiki 并核对结果，不再创建或委派另一个 Thread。没有相关 Model 的 Cognitive Debt 继续作为独立页面存在；它可以在未来推动新 Model 形成或关联到已有 Model，但不能仅凭主题相似性自动创建 Model。

所有已有证据的内容都已归类，允许的 Wiki 修改也已完成时，删除 Checkpoint。仍在等待用户确认或 Wiki 修改失败时保留 Checkpoint，并明确说明尚未完成的事项；用户拒绝保存或要求删除时，丢弃相应内容并清理。
