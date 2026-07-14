# 让 Codex 自动部署 CodexLens

你只需要先去百炼控制台创建 API Key。然后复制下面整段文字，粘贴到 Codex 对话中。

注意：如果你把 API Key 粘贴到 Codex，它会进入当前对话上下文。下面的提示词要求 Codex 不把它写入文件、日志或输出；如果你不接受这一点，请使用文末的两步法。

```text
请帮我在这台 Windows 电脑上安装 CodexLens。

GitHub 仓库：
https://github.com/ciamer/codex-lens

我的百炼 API Key：
<把你的 API Key 粘贴在这里>

请按下面要求完成：
1. 克隆或更新仓库到合适的本地目录。
2. 阅读 README.md、AGENTS.md、docs/python-environment.md 和 docs/api-key-setup.md。
3. 选择可用的 Python 3.9 或更高版本环境；如果我没有指定环境，优先使用系统 Python。
4. 安装依赖：python -m pip install -e .
5. 将我提供的 Key 保存为 Windows 用户环境变量 CODEX_LENS_API_KEY。
6. 不要把 Key 写入仓库文件、README、config.toml、日志或命令输出，也不要在回复中显示 Key。
7. 依次运行下面两项基础测试：
   python -m unittest discover -s tests
   python -m compileall .
8. 运行 python .\install.py --mcp-only，把 CodexLens MCP 安装到 Codex。默认不要开启图片自动拦截。
9. 如果修改了 Codex 配置，确认安装脚本已经创建备份。
10. 运行 python .\install.py --status，并只告诉我状态摘要。
11. 最后告诉我仓库路径、测试是否通过，以及提醒我重启 Codex。

如果网络、文件权限或 Codex 配置写入需要授权，请先向我申请授权。
```

完成后请关闭并重新打开 Codex。

## 更安全的两步法

如果不想把 Key 发给 Codex，先由你自己在 PowerShell 设置 Windows 用户环境变量：

```powershell
[Environment]::SetEnvironmentVariable("CODEX_LENS_API_KEY", "你的API_KEY", "User")
```

然后把下面提示词粘贴给 Codex。它不会要求或读取 Key 的内容，只检查变量是否已经配置。

```text
请帮我在这台 Windows 电脑上安装 CodexLens。

GitHub 仓库：
https://github.com/ciamer/codex-lens

我已经自行将百炼 API Key 设置为 Windows 用户环境变量 CODEX_LENS_API_KEY。

请按下面要求完成：
1. 克隆或更新仓库到合适的本地目录。
2. 阅读 README.md、AGENTS.md、docs/python-environment.md 和 docs/api-key-setup.md。
3. 选择可用的 Python 3.9 或更高版本环境；如果我没有指定环境，优先使用系统 Python。
4. 安装依赖：python -m pip install -e .
5. 只检查 CODEX_LENS_API_KEY 是否存在，绝不打印、读取或写入它的值。
6. 依次运行下面两项基础测试：
   python -m unittest discover -s tests
   python -m compileall .
7. 运行 python .\install.py --mcp-only，把 CodexLens MCP 安装到 Codex。默认不要开启图片自动拦截。
8. 运行 python .\install.py --status，并只告诉我状态摘要。
9. 最后告诉我仓库路径、测试是否通过，以及提醒我重启 Codex。

如果网络、文件权限或 Codex 配置写入需要授权，请先向我申请授权。
```

设置用户环境变量后，重启 Codex。已经打开的程序不会自动读到新变量。

## 开启图片自动拦截

默认安装只提供 MCP 工具。若部署完成后你明确想让粘贴的图片自动转成文字说明，请让 Codex 按 [图片自动拦截开关](image-proxy-toggle.md) 操作。开启前它应说明：该功能会修改 Codex 的 `base_url`，安装脚本会备份当前配置，完成后需要重启 Codex。
