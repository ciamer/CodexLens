import argparse
import json
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

from tools.analyze_img import DEFAULT_PROMPT, MODEL, analyze_image_base64


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


@dataclass
class ProxyConfig:
    upstream_base_url: str = "http://127.0.0.1:57321"
    timeout: float = 300.0
    vision_model: str = MODEL
    vision_prompt: str = DEFAULT_PROMPT
    vision_temperature: float = 0.3
    vision_max_tokens: int = 2048


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def extract_image_data(part: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    part_type = part.get("type")
    if part_type not in {"image_url", "input_image", "image"}:
        return None

    image_url = part.get("image_url") or part.get("url")
    if isinstance(image_url, dict):
        image_url = image_url.get("url")
    if isinstance(image_url, str) and image_url.startswith("data:"):
        mime = image_url.split(";", 1)[0].removeprefix("data:") or "image/png"
        return image_url, mime

    source = part.get("source")
    if isinstance(source, dict):
        data = source.get("data") or source.get("base64")
        mime = source.get("media_type") or source.get("mime_type") or "image/png"
        if isinstance(data, str):
            if data.startswith("data:"):
                return data, mime
            return data, mime

    data = part.get("data") or part.get("base64")
    if isinstance(data, str):
        mime = part.get("mime_type") or part.get("media_type") or "image/png"
        return data, mime

    return None


def replacement_part(original_type: str, text: str) -> Dict[str, str]:
    if original_type.startswith("input_"):
        return {"type": "input_text", "text": text}
    return {"type": "text", "text": text}


def rewrite_images(value: Any, config: ProxyConfig, counter: List[int]) -> Any:
    if isinstance(value, list):
        return [rewrite_images(item, config, counter) for item in value]
    if not isinstance(value, dict):
        return value

    image_payload = extract_image_data(value)
    if image_payload:
        image_data, mime_type = image_payload
        counter[0] += 1
        log(f"[CodexLens] analyzing pasted image #{counter[0]} ({mime_type})")
        try:
            description = analyze_image_base64(
                image_data,
                mime_type=mime_type,
                prompt=config.vision_prompt,
                model=config.vision_model,
                temperature=config.vision_temperature,
                max_tokens=config.vision_max_tokens,
            )
        except Exception as exc:
            description = f"图片分析失败：{exc}"
        return replacement_part(str(value.get("type", "")), f"[图片 {counter[0]} 分析结果]\n{description}")

    return {key: rewrite_images(item, config, counter) for key, item in value.items()}


def maybe_rewrite_json(body: bytes, content_type: str, config: ProxyConfig) -> Tuple[bytes, int]:
    if "json" not in content_type.lower():
        return body, 0
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return body, 0

    counter = [0]
    rewritten = rewrite_images(payload, config, counter)
    if counter[0] == 0:
        return body, 0
    return json.dumps(rewritten, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), counter[0]


def upstream_url(base_url: str, request_path: str) -> str:
    parsed_base = urllib.parse.urlsplit(base_url.rstrip("/"))
    parsed_path = urllib.parse.urlsplit(request_path)
    request_path_only = parsed_path.path if parsed_path.path.startswith("/") else "/" + parsed_path.path
    base_path = parsed_base.path.rstrip("/")
    if base_path and request_path_only != base_path and not request_path_only.startswith(base_path + "/"):
        path = base_path + "/" + request_path_only.lstrip("/")
    else:
        path = request_path_only
    return urllib.parse.urlunsplit(
        (
            parsed_base.scheme,
            parsed_base.netloc,
            path,
            parsed_path.query,
            "",
        )
    )


class CodexLensProxyHandler(BaseHTTPRequestHandler):
    server_version = "CodexLens-proxy/0.1"
    config: ProxyConfig

    def log_message(self, fmt: str, *args: Any) -> None:
        log("[proxy] " + fmt % args)

    def do_GET(self) -> None:
        self.forward()

    def do_POST(self) -> None:
        self.forward()

    def do_PUT(self) -> None:
        self.forward()

    def do_PATCH(self) -> None:
        self.forward()

    def do_DELETE(self) -> None:
        self.forward()

    def do_OPTIONS(self) -> None:
        self.forward()

    def request_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or "0")
        return self.rfile.read(length) if length else b""

    def outbound_headers(self, body: bytes) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        for key, value in self.headers.items():
            if key.lower() in HOP_BY_HOP_HEADERS or key.lower() == "host":
                continue
            if key.lower() == "content-length":
                continue
            headers[key] = value
        if body:
            headers["Content-Length"] = str(len(body))
        return headers

    def forward(self) -> None:
        body = self.request_body()
        content_type = self.headers.get("Content-Type", "")
        if body and self.command.upper() == "POST":
            body, image_count = maybe_rewrite_json(body, content_type, self.config)
            if image_count:
                log(f"[CodexLens] replaced {image_count} image part(s) with text")

        url = upstream_url(self.config.upstream_base_url, self.path)
        request = urllib.request.Request(
            url,
            data=body if body or self.command.upper() in {"POST", "PUT", "PATCH"} else None,
            headers=self.outbound_headers(body),
            method=self.command,
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                self.send_response(response.status, response.reason)
                for key, value in response.headers.items():
                    if key.lower() in HOP_BY_HOP_HEADERS:
                        continue
                    self.send_header(key, value)
                self.end_headers()
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code, exc.reason)
            for key, value in exc.headers.items():
                if key.lower() in HOP_BY_HOP_HEADERS:
                    continue
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(exc.read())
        except Exception as exc:
            payload = json.dumps({"error": f"CodexLens proxy error: {exc}"}, ensure_ascii=False).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)


class CodexLensProxyServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, config: ProxyConfig):
        super().__init__(server_address, RequestHandlerClass)
        self.config = config
        RequestHandlerClass.config = config


def make_server(host: str, port: int, config: ProxyConfig) -> CodexLensProxyServer:
    return CodexLensProxyServer((host, port), CodexLensProxyHandler, config)


def start_proxy_in_thread(host: str, port: int, config: ProxyConfig) -> Tuple[CodexLensProxyServer, threading.Thread]:
    server = make_server(host, port, config)
    thread = threading.Thread(target=server.serve_forever, name="CodexLens-proxy", daemon=True)
    thread.start()
    log(f"[CodexLens] proxy listening on http://{host}:{port}, upstream {config.upstream_base_url}")
    return server, thread


def run_proxy(host: str, port: int, config: ProxyConfig) -> None:
    server = make_server(host, port, config)
    log(f"[CodexLens] proxy listening on http://{host}:{port}, upstream {config.upstream_base_url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodexLens HTTP image rewriting proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=57320)
    parser.add_argument("--upstream-base-url", default="http://127.0.0.1:57321")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--vision-model", default=MODEL)
    parser.add_argument("--vision-temperature", type=float, default=0.3)
    parser.add_argument("--vision-max-tokens", type=int, default=2048)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    run_proxy(
        args.host,
        args.port,
        ProxyConfig(
            upstream_base_url=args.upstream_base_url,
            timeout=args.timeout,
            vision_model=args.vision_model,
            vision_temperature=args.vision_temperature,
            vision_max_tokens=args.vision_max_tokens,
        ),
    )


if __name__ == "__main__":
    main()
