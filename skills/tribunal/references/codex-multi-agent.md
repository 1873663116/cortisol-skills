# Codex Multi-Agent 路由

在 Codex 中使用当前可用的 Multi-Agent 或 subagent 工具执行 `tribunal`。本路由保留审计、辩护、盲审裁决三段协议。

## 编排

1. 主 Agent 准备 `target`、`contextMap`、`lenses`、`defensePrompt`、`judgePrompt` 和可选 `seededDefects`。
2. 如果 `target` 是文件路径，主 Agent 在派发任务时明确要求 subagent 读取文件全文。
3. 为每个 `lens` 派发 challenge subagent。每条问题必须带 `issueId`、证据和理由。
4. 派发 dedup subagent 合并同源问题。输出保留 `issueId` 和 `sourceIssueIds`。
5. 派发 defense subagent 审视去重后的问题。每条回应必须带同一个 `issueId`。
6. 派发一个独立 judge subagent。judge 只接收被审对象、去重问题、辩护意见和必要上下文。
7. 主 Agent 汇总 `confirmed`、`rejected`、`uncertain`、`stats` 和 `seededRecall`，然后关闭不再需要的 subagent。

## 输出字段

challenge 和 dedup 阶段的问题对象使用同一核心字段：

```json
{
  "issueId": "challenge-1-001",
  "title": "一句话问题标题",
  "category": "真实性 | 可行性 | 累赘 | 缺漏 | 其他",
  "severity": "high | medium | low",
  "evidence": "文档句子、文件路径、代码位置或可核实事实",
  "rationale": "为什么这构成问题"
}
```

dedup 额外返回：

```json
{
  "sourceIssueIds": ["challenge-1-001", "challenge-2-003"],
  "mergedCount": 2
}
```

defense 返回：

```json
{
  "reviews": [
    {
      "issueId": "challenge-1-001",
      "stance": "驳回 | 部分成立 | 成立",
      "argument": "辩护理由"
    }
  ]
}
```

judge 返回：

```json
{
  "rulings": [
    {
      "issueId": "challenge-1-001",
      "title": "原问题标题",
      "category": "类别",
      "verdict": "confirmed | rejected | uncertain",
      "severity": "high | medium | low",
      "reasoning": "裁决理由",
      "action": "如果 confirmed，给出下一步处理建议；否则说明无需行动或待用户拍板"
    }
  ]
}
```

## 失败边界

- 结构化输出无法解析时，让该 subagent 只重发 JSON。重发仍失败时，停止该阶段或带着缺失项继续汇报，不在主线程改写实质判断。
- 等待 subagent 时避免无限等待。遇到超时、需要输入或非终止状态时，记录该阶段不可用，并关闭不再需要的 subagent。
- 完成、失败、放弃重试或用户中断后，关闭已经不需要的 subagent。
- 子 Agent 数量由主 Agent 判断。任务变大时分批派发，避免一次占满并发额度。

## 最小派发模板

challenge subagent：

```text
执行审计。

审计立场：
<lens>

被审对象：
<target 或文件路径>

可核实上下文：
<contextMap>

可用工具和路径：
<需要显式传入的 skill、MCP 工具、工作目录、沙箱边界>

要求：
1. 如果被审对象是文件路径，先读取文件全文。
2. 每条问题都必须有证据。
3. 每条问题都带稳定 issueId。
4. 只输出合法 JSON，格式为 {"issues":[...]}。
```

judge subagent：

```text
执行盲审裁决。

被审对象：
<target 或文件路径>

可核实上下文：
<contextMap>

去重问题与辩护意见：
<issues and defenses>

要求：
1. 逐条裁定 confirmed、rejected 或 uncertain。
2. 只裁定输入清单中的问题。
3. 用 issueId 对齐问题。
4. 只输出合法 JSON，格式为 {"rulings":[...]}。
```
