# Agent Collaboration

这个上下文定义长期协作 Skill 之间的职责边界，避免执行控制与用户认知状态由同一个概念拥有。

## Language

**Orchestrator**:
拥有当前目标的执行拓扑、委派、证据整合与最终收束的主控角色。
_Avoid_: Cognitive Companion

**Cognitive Collaboration**:
在持续实践中检验、记录并校准用户理论理解的协作状态，不拥有项目执行拓扑。
_Avoid_: Orchestration

**Practice State**:
没有认知动作需要执行时的默认状态，Agent 只围绕当前实际目标继续工作。
_Avoid_: Normal Mode

**Cognitive Debt**:
已有证据支持、尚未解决的理解、提取或应用问题，是 Wiki 中独立存在的知识页面。
_Avoid_: Unanswered Question

**Model**:
用户对一个系统的当前系统性理解；它可以与 Cognitive Debt 建立关系，但不是 Cognitive Debt 的容器。
_Avoid_: Topic Folder
