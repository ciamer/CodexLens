# Codex 工作指令

默认使用中文回答。

## 项目定位

codex-lens 是 Codex 的科研输入透镜，用 MCP 工具和 HTTP 代理把图片、DOCX、PDF 等多模态输入转换为结构化文本。

## Python 环境

- 推荐 Python：3.9 或更高版本。
- 本项目依赖：`openai`、`python-docx`、`pdfplumber`、`PyMuPDF`。
- 执行 Python 命令前建议设置：`$env:PYTHONIOENCODING='utf-8';`
- 如果用户有自己的 Conda/Python 环境，优先使用用户指定环境。
- 安装依赖使用：`python -m pip install -e .`

## API Key

- API Key 不写入代码、不写入 README、不写入 `config.toml`。
- 统一读取 Windows 用户环境变量：`CODEX_LENS_API_KEY`。
- 默认视觉模型：`CODEX_LENS_VISION_MODEL=qwen3.5-flash`。
- 默认接口地址：`CODEX_LENS_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`。
- 完整说明见 `docs/api-key-setup.md`。

## 常用命令

```powershell
$env:PYTHONIOENCODING='utf-8'; python -m compileall .
$env:PYTHONIOENCODING='utf-8'; python -m unittest discover -s tests
$env:PYTHONIOENCODING='utf-8'; python .\main.py --no-proxy
$env:PYTHONIOENCODING='utf-8'; python .\install.py --upstream-base-url http://127.0.0.1:57321
$env:PYTHONIOENCODING='utf-8'; python .\install.py --uninstall
```

## 部署原则

- 用户只应手动获取百炼 API Key。
- Codex 可以帮助设置 `CODEX_LENS_API_KEY` 用户环境变量，但不要把 Key 输出到日志或写入文件。
- 安装脚本会修改 Codex `config.toml`，运行前后都要提醒用户重启 Codex。
- 旧版脚本放在 `_local_legacy/`，该目录被 `.gitignore` 忽略，不应提交到 GitHub。
