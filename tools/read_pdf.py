import os
from pathlib import Path
from typing import List, Optional, Tuple

from .docx_utils import TemporaryImageDir, analyze_images_to_sections


def extract_text_from_pdf(pdf_path: str) -> List[Tuple[int, str]]:
    try:
        import pdfplumber
    except ImportError:
        pdfplumber = None

    if pdfplumber is not None:
        pages_text: List[Tuple[int, str]] = []
        with pdfplumber.open(pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                pages_text.append((idx, text.strip()))
        return pages_text

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("缺少 pdfplumber 或 PyMuPDF，无法读取 PDF。") from exc

    doc = fitz.open(pdf_path)
    try:
        return [(idx + 1, (page.get_text() or "").strip()) for idx, page in enumerate(doc)]
    finally:
        doc.close()


def extract_images_from_pdf(pdf_path: str, output_dir: str, min_size_kb: float = 3.0) -> List[dict]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("缺少 PyMuPDF/fitz 包，无法提取 PDF 图片。") from exc

    os.makedirs(output_dir, exist_ok=True)
    images: List[dict] = []
    doc = fitz.open(pdf_path)
    try:
        for page_num in range(doc.page_count):
            page = doc[page_num]
            img_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(img_list, start=1):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                ext = base_image["ext"]
                size_kb = len(img_bytes) / 1024
                if size_kb < min_size_kb:
                    continue

                img_filename = f"P{page_num + 1}_img{img_idx}.{ext}"
                img_path = os.path.join(output_dir, img_filename)
                with open(img_path, "wb") as f:
                    f.write(img_bytes)

                images.append(
                    {
                        "filename": img_filename,
                        "path": img_path,
                        "media_path": f"page{page_num + 1}_img{img_idx}",
                        "size_kb": round(size_kb, 1),
                        "source": "pdf",
                        "page": page_num + 1,
                        "context": None,
                    }
                )
    finally:
        doc.close()
    return images


def read_pdf(
    file_path: str,
    use_image_analysis: bool = True,
    max_images: Optional[int] = None,
    min_image_kb: float = 3.0,
    image_prompt: Optional[str] = None,
) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文档不存在: {file_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"read_pdf 只支持 .pdf，当前文件: {path.suffix}")

    result: List[str] = [f"# 文档: {path.name}\n", "## 文档正文\n"]
    for page_num, text in extract_text_from_pdf(str(path)):
        result.append(f"--- 第 {page_num} 页 ---")
        result.append(text or "（本页未提取到可复制文本）")
        result.append("")

    if use_image_analysis:
        with TemporaryImageDir("pdf_images_") as temp_dir:
            images = extract_images_from_pdf(str(path), temp_dir, min_size_kb=min_image_kb)
            result.extend(analyze_images_to_sections(images, max_images=max_images, prompt=image_prompt))

    return "\n".join(result)
