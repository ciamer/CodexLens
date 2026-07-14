import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from notifications import notify


APP_NAME = "CodexLens"
MCP_TABLE_NAME = "CodexLens"
DEFAULT_PROXY_BASE_URL = "http://127.0.0.1:57320/v1"
DEFAULT_UPSTREAM_BASE_URL = "http://127.0.0.1:57321"
MCP_BLOCK_RE = re.compile(r"(?ms)^\[mcp_servers\.(?:CodexLens|codex_lens|codex_turbo)\]\n.*?(?=^\[|\Z)")
BASE_URL_RE = re.compile(r'(?m)^base_url\s*=\s*(["\'])(?P<value>.*?)\1\s*$')


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def default_config_path() -> Path:
    codex_home = os.getenv("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "config.toml"
    return Path.home() / ".codex" / "config.toml"


def default_state_path(config_path: Path) -> Path:
    return config_path.parent / "codex-lens-state.json"


def server_block(python_path: str, main_path: str, upstream_base_url: str, image_proxy_enabled: bool) -> str:
    args = [
        main_path,
        "--upstream-base-url",
        upstream_base_url,
    ]
    if not image_proxy_enabled:
        args.append("--no-proxy")

    lines = [
        f"[mcp_servers.{MCP_TABLE_NAME}]",
        f"command = {toml_string(python_path)}",
        "args = [",
    ]
    lines.extend(f"  {toml_string(arg)}," for arg in args)
    lines.extend(
        [
            "]",
            "startup_timeout_sec = 30",
            "",
        ]
    )
    return "\n".join(lines)


def upsert_block(text: str, block: str) -> str:
    if MCP_BLOCK_RE.search(text):
        text = MCP_BLOCK_RE.sub("", text).rstrip()
        if text:
            return text + "\n\n" + block
        return block
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block


def get_base_url(text: str) -> Tuple[bool, Optional[str]]:
    match = BASE_URL_RE.search(text)
    if not match:
        return False, None
    return True, match.group("value")


def upsert_base_url(text: str, proxy_base_url: str) -> str:
    line = f"base_url = {toml_string(proxy_base_url)}"
    if BASE_URL_RE.search(text):
        return BASE_URL_RE.sub(line, text)
    return line + "\n" + text


def remove_base_url_if_value(text: str, value: str) -> str:
    def replace(match: re.Match) -> str:
        return "" if match.group("value") == value else match.group(0)

    return BASE_URL_RE.sub(replace, text)


def set_base_url(text: str, value: str) -> str:
    line = f"base_url = {toml_string(value)}"
    if BASE_URL_RE.search(text):
        return BASE_URL_RE.sub(line, text)
    return line + "\n" + text


def normalize_blank_lines(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text + "\n" if text else ""


def backup_config(config_path: Path) -> None:
    if not config_path.exists():
        return
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_suffix(config_path.suffix + f".bak-{stamp}")
    shutil.copy2(config_path, backup)
    print(f"[备份] {backup}")


def read_text(config_path: Path) -> str:
    if not config_path.exists():
        return ""
    return config_path.read_text(encoding="utf-8")


def write_text(config_path: Path, text: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(text, encoding="utf-8")


def load_state(state_path: Path) -> Dict[str, Any]:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state_path: Path, state: Dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remove_state(state_path: Path) -> None:
    if state_path.exists():
        state_path.unlink()


def build_state(
    existing_state: Dict[str, Any],
    had_base_url: bool,
    current_base_url: Optional[str],
    proxy_base_url: str,
    upstream_base_url: str,
) -> Dict[str, Any]:
    state = dict(existing_state)
    if current_base_url != proxy_base_url:
        state["previous_base_url"] = current_base_url
        state["had_previous_base_url"] = had_base_url
    state["proxy_base_url"] = proxy_base_url
    state["upstream_base_url"] = upstream_base_url
    return state


def install_mcp(
    config_path: Path,
    python_path: str,
    main_path: str,
    upstream_base_url: str,
    image_proxy_enabled: bool,
) -> None:
    text = read_text(config_path)
    block = server_block(python_path, main_path, upstream_base_url, image_proxy_enabled=image_proxy_enabled)
    text = upsert_block(text, block)
    write_text(config_path, normalize_blank_lines(text))


def install_mcp_only(
    config_path: Path,
    state_path: Path,
    python_path: str,
    main_path: str,
    proxy_base_url: str,
    upstream_base_url: str,
) -> None:
    backup_config(config_path)
    text = read_text(config_path)
    state = load_state(state_path)
    _, current_base_url = get_base_url(text)
    if current_base_url == proxy_base_url:
        if state.get("had_previous_base_url") and state.get("previous_base_url"):
            text = set_base_url(text, str(state["previous_base_url"]))
        else:
            text = remove_base_url_if_value(text, proxy_base_url)
        remove_state(state_path)

    block = server_block(python_path, main_path, upstream_base_url, image_proxy_enabled=False)
    text = upsert_block(text, block)
    write_text(config_path, normalize_blank_lines(text))
    print(f"[完成] 已启用 {APP_NAME} MCP，图片自动拦截未开启: {config_path}")
    print("[提示] 重启 Codex 后生效。")
    notify(APP_NAME, "MCP 已启用，图片自动拦截未开启。重启 Codex 后生效。")


def enable_image_proxy(
    config_path: Path,
    state_path: Path,
    python_path: str,
    main_path: str,
    proxy_base_url: str,
    upstream_base_url: str,
) -> None:
    backup_config(config_path)
    text = read_text(config_path)
    had_base_url, current_base_url = get_base_url(text)
    state = build_state(load_state(state_path), had_base_url, current_base_url, proxy_base_url, upstream_base_url)

    text = upsert_base_url(text, proxy_base_url)
    block = server_block(python_path, main_path, upstream_base_url, image_proxy_enabled=True)
    text = upsert_block(text, block)
    write_text(config_path, normalize_blank_lines(text))
    save_state(state_path, state)

    print(f"[完成] 已开启图片自动拦截: {proxy_base_url}")
    print("[提示] 重启 Codex 后生效。")
    notify(APP_NAME, "图片自动拦截已开启。重启 Codex 后生效。")


def disable_image_proxy(
    config_path: Path,
    state_path: Path,
    python_path: str,
    main_path: str,
    proxy_base_url: str,
    upstream_base_url: str,
) -> None:
    backup_config(config_path)
    text = read_text(config_path)
    state = load_state(state_path)

    if state.get("had_previous_base_url") and state.get("previous_base_url"):
        text = set_base_url(text, str(state["previous_base_url"]))
        base_url_message = f"已恢复原 base_url: {state['previous_base_url']}"
    else:
        text = remove_base_url_if_value(text, proxy_base_url)
        base_url_message = "已移除 CodexLens 代理 base_url"

    block = server_block(python_path, main_path, upstream_base_url, image_proxy_enabled=False)
    text = upsert_block(text, block)
    write_text(config_path, normalize_blank_lines(text))
    remove_state(state_path)

    print("[完成] 已关闭图片自动拦截，MCP 工具仍保留。")
    print(f"[信息] {base_url_message}")
    print("[提示] 重启 Codex 后生效。")
    notify(APP_NAME, "图片自动拦截已关闭。Word/PDF MCP 工具仍可使用。")


def uninstall(config_path: Path, state_path: Path, proxy_base_url: str) -> None:
    if not config_path.exists():
        print(f"[跳过] Codex 配置不存在: {config_path}")
        remove_state(state_path)
        return

    backup_config(config_path)
    text = read_text(config_path)
    state = load_state(state_path)
    text = MCP_BLOCK_RE.sub("", text)

    if state.get("had_previous_base_url") and state.get("previous_base_url"):
        text = set_base_url(text, str(state["previous_base_url"]))
    else:
        text = remove_base_url_if_value(text, proxy_base_url)

    write_text(config_path, normalize_blank_lines(text))
    remove_state(state_path)
    print(f"[完成] 已移除 {APP_NAME} 配置: {config_path}")
    print("[提示] 如需恢复原配置，请使用刚生成的备份文件。")
    notify(APP_NAME, "已卸载。重启 Codex 后生效。")


def status(config_path: Path, state_path: Path, proxy_base_url: str) -> None:
    text = read_text(config_path)
    state = load_state(state_path)
    mcp_block = MCP_BLOCK_RE.search(text)
    block_text = mcp_block.group(0) if mcp_block else ""
    has_mcp = bool(mcp_block) and not bool(re.search(r"(?m)^enabled\s*=\s*false\s*$", block_text))
    has_no_proxy = "--no-proxy" in block_text
    had_base_url, current_base_url = get_base_url(text)
    image_proxy_enabled = current_base_url == proxy_base_url and has_mcp and not has_no_proxy

    print(f"{APP_NAME} 状态")
    print(f"- MCP: {'enabled' if has_mcp else 'disabled'}")
    print(f"- Image proxy: {'enabled' if image_proxy_enabled else 'disabled'}")
    print(f"- Codex base_url: {current_base_url if had_base_url else '(not set)'}")
    print(f"- State file: {state_path if state else '(not present)'}")
    if state:
        previous = state.get("previous_base_url")
        print(f"- Previous base_url: {previous if previous else '(not set)'}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Install and manage {APP_NAME} in Codex config.toml")
    parser.add_argument("--config", type=Path, default=default_config_path(), help="Codex config.toml 路径")
    parser.add_argument("--state", type=Path, default=None, help="状态文件路径，默认与 Codex config.toml 同目录")
    parser.add_argument("--python", default=sys.executable, help=f"用于启动 {APP_NAME} 的 Python")
    parser.add_argument("--main", default=str(Path(__file__).resolve().parent / "main.py"))
    parser.add_argument("--proxy-base-url", default=DEFAULT_PROXY_BASE_URL)
    parser.add_argument("--upstream-base-url", default=DEFAULT_UPSTREAM_BASE_URL)

    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--mcp-only", action="store_true", help="只启用 MCP，并关闭图片自动拦截")
    actions.add_argument("--enable-image-proxy", action="store_true", help="开启粘贴图片自动拦截")
    actions.add_argument("--disable-image-proxy", action="store_true", help="关闭图片自动拦截，保留 MCP")
    actions.add_argument("--status", action="store_true", help="显示当前安装状态")
    actions.add_argument("--uninstall", action="store_true", help=f"移除 {APP_NAME} MCP 配置和代理 base_url")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    state_path = args.state or default_state_path(args.config)

    if args.status:
        status(config_path=args.config, state_path=state_path, proxy_base_url=args.proxy_base_url)
        return
    if args.uninstall:
        uninstall(config_path=args.config, state_path=state_path, proxy_base_url=args.proxy_base_url)
        return
    if args.enable_image_proxy:
        enable_image_proxy(
            config_path=args.config,
            state_path=state_path,
            python_path=args.python,
            main_path=args.main,
            proxy_base_url=args.proxy_base_url,
            upstream_base_url=args.upstream_base_url,
        )
        return
    if args.disable_image_proxy:
        disable_image_proxy(
            config_path=args.config,
            state_path=state_path,
            python_path=args.python,
            main_path=args.main,
            proxy_base_url=args.proxy_base_url,
            upstream_base_url=args.upstream_base_url,
        )
        return

    enable_image_proxy(
        config_path=args.config,
        state_path=state_path,
        python_path=args.python,
        main_path=args.main,
        proxy_base_url=args.proxy_base_url,
        upstream_base_url=args.upstream_base_url,
    )


if __name__ == "__main__":
    main()
