import argparse
import sys

from mcp_server import run_stdio
from proxy.server import ProxyConfig, run_proxy, start_proxy_in_thread


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="codex-lens: MCP tools + image rewriting proxy")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP proxy listen host")
    parser.add_argument("--port", type=int, default=57320, help="HTTP proxy listen port")
    parser.add_argument(
        "--upstream-base-url",
        default="http://127.0.0.1:57321",
        help="Downstream OpenAI-compatible service base URL",
    )
    parser.add_argument("--timeout", type=float, default=300.0, help="Upstream request timeout seconds")
    parser.add_argument("--no-proxy", action="store_true", help="Only run MCP stdio server")
    parser.add_argument("--proxy-only", action="store_true", help="Only run HTTP proxy")
    parser.add_argument("--vision-model", default=None, help="Vision model name for proxy image rewriting")
    parser.add_argument("--vision-temperature", type=float, default=0.3)
    parser.add_argument("--vision-max-tokens", type=int, default=2048)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    config_kwargs = {
        "upstream_base_url": args.upstream_base_url,
        "timeout": args.timeout,
        "vision_temperature": args.vision_temperature,
        "vision_max_tokens": args.vision_max_tokens,
    }
    if args.vision_model:
        config_kwargs["vision_model"] = args.vision_model
    config = ProxyConfig(**config_kwargs)

    if args.proxy_only:
        run_proxy(args.host, args.port, config)
        return

    if not args.no_proxy:
        try:
            start_proxy_in_thread(args.host, args.port, config)
        except OSError as exc:
            print(f"[codex-lens] 代理启动失败: {exc}", file=sys.stderr, flush=True)
            raise

    run_stdio()


if __name__ == "__main__":
    main()
