# 百炼 API Key 配置指南

CodexLens 需要一个百炼 API Key 来调用视觉模型。简单说，CodexLens 负责把图片、Word 或 PDF 里的图交给模型看，API Key 用来证明这是你的百炼账号在发起调用。

如果你只是想完成安装，先在百炼控制台创建一个 Key，然后回到 [Codex 自动部署提示词](codex-deploy-prompt.md)。默认提示词可以让 Codex 帮你设置；不想把 Key 发到对话时，也可以按提示词页面里的两步法自己设置。

当前项目默认使用：

```text
CODEX_LENS_API_KEY
CODEX_LENS_VISION_MODEL=qwen3.5-flash
```

`CODEX_LENS_API_KEY` 是本项目专用的环境变量名。阿里云官方文档常用 `DASHSCOPE_API_KEY` 作为示例变量名，但 CodexLens 不直接使用它，避免和用户机器上的其他百炼项目混在一起。

## Key 应该放在哪里

推荐放在 **Windows 用户环境变量**：

- 不放进 `Path`
- 不写进 Python 文件
- 不写进 `config.toml`
- 不写进 README、Word、飞书文档正文
- 不提交到 Git

用户变量不需要管理员权限，适合普通个人部署。系统变量只适合多用户共享机器、Windows 服务或系统级后台进程，CodexLens 一般用不到。

## 在百炼控制台获取 API Key

1. 打开 [阿里云百炼控制台](https://bailian.console.aliyun.com/)。
2. 登录阿里云账号，并确认已经开通百炼服务。
3. 在页面右上角选择地域，通常选择 **华北 2（北京）**。
4. 进入 **API Key** 页面。
5. 点击 **创建 API Key**。
6. 业务空间一般选择默认业务空间。
7. 描述建议填写 `CodexLens`，方便以后识别用途。
8. 权限可以先选择 **全部**；如果后续要做更细的成本和权限控制，再改成自定义模型权限。
9. 创建成功后，立即复制 API Key 并妥善保存。

注意：百炼新版 API Key 通常只在创建弹窗里显示一次完整明文。关闭弹窗后可能无法再次查看完整 Key，丢失时需要重置或重新创建。

## 关于免费 token

百炼控制台可能会为部分模型或新用户提供免费额度。`qwen3.5-flash` 适合作为 CodexLens 的默认轻量视觉分析模型。

免费额度会受账号、地域、活动和模型版本影响，项目不承诺固定额度。部署时请以百炼控制台的实际额度页面为准。

## 配置到 Windows 用户环境变量

打开 PowerShell，执行：

```powershell
[Environment]::SetEnvironmentVariable("CODEX_LENS_API_KEY", "你的API_KEY", "User")
```

如果要显式指定模型：

```powershell
[Environment]::SetEnvironmentVariable("CODEX_LENS_VISION_MODEL", "qwen3.5-flash", "User")
```

如果以后换成其他百炼兼容地址，也可以设置：

```powershell
[Environment]::SetEnvironmentVariable("CODEX_LENS_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1", "User")
```

设置后必须重启 Codex、PowerShell、IDE 或其他已经打开的程序。已经运行的进程不会自动拿到新的用户环境变量。

## 检查是否配置成功

不要把 Key 打印出来。推荐只检查变量是否存在：

```powershell
[bool][Environment]::GetEnvironmentVariable("CODEX_LENS_API_KEY", "User")
```

如果返回 `True`，说明用户环境变量已经写入。

新开一个 PowerShell 后，也可以检查当前进程是否读到了变量：

```powershell
[bool]$env:CODEX_LENS_API_KEY
```

## 让 Codex 帮你配置

更安全的方式是用户自己在 PowerShell 输入 Key。若确实想让 Codex 代为设置，需要知道：你发给 Codex 的 Key 会进入当前对话上下文。确认能接受后，可以这样对 Codex 说：

```text
请把下面这个百炼 API Key 设置为 Windows 用户环境变量 CODEX_LENS_API_KEY。
只使用 PowerShell 的 [Environment]::SetEnvironmentVariable(..., "User")。
不要把 Key 写入仓库文件、README、config.toml、日志或命令输出。
设置完成后只告诉我是否成功，并提醒我重启 Codex。

API Key:
<把你的 Key 粘贴在这里>
```

Codex 设置完成后，用户需要重启 Codex。重启后，Codex 自动启动的 CodexLens MCP 服务才能继承到新的环境变量。

## 常见问题

**为什么不用 `DASHSCOPE_API_KEY`？**

因为它是百炼/DashScope 的通用变量名。CodexLens 使用 `CODEX_LENS_API_KEY`，可以让用户一眼看出这个 Key 是给本项目用的，也避免和其他项目互相影响。

**可以把 Key 写进 Codex 的 `config.toml` 吗？**

不建议。`config.toml` 更适合保存服务命令、端口和 base URL。API Key 应放在用户环境变量里。

**设置用户变量后为什么测试还失败？**

通常是因为 Codex 或 PowerShell 是在设置变量之前启动的。关闭并重新打开 Codex，再试一次。

**Key 泄漏了怎么办？**

去百炼控制台禁用、重置或删除旧 Key，然后重新创建一个新的 Key，并重新设置 `CODEX_LENS_API_KEY`。

## 官方参考

- [阿里云百炼：获取 API Key](https://help.aliyun.com/zh/model-studio/get-api-key)
- [阿里云百炼：文本生成模型 API 参考](https://help.aliyun.com/zh/model-studio/qwen-api-reference/)
