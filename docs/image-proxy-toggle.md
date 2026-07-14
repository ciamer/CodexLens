# 图片自动拦截开关

CodexLens 有两套独立能力：

```text
MCP 工具：read_docx / read_pdf / read_document / analyze_img
图片代理：自动拦截粘贴图片并转成文字描述
```

图片自动拦截由 Codex `base_url` 是否指向 CodexLens 代理决定。CodexLens MCP 现在提供状态、开启和关闭图片自动拦截工具，因此在 MCP 已启用的会话中，可以直接要求 Codex 开关它。

## 默认安装

默认安装会开启图片自动拦截：

```powershell
python .\install.py
```

安装后：

- Word/PDF 读取工具可用
- `analyze_img` 工具可用
- 粘贴图片会自动转成文字说明
- Codex `base_url` 会指向 CodexLens 代理

大多数用户不需要自己运行命令。直接对 Codex 说“请开启 CodexLens 的图片自动拦截”或“请关闭 CodexLens 的图片自动拦截，但保留 MCP 工具”即可。Codex 会调用当前 MCP 中的管理工具并提醒你重启。

已经安装过旧版本的用户不会被自动改动配置。若希望启用自动拦截，请明确对 Codex 说“请开启 CodexLens 的图片自动拦截”。

## 重新开启图片自动拦截

```powershell
python .\install.py --enable-image-proxy --upstream-base-url http://127.0.0.1:57321
```

开启后，安装脚本会：

1. 备份 Codex `config.toml`
2. 保存原来的 `base_url` 到 `codex-lens-state.json`
3. 设置 `base_url = "http://127.0.0.1:57320/v1"`
4. 修改 MCP 启动参数，让 `main.py` 启动图片代理
5. 发送 Windows Toast 通知

重启 Codex 后，粘贴图片会自动走：

```text
图片 -> CodexLens 代理 -> Qwen 视觉模型 -> 文字描述 -> 下游模型
```

## 关闭图片自动拦截但保留 MCP

```powershell
python .\install.py --disable-image-proxy
```

关闭后，安装脚本会：

1. 备份 Codex `config.toml`
2. 恢复原来的 `base_url`，或移除 CodexLens 代理的 `base_url`
3. 给 MCP 启动参数加上 `--no-proxy`
4. 删除 CodexLens 状态文件
5. 发送 Windows Toast 通知

## 查看状态

```powershell
python .\install.py --status
```

示例输出：

```text
CodexLens 状态
- MCP: enabled
- Image proxy: disabled
- Codex base_url: (not set)
- State file: (not present)
```

## 通知

Windows 上如果安装了 `winotify`，CodexLens 会尽量发送右下角 Toast 通知：

- 手动开启图片自动拦截
- 手动关闭图片自动拦截
- Codex 自动启动图片代理
- 图片代理启动失败

通知是 best effort。通知失败不会影响 MCP 或图片代理功能。

常见无法显示通知的原因：

- Windows 勿扰模式 / 专注助手开启
- 系统通知权限关闭
- Python 环境没有安装 `winotify`
- 企业策略禁用通知

## 完全卸载

```powershell
python .\install.py --uninstall
```

这会移除 MCP 配置，并恢复或移除 CodexLens 管理的 `base_url`。
