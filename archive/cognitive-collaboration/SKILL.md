---
name: cognitive-collaboration
description: 在持续实践中识别用户因理论知识缺失产生的困惑，通过知识检验、认知债和独立考核校准并沉淀理解。
disable-model-invocation: true
---

# Cognitive Collaboration

本 Skill 负责在实践过程中判断并维护认知协作状态，不拥有项目执行拓扑。默认继续实践；只有用户明确要求认知协作，或困惑确实指向理论知识缺失时，才采取认知动作。

需要判断是否进入或退出认知协作状态时，读取 [`references/state.md`](references/state.md)。
进入认知协作状态后，先读取个人 Wiki 的 `AGENTS.md`，再按当前动作渐进读取：

- 进行知识检验或判定结果时，读取 [`references/knowledge-testing.md`](references/knowledge-testing.md)。
- 记录过程或持久化 Cognitive Debt 时，读取 [`references/persistence.md`](references/persistence.md)。
- 派生独立考核并收束结果时，读取 [`references/assessment.md`](references/assessment.md)。
