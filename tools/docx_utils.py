import csv
import io
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET

from .analyze_img import analyze_image


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".wmf", ".emf", ".jpx", ".jp2", ".webp"}
WORD_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


def log(message: str) -> None:
    print(message, file=__import__("sys").stderr)


def table_to_markdown(rows: Iterable[Iterable[str]]) -> str:
    rows = [[(cell or "").replace("\n", " ").strip() for cell in row] for row in rows]
    if not rows:
        return ""

    def esc(value: str) -> str:
        return value.replace("|", "\\|")

    output = [" | ".join(esc(cell) for cell in rows[0])]
    output.append(" | ".join("---" for _ in rows[0]))
    for row in rows[1:]:
        output.append(" | ".join(esc(cell) for cell in row))
    return "\n".join(output)


def table_to_csv(rows: Iterable[Iterable[str]]) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerows(rows)
    return stream.getvalue().strip()


def extract_xml_texts(docx_path: str, member_names: Iterable[str]) -> Dict[str, List[str]]:
    texts: Dict[str, List[str]] = {}
    with zipfile.ZipFile(docx_path, "r") as z:
        names = set(z.namelist())
        for member_name in member_names:
            if member_name not in names:
                continue
            root = ET.fromstring(z.read(member_name))
            values = []
            for node in root.findall(".//w:t", WORD_NS):
                if node.text:
                    values.append(node.text)
            if values:
                texts[member_name] = values
    return texts


def _rels_map(z: zipfile.ZipFile) -> Dict[str, str]:
    rels_path = "word/_rels/document.xml.rels"
    if rels_path not in z.namelist():
        return {}
    rels_root = ET.fromstring(z.read(rels_path))
    mapping: Dict[str, str] = {}
    for rel in rels_root.findall(".//rel:Relationship", REL_NS):
        rel_id = rel.get("Id")
        target = rel.get("Target", "")
        if rel_id:
            mapping[rel_id] = target
    return mapping


def get_image_positions_in_docx(docx_path: str) -> Dict[str, Dict[str, Optional[str]]]:
    media_positions: Dict[str, Dict[str, Optional[str]]] = {}
    with zipfile.ZipFile(docx_path, "r") as z:
        if "word/document.xml" not in z.namelist():
            return media_positions

        root = ET.fromstring(z.read("word/document.xml"))
        rels = _rels_map(z)
        paragraphs = root.findall(".//w:p", WORD_NS)

        for p_idx, para in enumerate(paragraphs, start=1):
            texts = para.findall(".//w:t", WORD_NS)
            para_text = "".join(t.text or "" for t in texts).strip()
            blips = para.findall(".//a:blip", WORD_NS)
            for blip in blips:
                embed = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                target = rels.get(embed or "")
                if target.startswith("media/"):
                    full_media_path = f"word/{target}"
                    media_positions.setdefault(
                        full_media_path,
                        {
                            "paragraph": str(p_idx),
                            "context": para_text[:240] if para_text else "(图片单独段落)",
                        },
                    )
    return media_positions


def extract_images_from_docx(docx_path: str, output_dir: str, min_size_kb: float = 3.0) -> List[dict]:
    os.makedirs(output_dir, exist_ok=True)
    images = []
    positions = get_image_positions_in_docx(docx_path)

    with zipfile.ZipFile(docx_path, "r") as z:
        media_files = sorted(name for name in z.namelist() if name.startswith("word/media/"))
        for media_path in media_files:
            ext = os.path.splitext(media_path)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            img_data = z.read(media_path)
            size_kb = len(img_data) / 1024
            if size_kb < min_size_kb:
                continue

            img_filename = os.path.basename(media_path)
            img_path = os.path.join(output_dir, img_filename)
            with open(img_path, "wb") as f:
                f.write(img_data)

            position = positions.get(media_path, {})
            images.append(
                {
                    "filename": img_filename,
                    "path": img_path,
                    "media_path": media_path,
                    "size_kb": round(size_kb, 1),
                    "source": "docx",
                    "page": None,
                    "paragraph": position.get("paragraph"),
                    "context": position.get("context"),
                }
            )
    return images


def analyze_images_to_sections(images: List[dict], max_images: Optional[int] = None, prompt: Optional[str] = None) -> List[str]:
    sections: List[str] = []
    if not images:
        return ["（文档中未内嵌可提取的图片；图片可能以矢量图形形式直接绘制在页面中）\n"]

    sections.append("## 文档中的图片分析\n")
    if max_images and len(images) > max_images:
        log(f"[INFO] 文档共有 {len(images)} 张图片，限制分析前 {max_images} 张")
        images = images[:max_images]

    log(f"[INFO] 发现 {len(images)} 张有意义的图片，正在逐一分析...")
    for img_idx, img in enumerate(images, start=1):
        page_info = f"第 {img['page']} 页" if img.get("page") else ""
        context = img.get("context")
        sections.append(f"--- 图片 {img_idx}/{len(images)} [{img['filename']}, {img['size_kb']}KB] {page_info}---")
        if context:
            sections.append(f"上下文：{context}")
        sections.append("")
        log(f"[INFO] 分析图片 {img_idx}/{len(images)}: {img['filename']} ({img['size_kb']}KB)")
        try:
            description = analyze_image(
                image_path=img["path"],
                prompt=prompt
                or "请详细描述这张学术论文图中的所有视觉元素，包括曲线趋势、坐标轴、图例、文字标注、模型结构等。请尽可能详细。",
            )
            sections.append(f"【图片 {img_idx} 描述】:")
            sections.append(description)
        except Exception as exc:
            sections.append(f"【图片 {img_idx} 分析失败】: {exc}")
        sections.append("")
    return sections


class TemporaryImageDir:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.path: Optional[str] = None

    def __enter__(self) -> str:
        self.path = tempfile.mkdtemp(prefix=self.prefix)
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.path:
            import shutil

            shutil.rmtree(self.path, ignore_errors=True)
