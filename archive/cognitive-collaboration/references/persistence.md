# Persistence

## Cognitive Ledger

Cognitive Ledger 是当前 Thread 独占的运行状态，位于个人 Wiki 的 `.runtime/cognitive-ledger/`，不进入 Git 或 Obsidian 认知图谱。进入认知协作状态后按需创建 Ledger，保留用户表达的新理论理解、待检验信号、知识检验过程及其结果、项目证据指针和候选后续动作。

Ledger 直接区分待检验信号、未回答和已经确认的 Cognitive Debt。待检验信号与未回答只保留在 Ledger。Ledger 在过于巨大、繁杂时进行合并性压缩重构。

## Cognitive Debt

知识检验确认“尚未理解”后，立即按照 Wiki 规则在 `cognitive-debts/` 创建或更新对应 Cognitive Debt 页面，并在 Ledger 中只保留页面链接与当前 Thread 仍需执行的动作。Cognitive Debt 不写入项目目录，也不以 Ledger 或 Checkpoint 作为唯一持久化位置。

没有相关 Model 不阻止 Cognitive Debt 落盘。未归属 Cognitive Debt 直接位于 `cognitive-debts/`，不建立“未分类”子目录；缺少 `model` 关系本身就表示当前尚未归属。页面按可独立追踪的共同根因形成，不按一次对话、资料章节或零散知识点逐项创建。

需要派生独立考核或处理 Checkpoint 时，再读取 [`assessment.md`](assessment.md)。
