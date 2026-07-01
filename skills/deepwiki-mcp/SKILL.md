---
name: deepwiki-mcp
description: Use for public GitHub repository orientation, architecture maps, and repository-scoped questions through DeepWiki MCP. Verify exact code claims against real source before using them for reviews, fixes, or decisions.
---

# DeepWiki MCP

Use DeepWiki MCP for public GitHub repository orientation.

## When to Use

Use it when the user asks to understand a public GitHub repository, map its architecture, or ask a repository-scoped question.

Do not treat DeepWiki as final evidence for code review findings, bug fixes, security claims, compatibility claims, or line-specific implementation details. Use it for orientation, then verify important claims against the real source.

## Tools

Use `mcp__deepwiki`:

- `read_wiki_structure`: Start here for repository orientation.
- `read_wiki_contents`: Fetch the repository wiki when the user needs broader context.
- `ask_question`: Ask focused questions. Pass the user's full question, not keywords.

## Boundaries

The public DeepWiki MCP server targets public GitHub repositories and does not require authentication. For private repositories, use the local checkout, GitHub connector, or Devin MCP if configured.

Official MCP endpoint: `https://mcp.deepwiki.com/mcp`.
Official docs: `https://docs.devin.ai/work-with-devin/deepwiki-mcp.md`.
