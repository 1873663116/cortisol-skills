# agent-codex

跨平台 Agent Skill：把任务委派给 [OpenAI Codex](https://github.com/openai/codex)。

任何支持 Agent Skills 的 AI Agent 都可用本 skill 调用 Codex，完成代码生成、修 bug、实现功能等。

## 工作原理

1. 收集项目上下文（约定、技术栈、目录结构）
2. 为 Codex 组装自洽 prompt
3. 优先经 MCP 工具调用；不可用则回退 CLI
4. 支持多轮：`codex-reply` 或 `codex resume`

## 结构

```
agent-codex/
├── SKILL.md                    # 主 skill 说明
├── README.md                   # 本文件
├── scripts/
│   └── prepare-context.sh      # 为 prompt 收集项目上下文
├── references/
│   └── codex-cli.md            # Codex CLI 参考
├── agents/
│   └── codex-rescue.md         # 救援用 subagent 定义
└── skills/
    ├── codex-cli-runtime/      # CLI 调用约定（内部）
    ├── codex-result-handling/  # 结果呈现约定（内部）
    └── gpt-5-4-prompting/      # Prompt 收紧（内部）
```

## 安装

### 快速安装（检测并写入各 Agent）

```bash
npx skills add Ray0907/agent-codex
```

会自动检测并安装到已支持的 Agent（Claude Code、Codex CLI、Gemini CLI、Cursor 等）。

### 指定某一 Agent

```bash
npx skills add Ray0907/agent-codex -a claude-code
npx skills add Ray0907/agent-codex -a cursor
```

### 手动安装

```bash
# Claude Code
ln -s /path/to/agent-codex ~/.claude/skills/agent-codex

# Codex CLI
ln -s /path/to/agent-codex ~/.codex/skills/agent-codex

# Gemini CLI
ln -s /path/to/agent-codex ~/.gemini/skills/agent-codex
```

## 用法

```
/agent-codex Fix the login page redirect bug
/agent-codex Implement rate limiting for the API endpoints
/agent-codex Refactor the auth module to use JWT
```

## 前置条件

- [OpenAI Codex CLI](https://github.com/openai/codex)：`npm install -g @openai/codex`
- 或在 Agent 中已配置 Codex MCP server（见下）

## 配置 Codex MCP Server

本 skill 在 MCP 可用时走 MCP，否则回退 CLI。启用 MCP：

### 1. 安装 Codex CLI

```bash
npm install -g @openai/codex
```

或 Homebrew：

```bash
brew install --cask codex
```

### 2. 认证

推荐用 ChatGPT 账号登录：

```bash
codex  # 选择 "Sign in with ChatGPT"
```

或设置 API Key：

```bash
export OPENAI_API_KEY="your-api-key"
```

### 3. 配置 MCP Server

`codex mcp-server` 以 stdio 启动 Codex MCP。写入 Agent 配置：

**Claude Code**（`~/.claude.json`）：

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

**Cursor**（`.cursor/mcp.json` 或 `~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "codex": {
      "command": "codex",
      "args": ["mcp-server"]
    }
  }
}
```

**Windsurf**（`~/.codeium/windsurf/mcp_config.json`）：

```json
{
  "mcpServers": {
    "codex": {
      "command": "codex",
      "args": ["mcp-server"]
    }
  }
}
```

**OpenAI Agents SDK**（Python）：

```python
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    name="Codex CLI",
    params={
        "command": "codex",
        "args": ["mcp-server"],
    },
    client_session_timeout_seconds=360000,
) as codex_mcp_server:
    agent = Agent(
        name="Developer",
        mcp_servers=[codex_mcp_server],
    )
```

### 4. 验证

可用 MCP Inspector 测试：

```bash
npx @modelcontextprotocol/inspector codex mcp-server
```

或重启 Agent，确认下列 MCP 工具可用：

### MCP 工具

#### `codex` — 开启新会话

| 参数 | 类型 | 必填 | 说明 |
|-----------|------|----------|-------------|
| `prompt` | string | 是 | 初始用户 prompt |
| `cwd` | string | | 工作目录 |
| `approval-policy` | string | | `untrusted`、`on-failure`、`on-request`、`never` |
| `sandbox` | string | | `read-only`、`workspace-write`、`danger-full-access` |
| `model` | string | | 模型覆盖（如 `o3`、`gpt-5.2-codex`） |
| `developer-instructions` | string | | 注入为 developer 角色消息 |
| `base-instructions` | string | | 覆盖默认系统指令 |
| `config` | object | | 覆盖 `config.toml` 设置 |
| `profile` | string | | `config.toml` 中的配置 profile |

在 `structuredContent` 中返回 `threadId`，用于续聊。

#### `codex-reply` — 续已有会话

| 参数 | 类型 | 必填 | 说明 |
|-----------|------|----------|-------------|
| `prompt` | string | 是 | 后续消息 |
| `threadId` | string | 是 | 上一轮返回的线程 ID |

### 响应格式

```json
{
  "structuredContent": {
    "threadId": "019bbb20-bff6-7130-83aa-bf45ab33250e",
    "content": "Agent response text..."
  }
}
```

若未检测到 MCP 工具，本 skill 自动回退到 `codex exec` CLI。

CLI 续聊应 resume 已有会话，而不是新开：

```bash
codex resume <session-id> "Follow up instruction"
```

## 参考

- [Codex 文档](https://developers.openai.com/codex)
- [Codex CLI GitHub](https://github.com/openai/codex)
- [MCP Server 指南](https://developers.openai.com/codex/guides/agents-sdk)

## License

MIT
