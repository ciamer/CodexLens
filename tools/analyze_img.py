import base64
import mimetypes
import os
import re
from pathlib import Path
from typing import Optional, Tuple


DEFAULT_PROMPT = """请详细描述这张论文图中的所有视觉元素，包括但不限于：

1. **图表类型**：是折线图、柱状图、散点图、热力图、模型结构图、示意图还是其他？
2. **坐标轴**：X轴和Y轴的标签、范围、刻度分布。
3. **曲线/数据**：每条曲线/柱子的颜色、走势、趋势（上升/下降/波动）、最高点/最低点位置，多条曲线之间的对比关系。
4. **图例**：标签内容和对应的颜色/符号。
5. **文字标注**：图中所有文字的内容和位置。
6. **模型结构图**：如果是网络结构图，请描述每个模块的名称、形状、输入输出尺寸，以及模块之间的连接关系。
7. **其他视觉元素**：箭头、虚线、阴影、背景色块等。

请尽可能详细和结构化地输出，不要遗漏任何视觉信息。"""


API_KEY_ENV_VAR = "CODEX_LENS_API_KEY"
BASE_URL = os.getenv("CODEX_LENS_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = os.getenv("CODEX_LENS_VISION_MODEL") or "qwen3.5-flash"

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".jpx",
    ".jp2",
}

DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;,]+)?(?:;[^,]*)?,(?P<data>.*)$", re.DOTALL)


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def guess_mime_type(image_path: str) -> str:
    path = Path(image_path)
    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type:
        return mime_type
    ext = path.suffix.lower().lstrip(".").replace("jpg", "jpeg")
    return f"image/{ext or 'png'}"


def split_data_url(image_data: str, fallback_mime_type: str = "image/png") -> Tuple[str, str]:
    match = DATA_URL_RE.match(image_data.strip())
    if not match:
        return fallback_mime_type, image_data.strip()
    return match.group("mime") or fallback_mime_type, match.group("data").strip()


def get_api_key(api_key: Optional[str] = None) -> str:
    resolved = api_key or os.getenv(API_KEY_ENV_VAR)
    if not resolved:
        raise RuntimeError(
            f"未设置 {API_KEY_ENV_VAR}。请把视觉模型 API Key 配置为 Windows 用户环境变量，"
            "设置后重启 Codex 或当前终端。"
        )
    return resolved


def _client(api_key: Optional[str] = None, base_url: Optional[str] = None):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("缺少 openai 包，请安装 openai 或使用 Codex 自带运行时。") from exc

    return OpenAI(api_key=get_api_key(api_key), base_url=base_url or BASE_URL)


def _run_vision_request(
    image_b64: str,
    mime_type: str,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    api_key: Optional[str],
    base_url: Optional[str],
) -> str:
    completion = _client(api_key=api_key, base_url=base_url).chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return completion.choices[0].message.content or ""


def analyze_image(
    image_path: str,
    prompt: str = DEFAULT_PROMPT,
    model: str = MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的图片格式: {path.suffix}，支持: {sorted(SUPPORTED_EXTENSIONS)}")

    return _run_vision_request(
        image_b64=encode_image(str(path)),
        mime_type=guess_mime_type(str(path)),
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
    )


def analyze_image_base64(
    image_data: str,
    mime_type: str = "image/png",
    prompt: str = DEFAULT_PROMPT,
    model: str = MODEL,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    detected_mime_type, image_b64 = split_data_url(image_data, fallback_mime_type=mime_type)
    return _run_vision_request(
        image_b64=image_b64,
        mime_type=detected_mime_type,
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
    )
