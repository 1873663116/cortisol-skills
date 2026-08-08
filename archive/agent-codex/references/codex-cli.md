# Codex CLI 参考

## 安装

```bash
npm install -g @openai/codex
```

## 命令

| 命令 | 说明 |
|---------|-------------|
| `codex [PROMPT]` | 交互式会话 |
| `codex exec [PROMPT]` | 非交互（适合自动化） |
| `codex review` | 代码审查 |
| `codex resume` | 恢复先前会话 |
| `codex fork` | Fork 先前会话 |
| `codex mcp-server` | 以 MCP server 启动（stdio） |

## 常用选项

| Flag | 说明 |
|------|-------------|
| `-m, --model <MODEL>` | 使用的模型（如 `o3`、`gpt-5.2-codex`） |
| `-C, --cd <DIR>` | 工作目录 |
| `-s, --sandbox <MODE>` | `read-only`、`workspace-write`、`danger-full-access` |
| `-a, --ask-for-approval <POLICY>` | `untrusted`、`on-failure`、`on-request`、`never` |
| `--full-auto` | 等价于 `-a on-request --sandbox workspace-write`（已偏旧，新脚本宜显式写 sandbox） |
| `-i, --image <FILE>` | 向 prompt 附加图片 |
| `--search` | 启用网页搜索 |
| `--add-dir <DIR>` | 额外可写目录 |
| `-c, --config <key=value>` | 覆盖 config.toml |

## 非交互（exec）专用

| Flag | 说明 |
|------|-------------|
| `--json` | 以 JSONL 输出事件 |
| `-o, --output-last-message <FILE>` | 将最后一条 agent 消息写入文件 |
| `--output-schema <FILE>` | 结构化输出的 JSON Schema |
| `--ephemeral` | 不把会话持久化到磁盘 |

## 常见用法

### 快速修复
```bash
codex exec -s workspace-write -a on-failure "Fix the TypeScript build errors in src/"
```

### 非交互 + 结构化输出
```bash
codex exec --json "Analyze the auth module for security issues"
```

### 带截图上下文
```bash
codex exec -i screenshot.png "Fix the UI bug shown in this screenshot"
```

### 只读分析
```bash
codex exec -s read-only -a untrusted "Explain how the authentication flow works"
```

### 续跑先前会话
```bash
codex resume <session-id> "Apply the same approach to the signup flow"
```

## MCP Server

把 Codex 当作 MCP server 提供给其他 Agent：
```bash
codex mcp-server
```

Claude Code 配置（`~/.claude.json`）：
```json
{
  "mcpServers": {
    "codex": {
      "type": "stdio",
      "command": "codex",
      "args": ["mcp-server"]
    }
  }
}
```

### MCP 工具

| 工具 | 说明 |
|------|-------------|
| `codex` | 开启新会话（返回 threadId） |
| `codex-reply` | 按 threadId 续会话 |
