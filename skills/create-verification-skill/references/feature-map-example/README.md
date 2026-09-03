# Notes verification map

本目录是验证 Notes 应用面向用户真实行为的权威维护来源。在驱动应用前先查阅本索引，并以对应功能文件作为确定性的操作规程。

## Baseline preconditions

- 启动 Notes 应用于 `http://127.0.0.1:4173`，配置独立的一次性数据目录。
- 注入环境变量 `NOTES_DATA_DIR=/tmp/notes-verify-$RUN_ID`，确保并发测试运行之间互不污染共享状态。
- 注入标题分别为 `Quarterly plan` 与 `Grocery list` 的初始种子便签。
- 将 `control-notes` 与 `notes` CLI 工具加入系统 `PATH`。
- 执行 `control-notes doctor`，核验当前 URL、数据目录及构建版本号均符合预期。
- 严禁驱动非本次验证运行自身拉起的任何既有实例。

## Driving conventions

- 除非特定用例显式另有说明，所有操作均须从基线状态起步。
- 优先采用 ARIA 语义角色与可访问性名称定位元素，严禁依赖脆弱的 CSS 选择器或绝对 DOM 层级。
- 所有命令均须原样精确执行，保留引号与参数选项不变。
- Web 界面动作统一通过 `control-notes browser` 执行。
- 终端命令行动作统一通过 `control-notes cli -- <command>` 执行。
- 数据变更测试后须重置种子状态；执行清理时坚决不得删除已捕获的证据文件。

## Proof and skip reporting

- 完整捕获用户触发动作与伴随的状态变更，而非仅截取最终画面。
- Web UI 验证证据须包含 ARIA 结构快照与展示应用标识的可视化界面截图。
- CLI 验证证据须包含所执行的完整命令、标准输出（stdout）、标准错误（stderr）以及进程退出码。
- 数据变更类验证须提供只读维度的二次查询证据，以确认数据真实落盘。
- 每份证据文件均须清晰标注对应的功能 ID 与所使用的入口路径。
- 若遇不可达路径，须精确汇报所尝试的命令及未满足的前置条件。
- 严禁将某入口由于前置受阻而跳过的情况，偷换为通过其他入口已完成验证。

## Feature entry contract

每个功能分册均以一级标题（H1）和一段简要说明该功能在用户端表现的文字开篇，随后严格依序包含以下四个二级标题（H2）：

1. `Sub-features`：简短的功能子项 ID 列表，每行对应一项具体行为。
2. `How to get to it (user POV)`：列出所有可触达该功能的用户入口。
3. `Driving it with <harness>`：以 `Preconditions:` 开头，使用带标签的项目符号将每个用户动作与精确命令及预期客观结果一一配对。
4. `Gotchas`：列出可能导致测试失真或白费功夫的注意事项与陷阱。

保持功能地图纯粹：严禁堆砌内部实现细节，仅记录面向用户的交互路径、语义稳定句柄、必要状态、确切命令以及客观验证证据。

## Features

- [创建便签（Create a note）](./create-note.md)：覆盖 Web 界面与 CLI 终端的便签创建、取消草稿、数据落盘持久化与测试清理。
- [搜索便签（Search notes）](./search.md)：覆盖工具栏、全局快捷键与 CLI 终端搜索，包含命中、无结果及清空搜索等状态。
