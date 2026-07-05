from pathlib import Path
from typing import Optional

from .read_docx import read_docx
from .read_pdf import read_pdf


def read_document(
    file_path: str,
    use_image_analysis: bool = True,
    max_images: Optional[int] = None,
    min_image_kb: float = 3.0,
    image_prompt: Optional[str] = None,
) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext == ".docx":
        return read_docx(file_path, use_image_analysis, max_images, min_image_kb, image_prompt)
    if ext == ".pdf":
        return read_pdf(file_path, use_image_analysis, max_images, min_image_kb, image_prompt)
    raise ValueError(f"不支持的文件格式: {ext}，支持 .docx / .pdf")
