# Changelog

## Unreleased

- Renamed visible MCP/server display name to `CodexLens`.
- Added `--mcp-only`, `--enable-image-proxy`, `--disable-image-proxy`, and `--status`.
- Made MCP-only the recommended default install mode.
- Added stateful restore of the previous Codex `base_url` when disabling image proxy.
- Added best-effort Windows Toast notifications for image proxy changes and startup.

## 0.1.0

- Initial CodexLens prototype.
- Added MCP tools: `analyze_img`, `read_docx`, `read_pdf`, `read_document`.
- Added HTTP proxy for replacing pasted image payloads with vision-model descriptions.
- Added Codex install/uninstall script.
- Added API Key setup guide and deployment prompt.
