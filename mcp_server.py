import json
import sys
import traceback
from typing import Any, Callable, Dict, Iterable, List, Optional

from tools import analyze_image, analyze_image_base64, read_docx, read_document, read_pdf
from tools.analyze_img import DEFAULT_PROMPT, MODEL


for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "codex-lens", "version": "0.1.0"}


def _schema_file_tool(description: str) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "本地文件路径"},
            "include_images": {
                "type": "boolean",
                "description": "是否提取并调用视觉模型分析文档图片",
                "default": True,
            },
            "max_images": {
                "type": "integer",
                "description": "最多分析多少张图片；不传表示不限制",
                "minimum": 1,
            },
            "min_kb": {
                "type": "number",
                "description": "过滤小于该大小 KB 的图片",
                "default": 3.0,
            },
            "image_prompt": {
                "type": "string",
                "description": "传给视觉模型的图片分析提示词",
            },
        },
        "required": ["file_path"],
        "additionalProperties": False,
        "description": description,
    }


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "analyze_img",
        "title": "Analyze Image",
        "description": "分析本地图片或 base64 图片，返回适合纯文本模型阅读的详细中文描述。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "本地图片路径"},
                "base64": {"type": "string", "description": "图片 base64，允许 data URL"},
                "mime_type": {"type": "string", "description": "base64 图片 MIME 类型", "default": "image/png"},
                "prompt": {"type": "string", "description": "自定义分析提示词", "default": DEFAULT_PROMPT},
                "model": {"type": "string", "description": "视觉模型名", "default": MODEL},
                "temperature": {"type": "number", "description": "生成温度", "default": 0.3},
                "max_tokens": {"type": "integer", "description": "最大输出 token 数", "default": 2048},
            },
            "anyOf": [{"required": ["file_path"]}, {"required": ["base64"]}],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_docx",
        "title": "Read DOCX",
        "description": "读取 Word 文档，提取正文、表格、页眉页脚、批注/脚注/尾注，并可分析内嵌图片。",
        "inputSchema": _schema_file_tool("DOCX 读取参数"),
    },
    {
        "name": "read_pdf",
        "title": "Read PDF",
        "description": "读取 PDF，提取每页文字，并可提取内嵌图片后调用视觉模型分析。",
        "inputSchema": _schema_file_tool("PDF 读取参数"),
    },
    {
        "name": "read_document",
        "title": "Read Document",
        "description": "根据后缀自动读取 .docx 或 .pdf 文件。",
        "inputSchema": _schema_file_tool("自动文档读取参数"),
    },
]


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def response(request_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        payload["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": payload}


def text_result(text: str, is_error: bool = False) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _bool_arg(args: Dict[str, Any], name: str, default: bool) -> bool:
    value = args.get(name, default)
    return bool(value)


def _doc_args(args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "file_path": args["file_path"],
        "use_image_analysis": _bool_arg(args, "include_images", True),
        "max_images": args.get("max_images"),
        "min_image_kb": float(args.get("min_kb", 3.0)),
        "image_prompt": args.get("image_prompt"),
    }


def call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "analyze_img":
        prompt = args.get("prompt") or DEFAULT_PROMPT
        model = args.get("model") or MODEL
        temperature = float(args.get("temperature", 0.3))
        max_tokens = int(args.get("max_tokens", 2048))
        if args.get("file_path"):
            return text_result(
                analyze_image(
                    args["file_path"],
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        if args.get("base64"):
            return text_result(
                analyze_image_base64(
                    args["base64"],
                    mime_type=args.get("mime_type") or "image/png",
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        raise ValueError("analyze_img 需要 file_path 或 base64")

    handlers: Dict[str, Callable[..., str]] = {
        "read_docx": read_docx,
        "read_pdf": read_pdf,
        "read_document": read_document,
    }
    if name not in handlers:
        raise JsonRpcError(-32602, f"未知工具: {name}")
    return text_result(handlers[name](**_doc_args(args)))


def handle_request(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if "id" not in message:
        return None

    try:
        if method == "initialize":
            return response(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": SERVER_INFO,
                    "instructions": "codex-lens 可读取 DOCX/PDF 并分析图片，将多模态输入转换为结构化文本。",
                },
            )
        if method == "ping":
            return response(request_id, {})
        if method == "tools/list":
            return response(request_id, {"tools": TOOLS})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if not name:
                raise JsonRpcError(-32602, "tools/call 缺少工具名")
            try:
                return response(request_id, call_tool(name, args))
            except JsonRpcError:
                raise
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                return response(request_id, text_result(f"工具执行失败: {exc}", is_error=True))
            except Exception as exc:
                log(traceback.format_exc())
                return response(request_id, text_result(f"工具执行失败: {exc}", is_error=True))

        raise JsonRpcError(-32601, f"未知方法: {method}")
    except JsonRpcError as exc:
        return error_response(request_id, exc.code, exc.message, exc.data)
    except Exception as exc:
        log(traceback.format_exc())
        return error_response(request_id, -32603, f"服务器内部错误: {exc}")


def emit(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _handle_payload(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                yield error_response(None, -32600, "无效 JSON-RPC 请求")
                continue
            result = handle_request(item)
            if result is not None:
                yield result
    elif isinstance(payload, dict):
        result = handle_request(payload)
        if result is not None:
            yield result
    else:
        yield error_response(None, -32600, "无效 JSON-RPC 请求")


def run_stdio() -> None:
    log("[codex-lens] MCP stdio server started")
    for raw_line in sys.stdin.buffer:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            emit(error_response(None, -32700, f"JSON 解析失败: {exc}"))
            continue

        for item in _handle_payload(payload):
            emit(item)
    log("[codex-lens] MCP stdio server stopped")


if __name__ == "__main__":
    run_stdio()
