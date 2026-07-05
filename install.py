import argparse
import datetime as dt
import os
import re
import shutil
import sys
from pathlib import Path


DEFAULT_PROXY_BASE_URL = "http://127.0.0.1:57320/v1"
DEFAULT_UPSTREAM_BASE_URL = "http://127.0.0.1:57321"
MCP_BLOCK_RE = re.compile(r"(?ms)^\[mcp_servers\.(?:codex_turbo|codex_lens)\]\n.*?(?=^\[|\Z)")


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def default_config_path() -> Path:
    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "config.toml"
    return Path.home() / ".codex" / "config.toml"


def server_block(python_path: str, main_path: str, upstream_base_url: str) -> str:
    return "\n".join(
        [
            "[mcp_servers.codex_lens]",
            f"command = {toml_string(python_path)}",
            "args = [",
            f"  {toml_string(main_path)},",
            '  "--upstream-base-url",',
            f"  {toml_string(upstream_base_url)},",
            "]",
            "startup_timeout_sec = 30",
            "",
        ]
    )


def upsert_block(text: str, block: str) -> str:
    if MCP_BLOCK_RE.search(text):
        text = MCP_BLOCK_RE.sub("", text).rstrip()
        if text:
            return text + "\n\n" + block
        return block
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block


def upsert_base_url(text: str, proxy_base_url: str) -> str:
    line = f"base_url = {toml_string(proxy_base_url)}"
    pattern = re.compile(r'(?m)^base_url\s*=\s*["\'].*?["\']\s*$')
    if pattern.search(text):
        return pattern.sub(line, text)
    return line + "\n" + text


def backup_config(config_path: Path) -> None:
    if not config_path.exists():
        return
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_suffix(config_path.suffix + f".bak-{stamp}")
    shutil.copy2(config_path, backup)
    print(f"[备份] {backup}")


def install(config_path: Path, python_path: str, main_path: str, proxy_base_url: str, upstream_base_url: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        backup_config(config_path)
        text = config_path.read_text(encoding="utf-8")
    else:
        text = ""

    text = upsert_base_url(text, proxy_base_url)
    text = upsert_block(text, server_block(python_path, main_path, upstream_base_url))
    config_path.write_text(text, encoding="utf-8")
    print(f"[完成] 已更新 Codex 配置: {config_path}")
    print("[提示] 重启 Codex 后生效。")


def remove_proxy_base_url(text: str, proxy_base_url: str) -> str:
    pattern = re.compile(r'(?m)^base_url\s*=\s*(["\'])(?P<value>.*?)\1\s*$')

    def replace(match: re.Match) -> str:
        return "" if match.group("value") == proxy_base_url else match.group(0)

    return pattern.sub(replace, text)


def uninstall(config_path: Path, proxy_base_url: str) -> None:
    if not config_path.exists():
        print(f"[跳过] Codex 配置不存在: {config_path}")
        return

    backup_config(config_path)
    text = config_path.read_text(encoding="utf-8")
    text = MCP_BLOCK_RE.sub("", text)
    text = remove_proxy_base_url(text, proxy_base_url)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    config_path.write_text(text, encoding="utf-8")
    print(f"[完成] 已移除 codex-lens 配置: {config_path}")
    print("[提示] 如需恢复原 base_url，请使用刚刚生成的备份文件。")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install codex-lens into Codex config.toml")
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--python", default=sys.executable, help="用于启动 codex-lens 的 Python")
    parser.add_argument("--main", default=str(Path(__file__).resolve().parent / "main.py"))
    parser.add_argument("--proxy-base-url", default=DEFAULT_PROXY_BASE_URL)
    parser.add_argument("--upstream-base-url", default=DEFAULT_UPSTREAM_BASE_URL)
    parser.add_argument("--uninstall", action="store_true", help="移除 codex-lens MCP 配置和代理 base_url")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.uninstall:
        uninstall(config_path=args.config, proxy_base_url=args.proxy_base_url)
        return

    install(
        config_path=args.config,
        python_path=args.python,
        main_path=args.main,
        proxy_base_url=args.proxy_base_url,
        upstream_base_url=args.upstream_base_url,
    )


if __name__ == "__main__":
    main()
