---
name: codex-cli-runtime
description: codex-rescue subagent 调用 Codex CLI 的内部约定
user-invocable: false
---

# Codex CLI Runtime

仅在 `codex-rescue` subagent 内使用本 skill。

## 命令选择

| 情形 | 命令 |
|-----------|---------|
| 默认实现/修复任务 | `codex exec -s workspace-write -a on-failure "<prompt>"` |
| 只读分析、审查、诊断 | `codex exec -s read-only -a untrusted "<prompt>"` |
| 续先前 Codex 线程 | `codex resume --last "<follow-up>"` |
| 显式选模型 | 加 `-m <model>` —— 映射 `spark` → `gpt-5.3-codex-spark` |
| 显式选努力程度 | 加 `-c reasoning.effort=<value>`（none/minimal/low/medium/high/xhigh） |

## 规则

- 每次救援交接恰好一次 CLI 调用 —— subagent 是转发器，不是编排器
- 默认可写（`workspace-write`），除非用户要求只读，或仅审查/诊断
- 把路由 flag（`--resume`、`--fresh`、`--background`、`--wait`、`--model`、`--effort`）从 prompt 文本中剥离后再传给 CLI
- `--resume` → 使用 `codex resume --last`；`--fresh` → 使用全新 `codex exec`
- 除剥离 flag 外，保留用户任务原文
- **原样**返回 stdout —— 不要自己查仓库、解题或做后续工作
- 若未安装 Codex，返回空（不要改用主 Agent 侧实现顶替）

## 安装检查

```bash
which codex || echo "NOT_FOUND"
```

若未找到，用户需要：
```bash
npm install -g @openai/codex
```
