# Python 环境要求

CodexLens 是纯 Python 项目，推荐使用 Python 3.9 或更高版本。

## 必需依赖

```text
openai
python-docx
pdfplumber
PyMuPDF
winotify; platform_system == "Windows"
```

安装方式：

```powershell
python -m pip install -e .
```

或者：

```powershell
python -m pip install -r requirements.txt
```

## 给 Codex 的选择规则

当 Codex 自动部署本项目时：

1. 优先使用用户明确指定的 Python 或 Conda 环境。
2. 如果用户没有指定，使用系统可用的 `python`。
3. 如果 `python` 不存在，再尝试 `py -3`。
4. 安装依赖时使用 `python -m pip install -e .`。
5. 运行命令前设置 `$env:PYTHONIOENCODING='utf-8';`，避免 Windows 中文输出乱码。

## 检查环境

```powershell
python --version
python -c "import openai, docx, fitz, pdfplumber; print('deps ok')"
```

## 离线基础测试

```powershell
python -m unittest discover -s tests
python -m compileall .
```

这些测试不调用百炼 API，也不会消耗 token。
