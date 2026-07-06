# CodexLens — 项目总结文档

## 一、项目定位

**CodexLens 是一个面向科研场景的 Codex 输入透镜。**

它不是写作工具，而是理解工具。专注于在信息到达 LLM 之前，完成多模态内容的提取、分析和结构化，让纯文本模型也能处理图片、文档等复杂输入。

> Documents 插件是"输出的笔"，CodexLens 是"输入的眼"。

---

## 二、目标用户

**使用 Codex 桌面版 + 第三方纯文本模型（如 DeepSeek）进行科研工作的用户。**

具体画像：
- 研究者/学生，日常需要阅读论文、分析图表
- 使用 codex++ 等工具将 Codex 接入第三方 API
- 希望粘贴图片后自动得到分析结果，而非手动传文件路径
- 希望 LLM 能直接理解文档内容，而非只能处理文本

---

## 三、解决的核心问题

| 场景 | 问题 | CodexLens 方案 |
|------|------|-----------------|
| 粘贴图片到聊天框 | 纯文本模型无法理解图片内容 | 代理拦截 → Qwen 分析 → 替换为文本 |
| "帮我分析这张 Figure" | 无现成工具 | MCP 工具：analyze_img |
| "帮我读这篇论文（docx）" | 需手动写 Python 代码提取 | MCP 工具：read_docx |
| "帮我读这份 PDF" | 同上 | MCP 工具：read_pdf |
| "这个表格里有什么数据" | docx 表格需要专门提取 | MCP 工具：read_docx（含表格提取） |

---

## 四、与已有插件的关系

### Documents 插件（OpenAI 官方）
- **定位**：写作工具——创建、编辑、排版、渲染 DOCX
- **输出**：格式精美的 .docx 文件
- **依赖**：python-docx + LibreOffice
- **局限**：假设 agent 在本地全模态运行，连第三方 API 时体验受限

### PDF 插件（OpenAI 官方）
- **定位**：PDF 创建和排版验证
- **局限**：以渲染检查为主，无 AI 图片分析能力

### CodexLens
- **定位**：科研输入透镜——从文档/图片中提取内容给模型理解
- **输出**：结构化纯文本
- **关系**：**互补，不冲突，可并存**

---

## 五、系统架构

### 总览

```
┌─ User's Machine ──────────────────────────────────────────────┐
│                                                                │
│  Codex 桌面版                                                   │
│    │                                                           │
│    ├─ config.toml: base_url → proxy:57320                      │
│    ├─ config.toml: mcp_server → CodexLens 进程                 │
│    │                                                           │
│    ▼                                                           │
│  ┌─────────────────────────────────────┐                      │
│  │  CodexLens (单一 MCP 进程)          │                      │
│  │  ┌──────────────┐  ┌────────────┐   │                      │
│  │  │ MCP Stdio    │  │ HTTP Proxy │   │                      │
│  │  │ 接口         │  │ :57320     │   │                      │
│  │  │              │  │            │   │                      │
│  │  │ Tools:       │  │ 拦截包含   │   │                      │
│  │  │ · read_docx  │  │ 图片的请求 │   │                      │
│  │  │ · read_pdf   │  │ → Qwen 分析│   │                      │
│  │  │ · analyze_img│  │ → 替换为   │   │                      │
│  │  └──────────────┘  │   文本     │   │                      │
│  │                     │ → 转发下游  │   │                      │
│  │                     └────────────┘   │                      │
│  └──────────┬──────────────────────────┘                      │
│             │                                                  │
│             ├───── MCP 请求 (对话中说"读这个文件")              │
│             └───── HTTP 请求 (粘贴图片时自动走)                │
│                                                                │
│             ▼                                                  │
│  ┌──────────────┐                                             │
│  │ codex++      │  →  DeepSeek 后端                           │
│  │ :57321       │                                             │
│  └──────────────┘                                             │
└────────────────────────────────────────────────────────────────┘
```

### 两种通信路径

**路径 A：用户主动请求（MCP）**
用户说"读这个 docx" → Codex 通过 MCP 协议调用 CodexLens 的 read_docx 工具 → 返回文档内容 → 模型理解内容

**路径 B：用户粘贴图片（Proxy）**
用户粘贴图片 → Codex 发 API 请求到 proxy:57320 → proxy 检测到 base64 图片 → 调用 Qwen 分析 → 替换为文本 → 转发给 codex++:57321 → DeepSeek 收到纯文本

---

## 六、模块设计

### 6.1 HTTP Proxy（图片拦截层）

