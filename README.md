# CodexLens

CodexLens 帮 Codex 看懂图片、Word 和 PDF 里的内容。

把 Codex 接入Deepseek v4等纯文本模型，会导致Codex看不懂你发来的图片或 Word 文档里的图片。

CodexLens 会把图片交给一个视觉模型分析，再把结果变成文字交给你正在使用的下游模型：

```text
图片 / Word / PDF -> CodexLens -> 视觉模型 -> 文字说明 -> 你的下游模型
```

只需要准备一个视觉模型或全模态模型的 API Key，再把一段提示词粘贴给 Codex，即可自动配置并生效。

## 它能做什么

- 分析一张图片，例如曲线图、表格截图、实验照片。
- 读取 Word 和 PDF 的正文，并分析其中可提取的图片。
- 让 Codex 在需要时调用这些能力，帮助总结、解释或对比科研材料。
- 自动把粘贴到输入框的图片转成文字说明。默认开启。

默认安装后，CodexLens 会自动处理粘贴到输入框的图片。接入 DeepSeek v4 等纯文本模型后，模型本身无法识别这类图片；CodexLens 会先用视觉模型生成文字说明，再把说明交给下游模型。重启 Codex 后，直接粘贴图片并正常提问即可。

## 开始前：获取一个百炼 API Key

CodexLens 需要一个全模态或视觉模型 API Key 来调用视觉模型。默认使用百炼的 `qwen3.5-flash` 来读图，每个人有100万的免费额度，足够分析上百张图片。

