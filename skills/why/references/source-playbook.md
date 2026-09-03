# Source Playbooks

Why 技能会针对每一种可用的证据类别并发派发一名独立的调查员子 Agent，每位调查员专门阅读下方对应的单个证据源操作规程。以下规程给出了常见 MCP 的具体操作示例；若环境中存在同类别的其他 MCP，可参照适配调整。

| 证据类别 | 专用规程 | 示例 MCP |
|---|---|---|
| 源码版本控制历史 | [`code-archaeology.md`](./sources/code-archaeology.md) | git, `gh` |
| 需求与缺陷工单跟踪 | [`linear.md`](./sources/linear.md) | Linear（可适配 Jira、GitHub Issues、Plane、Shortcut） |
| 长篇设计与知识文档 | [`notion.md`](./sources/notion.md) | Notion（可适配 Confluence、Google Docs、Coda） |
| 实时即时通讯群聊 | [`slack.md`](./sources/slack.md) | Slack（可适配 Discord、Microsoft Teams、Mattermost） |
| 基础设施可观测性 | [`datadog.md`](./sources/datadog.md) | Datadog（可适配 New Relic、Honeycomb、Grafana、Splunk） |
| 错误与异常监控 | [`sentry.md`](./sources/sentry.md) | Sentry（可适配 Rollbar、Bugsnag、Airbrake） |
| 产品数仓与业务指标 | [`databricks.md`](./sources/databricks.md) | Databricks SQL（可适配 Snowflake、BigQuery、ClickHouse、dbt） |

横切透视维度：

- [`incident-postmortem.md`](./sources/incident-postmortem.md)：当目标代码呈现出防御性特征（空值校验、重试、超时、限流、功能开关、出口防护、OOM 保护等）时，各调查员均应追加此规程开展事故考古。
