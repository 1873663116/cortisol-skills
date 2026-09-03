# Bugbot 评审意见分流准则（Bugbot triage）

当**看护** Playbook（`../playbooks/babysit.md`）处理由 Bugbot 或自动化代码审查工具生成的 Review 评论时，使用本参考规范。核心目标不是盲目无视 Bugbot，而是杜绝将机器人的每一条意见都机械地当成必须改动代码的绝对指令。

## 判定标准

在动手改动代码前，必须先对每条 Bugbot 评审讨论串进行定性分类：

- `fix`（修复）：该评论指出了在代码正确性、安全性、隐私合规、数据丢失风险、鉴权认证、计费逻辑、数据迁移、操作幂等性、并发竞态或既有生产行为上的实质问题。必须在归属该代码的最底层 PR 上实施修复，随后在讨论串中回复具体的 commit SHA 并将其标记为已解决。
- `dismiss`（驳回）：该评论符合已记录在案的低风险噪音模式，且当前代码实现与上下文足以证明该顾虑无需改动代码。在讨论串中回复简明具体的技术反证理由，并将其标记为已解决。
- `ask`（求证）：该评论属于全新出现的模式、涉及高危严重级别、牵涉安全/隐私/核心数据，或其本身语义模糊不清。直接向用户提问求证，严禁主观臆测。

存疑时坚决向用户求证。漏掉一条关于代码风格的琐碎意见代价极低，但漏掉一个真实的数据损坏或安全漏洞代价惨重。

## 沉淀模式的格式

后续提炼新增的有效模式统一按如下结构规范书写：

```markdown
### <模式简短名称>

- Confidence: candidate | recurring | strong
- Skip when: <满足跳过审查的充分必要条件>
- Do not skip when: <必须拦截修复的风险边界>
- Example signal: <用于识别该模式的典型特征词或代码上下文>
- Source: <关联的 PR/评论 URL 或简要历史背景>
```

仅有 1 到 2 个案例时标注为 `candidate`（候选）；经过多次真实生产验证与驳回后提升为 `recurring`（复现）；仅当该模式界定极其严密、被反复交叉验证且风险极低时，方可标注为 `strong`（强置信）。

## 反复出现的可跳过模式

### 有意为之的 UI 或设计系统视觉改动

- Confidence: candidate
- Skip when: PR 描述、设计稿截图、UI 评审记录或邻近代码中已明确注明该视觉调整，而 Bugbot 的评论仅是在机械复述某个全局共享的视觉默认值发生了变更。
- Do not skip when: 评论指向无障碍访问（a11y）、焦点可见性（focus visibility）、键盘无障碍导航、色彩对比度违规，或破坏了当前 PR 无意改动的组件公开 API 契约。
- Example signal: 针对焦点轮廓外框、按钮物理尺寸、外边距或共享组件视觉默认值的评论，且 PR Owner 明确回复“有意为之（intended）”。

### Bugbot 上下文缺失导致的未识别上层调用

- Confidence: candidate
- Skip when: Bugbot 将某个导出符号、UI 组件、辅助函数或文件标记为“未使用（unused）”，而 `gt ls -s`、堆叠上层 PR 的 diff 或 PR 整体上下文明确显示堆叠中更靠后的后续 PR 已经使用了该符号。
- Do not skip when: 当前 PR 不属于任何 stack、该符号属于对外暴露的公开 API，或所谓“上层使用”无法得到确凿核实。
- Example signal: “Exported component is never used”，而人工回复为“used upstack（上层 PR 已使用）”。

### 双轨演进与渐进式替换期间的临时代码重复

- Confidence: candidate
- Skip when: PR 为保障灰度验证平滑推进，有意保留少量重复代码，使新实现链路与正在被替换、验证或逐步下线的旧链路双轨并行。
- Do not skip when: 重复的代码改动涉及安全性、计费扣费、底层数据访问或公开 API 行为，或引入长期存在的公共抽象能够显著降低系统风险。
- Example signal: “Significant duplication” 或 “duplicated validation logic”，且 PR Owner 明确解释旧链路即将下线删除，或该重复逻辑是有意内聚在局部的。

### 既有框架或基础组件不变量已提供充分保障

- Confidence: candidate
- Skip when: 该潜在顾虑已由底层共享组件、框架运行契约、强类型系统不变量，或在当前 diff 及其周边代码中可见的单一事实来源严格保证。
- Do not skip when: 该不变量仅属于口头假设而未在代码中强制约束、逻辑强依赖时序先后，或跨越了异步/跨进程状态边界导致运行时可能发生状态发散。
- Example signal: 抱怨内层 Popover 缺少 `max-height` 限制，而外层共享 Popover 容器已在视口级别强制施加了尺寸截断；或指责某个值可能为 null，而本地判断依据与传入参数来自完全相同的不可变数据源。

### PR Owner 显式声明的后续跟进或延后清理

- Confidence: candidate
- Skip when: PR Owner 明确说明该项属于已记录的后续独立待办（Follow-up），当前 PR 并未使既有行为进一步恶化，且该评论不涉及高风险核心逻辑。
- Do not skip when: Agent 在缺乏 Owner 输入的前提下自主行动、该问题属于中高严重级别的线上产品行为缺陷，或延后处理等同于直接将全新的功能回归带入主干。
- Example signal: “I'll worry about that later” 或 “we'll delete this eventually”。

### 自行撤回的评论，或已明确注明为误报的规则类提示

- Confidence: recurring
- Skip when: 评论正文或 Bugbot 后续的自动回复已明确说明该发现已被撤回、代码已合规或属于误报，且 Agent 能够在本地直接核实相关规则。
- Do not skip when: 唯一的证据仅为某人在高危问题讨论中单方面留下一句未经解释的“误报”。
- Example signal: 针对文件命名规范的自动化提示，而正文后续判定该文件名已完全符合规范。

