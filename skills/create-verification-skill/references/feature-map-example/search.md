# Search notes

搜索便签功能允许用户根据标题或正文文本检索便签、查看匹配详情，并能清晰区分“无搜索结果”与“搜索服务不可用”等不同状态。

## Sub-features

- `search-open`：通过各个受支持的浏览器入口唤起搜索弹窗。
- `search-match`：返回标题或正文匹配的结果，而不修改任何便签数据。
- `search-open-result`：在便签编辑器中打开选中的搜索结果。
- `search-empty`：针对无匹配项的查询关键词展示标准的空状态提示。
- `search-clear`：清空搜索输入并恢复展示最近便签视图。
- `search-cli`：在终端命令行中检索并返回相同的匹配便签。

## How to get to it (user POV)

- 点击浏览器顶部工具栏中的 `Search` 按钮。
- 在页面焦点未处于可编辑区域时，在浏览器中按下键盘按键 `/`。
- 在终端中执行 `notes search <query>` 命令。

## Driving it with control-notes

Preconditions:

- Notes 应用在 `http://127.0.0.1:4173` 正常运行。
- 隔离的一次性数据目录中包含标题为 `Quarterly plan` 且正文包含 `Draft budget` 的便签。
- `control-notes doctor` 检查通过，报告预期的 URL 与数据目录。

- **工具栏入口**：点击 `Search` 按钮。执行 `control-notes browser click --role button --name "Search"`。名为 `Search notes` 的对话框弹出，焦点自动处于其搜索框中。
- **快捷键入口**：关闭对话框，聚焦主页面并按下 `/`。执行 `control-notes browser press --key "/"`。相同的搜索对话框弹出，且页面未插入多余的斜杠字符。
- **标题匹配**：键入 `quarterly`。执行 `control-notes browser fill --role searchbox --name "Search notes" --value "quarterly"`。搜索结果列表包含 `Quarterly plan`，且不包含 `Grocery list`。
- **正文匹配**：将查询替换为 `budget`。执行 `control-notes browser fill --role searchbox --name "Search notes" --value "budget"`。结果中仍展示 `Quarterly plan`，并带有正文匹配的高亮片段。
- **打开搜索结果**：点击 `Quarterly plan`。执行 `control-notes browser click --role link --name "Quarterly plan"`。搜索弹窗关闭，编辑器标题区域加载展示 `Quarterly plan`。
- **空结果状态**：重新打开搜索并键入 `volcano`。执行 `control-notes browser fill --role searchbox --name "Search notes" --value "volcano"`。搜索完成后展示 `No matching notes` 状态。
- **清空搜索词**：点击 `Clear search`。执行 `control-notes browser click --role button --name "Clear search"`。搜索框恢复为空，且 `Recent notes` 区域重新取代了结果列表。
- **CLI 命中检索**：从终端执行搜索。执行 `control-notes cli -- notes search "quarterly" --format json`。进程退出码为 `0`，标准输出中包含一个标题为 `Quarterly plan` 的 JSON 对象。
- **CLI 未命中检索**：检索不存在的关键词。执行 `control-notes cli -- notes search "volcano" --format json`。进程退出码为 `0`，标准输出为 `[]`。
- **捕获证据**：捕获包含结果的界面状态。执行 `control-notes browser snapshot --aria --path artifacts/search/results.aria.txt` 以及 `control-notes browser screenshot --path artifacts/search/results.png`。两份证据文件均清晰展示应用名称、查询词以及 `Quarterly plan` 结果。

## Gotchas

- 当焦点处于编辑器或搜索框内部时按下 `/` 会直接输入字符，而不会触发全局唤起搜索。
- 搜索结果在输入后有微小的防抖延迟。必须等待结果列表或空状态元素呈现，严禁使用固定时间的盲目 Sleep。
- 除非用户显式勾选 `Include archived`，否则搜索会自动排除已归档的便签。
- CLI 默认输出适合人类阅读的文本格式。在断言时请务必使用 `--format json` 以获取稳定的结构化数据。
- 打开搜索结果会改变页面当前状态。在验证下一个查询前，必须重新唤起搜索。