| 属性 | 说明 |
|------|------|
| 技术 | Python http.server（stdlib，零依赖） |
| 端口 | 57320 |
| 协议 | 完全透明的 HTTP 反向代理 |
| 核心逻辑 | 截获 POST 请求 → 解析 input 数组 → 找到 type=image 项 → Qwen API 分析 → 替换为文本 → 转发给下游 |
| 流式支持 | 透传 SSE（streaming）响应 |
| 配置 | 目标转发地址（默认 127.0.0.1:57321） |

### 6.2 MCP Stdio 接口（工具层）

| 工具 | 输入 | 输出 | 依赖 |
|------|------|------|------|
| read_docx | file_path: str | 正文、表格(CSV)、批注、脚注、页眉页脚 | python-docx（Codex 自带） |
| read_pdf | file_path: str | 文字内容 + 页面元数据 | pdfplumber（Codex 自带） |
| analyze_img | file_path 或 base64 | AI 描述的文本（趋势、标注、子图等） | Qwen 多模态 API |

### 6.3 Qwen API 层

所有视觉理解任务统一走千问视觉 API，用户只需配置一次 API Key。

```
analyze_img  ─┐
Proxy 拦截图片 ─┼──→ Qwen-VL API → 文字描述
               │
               └─ Key 管理：config 文件或环境变量
```

---

## 七、部署方案
**当前默认安装 MCP 工具，图片自动拦截需要用户显式开启。**
### 核心思路

利用 Codex 的 MCP 服务器机制，让 Codex **自动管理进程生命周期**：

```
config.toml 中注册：

[mcp_servers.CodexLens]
command = 'Codex 自带 python.exe'
args = ["main.py", "--no-proxy"]
startup_timeout_sec = 30
```

- Codex 启动 → 自动拉起 main.py
- Codex 关闭 → 自动杀掉进程
- 无需用户手动操作
- 跨平台（Win/Mac/Linux）：纯 Python

### 用户安装步骤

```bash
# 1. 克隆
git clone https://github.com/ciamer/codex-lens

# 2. 默认只安装 MCP 工具
python install.py --mcp-only

# 3. 重启 Codex
```

install.py 自动完成：
1. 找到 Codex 的 config.toml
2. 添加 `[mcp_servers.CodexLens]` 条目（指向 Codex 自带的 Python）
3. 默认添加 `--no-proxy`，不修改 `base_url`
4. 提示用户重启 Codex

如需粘贴图片自动拦截，再运行：

```bash
python install.py --enable-image-proxy --upstream-base-url http://127.0.0.1:57321
```

### 不依赖外部 Python 环境

所有三方库（python-docx、pdfplumber、Pillow）均由 **Codex 自带的 Python 运行时** 提供，项目本身只需 stdlib。

---

## 八、项目文件结构

```
codex-lens/
│
├── main.py                 # 入口：同时启动 MCP Stdio + HTTP Proxy
│
├── tools/
│   ├── __init__.py
│   ├── read_docx.py        # docx 内容提取（python-docx）
│   ├── read_pdf.py         # PDF 文字提取（pdfplumber）
│   └── analyze_img.py      # 图片分析（Qwen VL API + PIL）
│
├── proxy/
│   ├── __init__.py
│   └── server.py           # HTTP 拦截代理（stdlib，零依赖）
│
├── install.py              # 一键安装脚本
│
├── pyproject.toml           # 仅用于 pip install -e .（可选，非必须）
│
└── README.md               # 使用说明 + 开源信息
```

---

## 九、项目边界（不做的事）

| 不做 | 原因 |
|------|------|
| 创建/编辑 DOCX 文件 | Documents 插件已覆盖，不重复造轮子 |
| PDF 排版/渲染 | PDF 插件已覆盖 |
| docx/PDF 格式转换 | 不是科研理解的核心需求 |
| 文档格式美化 | 不是科研理解的核心需求 |
| 图片编辑/生成 | 定位是理解而非创造 |

---

## 十、开源策略

- 纯 Python 项目，MIT 许可证
- 唯一的外部依赖是用户的 Qwen API Key
- 所有底层库由 Codex 运行时提供
- GitHub Release 时可选提供 PyInstaller 编译的单 exe（非必须）
- README 明确注明：需要与 Documents 插件搭配使用以获得完整体验

---

## 十一、一句话总结

> **CodexLens 是 Codex × 纯文本模型场景下的科研输入透镜，用 MCP 工具 + HTTP 代理填补了官方插件在"理解文档内容"和"拦截粘贴图片"上的空白，与 Documents/PDF 插件互补共存。**
