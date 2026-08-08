---
name: codex-result-handling
description: 在 rescue 或审查运行结束后，向用户呈现 Codex 输出的内部指引
user-invocable: false
---

# Codex 结果呈现

在 `codex-rescue` 或审查运行之后，向用户呈现 Codex 输出时使用本 skill。

## 通用规则

- 保留 Codex 输出中的结论、摘要、发现与下一步结构
- 文件路径与行号按 Codex 报告原样使用 —— 不要擅自规范化或猜测
- 保持证据边界：若 Codex 标为推断、不确定或开放问题，须保留该区分
- 若无发现，明确说明；残留风险备注保持简短
- 若 Codex 改了文件，说明并在可得时列出触及的文件
- 若输出畸形或运行失败，附上最有用的 stderr 行后停止 —— 不要猜测 Codex「本会说什么」

## 审查输出（codex review / adversarial-review）

按严重程度呈现发现。然后**完全停住**。

不要：
- 自行应用任何修复
- 暗示马上要改代码
- 悄悄「纠正」审查里提到的问题

呈现发现后，明确询问用户：
> 「这些问题里，有哪些（如果有）希望我处理？」

等用户答复后再动任何文件。自动应用审查发现 —— 即便看起来很明显 —— 也不允许。

## 救援输出（codex-rescue）

- **原样**返回 Codex stdout
- 不要把失败或不完整的 Codex 运行，变成主 Agent 侧的自行实现
- 若从未成功调用 Codex，不要生成替代答案

## 安装 / 认证错误

若输出表明未安装或未认证，引导用户执行：

```bash
npm install -g @openai/codex   # 若未安装
codex login                    # 若未认证
```

不要即兴发明其它认证流程。
