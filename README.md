# CodexLens

CodexLens 是一个面向科研场景的 Codex 输入透镜。它把图片、DOCX、PDF 等多模态材料转换为结构化文本，让接在 Codex 后面的纯文本模型也能理解论文图表和文档内容。

当前版本提供两条路径：

- MCP 工具：`analyze_img`、`read_docx`、`read_pdf`、`read_document`
- 可选 HTTP 代理：拦截 OpenAI 兼容请求里的 base64 图片，调用 Qwen 视觉模型分析后替换为文本，再转发到下游服务

## 使用 Codex 自动安装 CodexLens

如果你希望让 Codex 自动完成克隆、安装、配置和测试，可以复制 [Codex 自动部署提示词](docs/codex-deploy-prompt.md)。提示词已经包含当前 GitHub 仓库链接，用户只需要准备百炼 API Key。

## 状态

这是早期原型，适合个人科研工作流和小范围试用。公开部署前请先阅读 API Key 配置、安全说明和卸载说明。

## 目录

```text
.
├── main.py                 # 单入口：启动 MCP stdio，可选启动 HTTP proxy
├── mcp_server.py            # MCP JSON-RPC stdio 服务
├── install.py               # 安装、卸载、开关图片拦截
├── notifications.py         # Windows Toast 通知
├── proxy/                   # HTTP 图片拦截代理
├── tools/                   # 图片、DOCX、PDF 读取工具
├── docs/
│   ├── api-key-setup.md
│   ├── codex-deploy-prompt.md
│   ├── image-proxy-toggle.md
│   └── python-environment.md
└── tests/                   # 基础离线测试
```

## Python 环境

- Python 3.9 或更高版本
- 依赖：`openai`、`python-docx`、`pdfplumber`、`PyMuPDF`
- Windows 通知：`winotify`
- 详细说明见 [Python 环境要求](docs/python-environment.md)

安装依赖：

```powershell
python -m pip install -e .
```

## API Key

CodexLens 默认使用百炼兼容接口和 `qwen3.5-flash`：

- `CODEX_LENS_API_KEY`：必填，百炼 API Key
- `CODEX_LENS_BASE_URL`：默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`
- `CODEX_LENS_VISION_MODEL`：默认 `qwen3.5-flash`

完整步骤见 [百炼 API Key 配置指南](docs/api-key-setup.md)。

PowerShell 持久配置：

```powershell
[Environment]::SetEnvironmentVariable("CODEX_LENS_API_KEY", "你的API_KEY", "User")
```

设置后需要重启 Codex、PowerShell 或其他已经打开的程序。

## 安装到 Codex

推荐默认只启用 MCP，不开启粘贴图片自动拦截：

```powershell
python .\install.py --mcp-only
```

安装脚本会：

1. 备份 `~/.codex/config.toml`
2. 写入 `[mcp_servers.CodexLens]`
3. 给 MCP 启动参数添加 `--no-proxy`
4. 不修改 Codex `base_url`
5. 提示重启 Codex

如果你希望让 Codex 自动完成克隆、安装、配置和测试，可以复制 [Codex 自动部署提示词](docs/codex-deploy-prompt.md)。

## 图片自动拦截开关

图片自动拦截默认关闭。需要时显式开启：

```powershell
python .\install.py --enable-image-proxy --upstream-base-url http://127.0.0.1:57321
```

关闭图片自动拦截但保留 MCP：

```powershell
python .\install.py --disable-image-proxy
```

查看当前状态：

```powershell
python .\install.py --status
```

开启、关闭、以及 Codex 自动启动代理时，Windows 会尽量弹出右下角 Toast 通知。通知失败不会影响主功能。完整说明见 [图片自动拦截开关](docs/image-proxy-toggle.md)。

## 手动运行

同时运行 MCP 和代理：

```powershell
python .\main.py
```

只运行 MCP：

```powershell
python .\main.py --no-proxy
```

只运行代理：

```powershell
python .\main.py --proxy-only --upstream-base-url http://127.0.0.1:57321
```

## 卸载

```powershell
python .\install.py --uninstall
```

卸载会移除 `[mcp_servers.CodexLens]`，并恢复或移除 CodexLens 管理的 `base_url`。脚本会先备份 `config.toml`；如需恢复安装前的其他配置，请从备份文件恢复。

## MCP 工具

`analyze_img`

```json
{"file_path": "F:\\path\\figure.png"}
```

`read_docx`

```json
{"file_path": "F:\\path\\paper.docx", "max_images": 5}
```

`read_pdf`

```json
{"file_path": "F:\\path\\paper.pdf", "include_images": false}
```

`read_document`

```json
{"file_path": "F:\\path\\paper.pdf"}
```

## 测试

基础测试不联网：

```powershell
python -m unittest discover -s tests
```

语法检查：

```powershell
python -m compileall main.py mcp_server.py install.py notifications.py proxy tools tests
```

## 限制

- 图片代理会同步调用视觉模型，粘贴大图或多图时请求会变慢。
- DOCX/PDF 中的矢量图可能无法作为内嵌图片提取，只能读取文本部分。
- `install.py` 会修改 Codex `config.toml`，因此每次安装或卸载前都会自动备份。
- Windows Toast 通知受系统通知设置、勿扰模式和权限策略影响。

## 许可证

MIT License，见 [LICENSE](LICENSE)。
