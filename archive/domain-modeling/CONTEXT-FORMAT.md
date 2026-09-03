# CONTEXT.md 格式规范

## 文档结构

```md
# {上下文名称 / Context Name}

{用一到两句话精炼阐述该上下文的核心职责以及其为何存在。}

## 统一语言（Language）

**Order（订单）**:
{用一到两句话精准定义该术语的领域本质含义。}
_避免使用_: Purchase, transaction

**Invoice（发票）**:
向客户交付商品或服务后发出的正式付款请求凭证。
_避免使用_: Bill, payment request

**Customer（客户）**:
在平台上下单采购商品或服务的个人或企业法人主体。
_避免使用_: Client, buyer, account
```

## 编写准则

- **立场鲜明，拒绝模棱两可**。当同一概念存在多种日常称谓时，敲定最权威的一个作为规范术语，并将其余近义词明确列入 `_避免使用_`（`_Avoid_`）。
- **定义精炼紧凑**。每个术语的定义严格控制在 1 到 2 句话以内。重点定义它“是什么”，而非啰嗦罗列它“能做什么”。
- **仅收录当前项目专属的领域概念**。通用的通用编程概念（如超时时间、异常类型、工具函数模式等）即使在项目中被频繁使用，也绝不属于领域词汇表。在收录前务必自问：这是属于本业务领域的专有概念，还是通用的编程概念？只有前者方可收录。
- **合理使用二级子标题进行逻辑聚类**。当术语自然形成业务分组时，使用二级标题归类；若术语规模较小且归属单一模块，直接使用扁平列表即可。

## 单上下文与多上下文形态

**单一上下文（绝大多数代码库）**：仅在仓库根目录下维护一份 `CONTEXT.md`。

**多限界上下文**：在仓库根目录维护一份 `CONTEXT-MAP.md`，列出所有上下文及其具体路径，并阐明彼此之间的交互拓扑关系：

```md
# 上下文映射拓扑（Context Map）

## 上下文列表（Contexts）

- [Ordering 订单域](./src/ordering/CONTEXT.md) — 接收并全流程跟踪客户订单。
- [Billing 结算域](./src/billing/CONTEXT.md) — 开具账单发票并处理资金支付。
- [Fulfillment 履约域](./src/fulfillment/CONTEXT.md) — 管理仓库分拣、打包与物流配送。

## 协作关系（Relationships）

- **Ordering → Fulfillment**：Ordering 发布 `OrderPlaced` 领域事件；Fulfillment 订阅该事件启动仓库拣货。
- **Fulfillment → Billing**：Fulfillment 发布 `ShipmentDispatched` 领域事件；Billing 订阅该事件开具应收发票。
- **Ordering ↔ Billing**：共享 `CustomerId` 与 `Money` 强类型值对象契约。
```

技能会自动推断适用的结构：

- 若存在 `CONTEXT-MAP.md`，读取该文件定位各个上下文。
- 若仅存在根目录下的 `CONTEXT.md`，按单一上下文处理。
- 若两者皆不存在，在首个领域术语敲定时，按需懒加载创建根目录 `CONTEXT.md`。

当存在多个上下文时，推断当前任务具体关联到哪一个上下文；若存在歧义，主动向用户确认。