1. 打开 [阿里云百炼控制台](https://bailian.console.aliyun.com/)，登录并开通百炼。
2. 在右上角选择地域，通常选“华北 2（北京）”。
3. 打开 **API Key** 页面，点击创建。
4. 复制新建的 Key。它通常只会完整显示一次。

百炼账号或活动可能提供免费额度，实际额度、可用模型和价格请以你的百炼控制台为准。

不要把 Key 放进 `Path`、代码、GitHub 仓库、截图或公开文档，因为这可能会导致你的Key泄漏。完整的获取、保存和泄漏处理说明见 [API Key 配置指南](docs/api-key-setup.md)。

## 最简单的安装方式：交给 Codex

打开 [Codex 自动部署提示词](docs/codex-deploy-prompt.md)，复制其中完整的一段文字，粘贴到 Codex 对话中。它会完成下载项目、安装依赖、配置 CodexLens 和基础测试。

默认提示词允许你把 API Key 一起发给 Codex，步骤最少。但请先知道：Key 会进入当前对话上下文。提示词已经要求 Codex 不把 Key 写入仓库、配置文件、日志或命令输出；如果你不愿把 Key 发到对话中，请使用提示词页面里的“更安全的两步法”。

安装完成后，关闭并重新打开 Codex。新开的 Codex 才能读取新的 API Key 和 CodexLens 配置。

## 安装后怎么用

把图片粘贴到 Codex 输入框后，直接正常提问即可。例如：

```text
说明这张图表达了什么、关键数值和可能的异常。
```

Word 和 PDF 仍需要明确让 Codex 使用 CodexLens：

```text
请使用 CodexLens 读取并总结这个 Word 或 PDF，重点解释其中的图表。
```

Word 和 PDF 不会被 MCP 工具自行接管。明确说“使用 CodexLens”能让 Codex 调用正确的工具。

## 图片自动拦截

当你把图片粘贴到 Codex 输入框时，CodexLens 会在图片到达下游模型之前先截住它，把图片发给视觉模型，得到文字说明后，再把这段说明连同你的问题交给下游模型。

所以，即使你接入的是 DeepSeek v4 这类纯文本模型，粘贴图片后它仍能根据 CodexLens 生成的文字说明回答问题。图片自动拦截会消耗视觉模型的 API 额度，默认开启。

## 开启或关闭图片自动拦截

图片自动拦截默认开启。想改变状态时，直接对 Codex 说下面任意一句：

```text
请开启 CodexLens 的图片自动拦截。
```

```text
请关闭 CodexLens 的图片自动拦截，但保留 Word、PDF 和图片分析工具。
```

Codex 会运行对应的开关命令。开启时会修改 Codex 的 `base_url`，安装脚本会先备份原配置；关闭时会恢复它。每次开关后都要重启 Codex。具体说明见 [图片自动拦截开关](docs/image-proxy-toggle.md)。

已经安装过旧版本的用户需要明确说一次“请开启 CodexLens 的图片自动拦截”。默认值只会影响之后的新安装。

## 关闭文档和图片分析工具

Word、PDF 和手动图片分析（在输入框中粘贴图片路径，而不是直接粘贴图片）由 CodexLens MCP 服务器提供。若你不再需要这一功能，可以在 Codex 的 **设置** 中找到 **MCP 服务器**，将 **CodexLens** 关闭。

请先关闭图片自动拦截，再关闭 MCP：

1. 对 Codex 说“请关闭 CodexLens 的图片自动拦截，但保留 MCP 工具”，然后重启 Codex。
2. 打开 Codex 设置，在 MCP 服务器列表中关闭 CodexLens。
3. 再重启一次 Codex，确保 MCP 进程已经停止。

目前图片自动拦截和 MCP 工具由同一个 CodexLens 进程启动。因此，若自动拦截仍开启，直接在设置里关闭 CodexLens 也会让图片代理停止，导致图片请求无法正常处理。

<details>
<summary>不想把 API Key 发给 Codex：更安全的两步法</summary>

先在 PowerShell 中运行下面命令，把 Key 保存为 Windows 用户环境变量。把 `你的API_KEY` 换成刚从百炼复制的内容。

```powershell
[Environment]::SetEnvironmentVariable("CODEX_LENS_API_KEY", "你的API_KEY", "User")
```

然后打开 [Codex 自动部署提示词](docs/codex-deploy-prompt.md)，使用其中的两步法提示词。它会只检查 Key 是否已经存在，不会要求你把 Key 粘贴进对话。

设置环境变量后，也需要重启 Codex。

</details>

<details>
<summary>常见问题</summary>

**装好了，为什么粘贴图片后还是看不懂？**

先确认 CodexLens MCP 在 Codex 设置中处于启用状态，再重启 Codex。如果你曾关闭自动拦截，请对 Codex 说“请开启 CodexLens 的图片自动拦截”。

**设置了 API Key，为什么还是报错？**

通常是 Codex 在设置 Key 之前就已经打开。完全退出并重新打开 Codex 后再试。

**会收费吗？**

每次图片分析都会调用百炼视觉模型，会消耗你的免费额度或产生模型费用。请在百炼控制台查看实际用量和价格。

**怎么关闭自动处理或完全卸载？**

在项目目录运行：

```powershell
python .\install.py --disable-image-proxy
python .\install.py --uninstall
```

关闭或卸载后重启 Codex。更多说明见 [图片自动拦截开关](docs/image-proxy-toggle.md)。

</details>

<details>
<summary>进阶：手动安装与技术说明</summary>

如果你希望自己运行命令，需要 Python 3.9 或更高版本。详细要求见 [Python 环境说明](docs/python-environment.md)。

```powershell
python -m pip install -e .
python .\install.py
```

无参数安装会开启图片自动拦截。若只想保留 Word、PDF 和图片分析工具而不接管粘贴图片，运行 `python .\install.py --mcp-only`。

可以用下面命令查看安装状态：

```powershell
python .\install.py --status
```

CodexLens 提供四个 MCP 工具：`analyze_img`、`read_docx`、`read_pdf` 和 `read_document`。项目目录、手动运行方式、测试命令和已知限制请查看 [完整技术说明](docs/python-environment.md)、[图片自动拦截开关](docs/image-proxy-toggle.md) 和源代码注释。

</details>

## 许可

MIT License，见 [LICENSE](LICENSE)。
