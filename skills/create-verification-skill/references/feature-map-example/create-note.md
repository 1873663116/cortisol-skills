# Create a note

创建便签功能允许用户通过 Web 浏览器或 CLI 终端保存带有标题的便签、取消未完成的草稿，并通过第二个面向用户的独立视图验证便签已成功持久化。

## Sub-features

- `create-open`：通过浏览器中的各个入口打开空白便签编辑器。
- `create-save`：成功持久化保存便签标题与正文。
- `create-cancel`：丢弃未保存的 Web 界面便签草稿。
- `create-cli`：通过终端命令行创建相同数据形态的便签。

## How to get to it (user POV)

- 点击浏览器顶部工具栏中的 `New note` 按钮。
- 在页面焦点未处于输入框内时，在浏览器中按下键盘按键 `n`。
- 在终端中执行 `notes create --title <title> --body <body>` 命令。

## Driving it with control-notes

Preconditions:

- Notes 应用在 `http://127.0.0.1:4173` 正常运行。
- 当前不存在标题为 `Release checklist` 的便签。
- `control-notes doctor` 检查通过，报告预期的 URL 与隔离的一次性数据目录。

- **打开编辑器**：点击 `New note`。执行 `control-notes browser click --role button --name "New note"`。出现名为 `Note editor` 的表单，焦点自动处于 `Title` 输入框中。
- **输入内容**：键入标题与正文。执行 `control-notes browser fill --role textbox --name "Title" --value "Release checklist"` 以及 `control-notes browser fill --role textbox --name "Body" --value "Tag and publish"`。界面上的 `Save note` 按钮变为可用状态。
- **保存便签**：点击 `Save note`。执行 `control-notes browser click --role button --name "Save note"`。出现 `Note saved` 提示状态，且页面标题区域显示为 `Release checklist`。
- **验证持久化**：返回便签列表并重新打开该便签。执行 `control-notes browser click --role link --name "All notes"` 以及 `control-notes browser click --role link --name "Release checklist"`。编辑器中完整呈现先前保存的标题与正文内容。
- **取消草稿**：新建便签，输入 `Discard me`，然后点击 `Cancel`。执行 `control-notes browser click --role button --name "New note"`、`control-notes browser fill --role textbox --name "Title" --value "Discard me"`，随后执行 `control-notes browser click --role button --name "Cancel"`。页面返回便签列表，且列表中不包含 `Discard me` 链接。
- **CLI 入口验证**：通过命令行创建第二条便签。执行 `control-notes cli -- notes create --title "CLI note" --body "Created from terminal" --format json`。进程退出码为 `0`，标准输出中包含新建便签的 ID 与标题。
- **捕获证据**：从 `All notes` 列表中重新查看这两条便签。执行 `control-notes browser snapshot --aria --path artifacts/create-note/list.aria.txt` 以及 `control-notes browser screenshot --path artifacts/create-note/list.png`。捕获的证据文件中清晰包含 `Release checklist` 与 `CLI note`。

## Gotchas

- 当焦点处于输入框内部时按下 `n` 会直接输入字母，而不会触发新建编辑器快捷键。
- 便签标题在保存时会自动去除首尾空白。断言时须匹配实际渲染出的标题，而非草稿输入值。
- 仅凭界面出现的“保存成功”Toast 提示不足以作为落盘证据，必须重新从列表中点开读取以验证持久化。
- 测试结束执行清理时应删除 `Release checklist` 与 `CLI note` 测试数据，但必须完整保留捕获的证据文件。