## 默认必须升级询问的场景

以下类别的评审意见严禁自动跳过，即便历史上有其他 PR 曾驳回过相似内容：

- 涉及系统安全、隐私合规、鉴权认证、计费逻辑、数据留存周期、模型训练数据隔离与权限隔离边界的任何发现。
- 标记为高严重级别（High/Critical）的任何发现。
- 涉及数据库迁移、Schema 变更、操作幂等性、高并发竞态与跨系统分布式行为的任何发现。
- 建议的修复方案极其精简、且能在完全不改变产品预期行为的前提下显著降低系统风险的评论。

历史数据表明，人类工程师有时可能会出于进度压力主观驳回安全或数据流相关的审查意见。必须将此类情况视为特定 Owner 的单次主观裁决，绝不能将其沉淀为全团队通用的自动跳过规则。

## 近期看护中提炼的候选模式

在看护过程中或任务收尾后，将对团队具有复用价值但尚处于初期阶段的新模式追加于此。一旦在多个实际 PR 中得到充分验证，优先将成熟模式提炼提升至上方正式章节。

### 手动重写浏览器原生行为的逻辑缺陷

- Confidence: candidate
- Skip when: 绝大多数情况下严禁跳过。当 diff 试图用自定义手写逻辑替代浏览器原生底层行为时（如用基于 JS 计算定位的克隆节点替代原生 CSS `sticky`、用手动事件转发替代原生滚动容器、用 `mask`/`clip-path` 替代原生图层绘制遮挡），Bugbot 针对此类复杂手写逻辑指出的缺陷绝大多数全部属实。
- Do not skip when: 该缺陷涉及事件转发盲区（`wheel deltaMode`、触摸平移、边缘滚动链断裂、点击碰撞容差）、`mask`/`clip` 与底层命中测试（hit-testing）的脱节，或此类实现中 Observer 回调与 React 内部状态更新的时序竞态。默认一律实施修复。
- Example signal: “masks do not affect hit-testing”、“overlay blocks wheel scroll”、“ignores deltaMode”、“runs in the IntersectionObserver callback before React applies state”。
- Source: 某个处理粘性遮挡的 PR，Bugbot 连续审查 6 轮提出约 18 项缺陷，全部经过实证并彻底修复，无一属于误报驳回。

### 契约测试与文档漂移的快速核实策略

- Confidence: candidate
- Skip when: 严禁跳过核实本身，因为执行核实仅需一条本地命令。当 PR 包含用于锁定协议规范或文档措辞的契约测试（如针对 `SKILL.md` 正则断言或文档文本快照），而 Bugbot 提出“测试与文档对不上”时，先在当前 PR 的 head 分支上直接运行该测试，再做定性分类。测试跑红即代表机器人指控属实；测试跑绿则可直接作为驳回回复中的确凿反证。
- Do not skip when: 不适用。本条属于快速验证策略，而非驳回模板。注意“多轮重复倾向于驳回”的经验法则在此处极易误伤，因为契约测试之所以发生漂移，往往正是由于前几轮修复改动了对应文本所致。
- Example signal: “Contract test omits the pre-fix wait” 出现在一个此前 commit 曾修改过对应规范文本的 PR 中；在 head 上运行测试，精准在被引用的断言处失败。
- Source: 某个锁定文档规范的 PR，Bugbot 审查 8 轮；尽管前序轮次均已修复并解决，第 7 轮的漂移指控完全属实。

### 前序加固提交已修复的陈旧安全审查意见

- Confidence: candidate
- Skip when: Agent 自动化安全审查（或类似工具）声称缺少某项鉴权或输入校验，而当前 PR 的最新 head 明确已经包含了该安全门禁及对应测试（通常是在安全审查扫描触发后由后续的加固 commit 补齐）。
- Do not skip when: 被引用的安全校验函数对当前主体属于空操作、校验逻辑发生在受保护的副作用之后，或声明的目标主体未被测试用例实际覆盖。
- Example signal: 标记为 HIGH 级别的 “missing authorization check” 警告，而在最新 head 分支上该权限门禁已在所有副作用触发前严格调用。
- Source: 某个 Webhook 接口 PR，其安全加固 commit 的提交时间晚于自动化安全审查的扫描时间点。

### 随意放宽刻意收窄的错误捕获条件会掩盖真实错误

- Confidence: candidate
- Skip when: 审查意见要求将一个刻意精确收窄的错误判断条件（如针对特定 `errno`、业务错误码或状态类型）放宽为通用的全局捕获，而该精确条件本身编码了关键的业务区分。典型场景是以 `ENOENT` 为边界的依赖回退逻辑：“未安装对应依赖”与“命令已执行但运行报错”属于两种截然不同的故障。若只要退出码非零就无脑重试回退，会导致原本正当的业务失败（文件未找到、鉴权过期、网络故障）在备用路径上重复执行，最终抛出备用路径的混淆错误，彻底掩盖真实的原始病因。
- Do not skip when: 该精确条件确实遗漏了同一错误类别下的其他合法情况（如另一个代表依赖不可用的 errno 如 `EACCES`，或其他传输层异常）、未处理分支会导致数据丢失或残留中间脏状态，或重试逻辑本身具备完全幂等性且能正确暴露原始错误。
- Example signal: “only retries when X fails with ENOENT … never tries the fallback even when a working Y exists”，对应代码的回退逻辑是为缺失底层二进制准备的，而非为处理运行时业务失败准备的。
- Source: 某个 CLI 重命名重构 PR，其依赖回退机制专用于处理二进制未安装，而非吞没运行报错。
