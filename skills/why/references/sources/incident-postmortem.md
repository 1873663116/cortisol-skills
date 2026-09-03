# Incident & Postmortem Context

这不是一个独立的数据源，而是一个**横切所有数据源的透视视角**。线上事故往往是促使工程师编写防御性代码的根本动因（“我们在经历了 X 次严重故障后补充了这项校验”）。因此，若目标代码呈现出明显的防御性特征（空值校验、补偿重试、超时熔断、动态限流、紧急功能开关等），必须跨所有可用数据源展开专项事故考古：

- **Notion**：检索包含目标文件、功能名或错误特征串的事故复盘报告（Postmortems）。
- **Linear**：检索带有 `incident`、`sev-*`、`postmortem-action-item`（复盘改进项）、`reliability` 标签的工单。
- **Slack**：在目标代码合并当期，检索 `#sev-*` 与 `#incident-*` 事故处置频道。
- **Git**：包含“fix for incident”、“add defensive check”或先回滚再“re-apply with...”的提交说明是强信号。
- **Datadog**：使用 `search_datadog_incidents` 调取事故记录及作为改进项创建的告警规则。
- **Sentry**：排查首次/末次出现时间与 PR 合并时间高度吻合的致命崩溃 Issue。
- **Databricks**：排查在事故时间窗口内急剧飙高、并在 PR 合并后彻底归零的客户端异常埋点事件。

一旦发现事故线索，必须调取完整的事故复盘报告。复盘报告通常包含“后续改进项（Action Items）”章节，可直接与代码改动对齐。当多源证据相互收敛时（Datadog 事故 ID 关联到了 Linear 工单，工单写入了 Notion 复盘报告，并在 Slack 讨论中链接了目标 PR，同时 Databricks 错误事件在修复后彻底消失），该结论具有无可辩驳的强置信度。

当且仅当代码具备防御性特征时投入精力深挖；对于明显不属于防御性逻辑的常规业务代码，果断略过本步骤。
