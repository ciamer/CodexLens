# Codex 自动部署提示词

下面的提示词已经填入当前 GitHub 仓库链接。用户唯一需要自己准备的是百炼 API Key。

```text
请帮我在这台电脑上部署 CodexLens。

GitHub 仓库：
https://github.com/ciamer/codex-lens

我的百炼 API Key：
<把你的 API Key 粘贴在这里>

要求：
1. 克隆或更新这个仓库到一个合适的本地目录。
2. 阅读 README.md、AGENTS.md、docs/python-environment.md、docs/api-key-setup.md。
3. 选择可用的 Python 3.9+ 环境；如果我没有指定环境，就优先用系统 python。
4. 安装依赖：python -m pip install -e .
5. 把我提供的 Key 设置为 Windows 用户环境变量 CODEX_LENS_API_KEY。
6. 不要把 Key 写入仓库文件、README、config.toml、日志或命令输出。
7. 运行基础测试：python -m unittest discover -s tests 和 python -m compileall .
8. 运行 install.py --mcp-only，把 CodexLens MCP 安装到 Codex config.toml。默认不要开启图片自动拦截。
9. 如果 config.toml 被修改，确认已经自动备份。
10. 运行 python .\install.py --status，把状态摘要告诉我。
11. 完成后告诉我：仓库路径、是否测试通过、是否需要重启 Codex。

如果某个命令因为网络权限或文件权限失败，请向我申请授权，不要绕过权限。
```

## 更安全的两步部署

如果不想把 API Key 发给 Codex，可以先自己在 PowerShell 设置：

```powershell
[Environment]::SetEnvironmentVariable("CODEX_LENS_API_KEY", "你的API_KEY", "User")
```

然后把提示词里的 API Key 段落删掉，并要求 Codex 只检查变量是否存在，不打印变量值。

## 可选开启图片自动拦截

部署完成后，如果我明确要求开启粘贴图片自动拦截，请运行：

```powershell
python .\install.py --enable-image-proxy --upstream-base-url http://127.0.0.1:57321
```

开启前请先提醒我：这会修改 Codex 的 `base_url`，但 CodexLens 会备份配置并保存原 `base_url` 以便关闭时恢复。
