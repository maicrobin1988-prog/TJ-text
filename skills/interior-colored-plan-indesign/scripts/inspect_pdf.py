#!/usr/bin/env python3
"""Read one PDF page for a color-plan workflow; never infer room identities.

Requires PyMuPDF (import fitz). Outputs inspect.json, preview.png,
extracted_text.txt, and a vector-preserving normalized_plan.pdf.
All display bboxes use the rendered CropBox's top-left as (0, 0), in pt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

try:
    import fitz
except ImportError:
    raise SystemExit("缺少 PyMuPDF：请在当前 Python 环境安装 pymupdf 后再运行。")


OUTPUT_NAMES = ("inspect.json", "preview.png", "extracted_text.txt", "normalized_plan.pdf")
DPI = 150


def rect_list(rect):
    return [round(float(value), 5) for value in fitz.Rect(rect)]


def bbox_record(bbox, rotation_matrix):
    display = fitz.Rect(bbox) * rotation_matrix
    return {
        "bbox_source_unrotated_pt": rect_list(bbox),
        "bbox_display_pt": rect_list(display),
        "bbox_preview_px": [round(float(v) * DPI / 72, 5) for v in display],
    }


def source_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_text(page):
    """Keep spans, characters, and words in both unrotated and display coordinates."""
    matrix = page.rotation_matrix
    flags = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
    raw = page.get_text("rawdict", flags=flags, sort=False)
    spans = []
    for block_index, block in enumerate(raw.get("blocks", [])):
        if block.get("type") != 0:
            continue
        for line_index, line in enumerate(block.get("lines", [])):
            for span_index, span in enumerate(line.get("spans", [])):
                characters = []
                for char in span.get("chars", []):
                    characters.append({"text": char["c"], **bbox_record(char["bbox"], matrix)})
                spans.append({
                    "block_index": block_index,
                    "line_index": line_index,
                    "span_index": span_index,
                    "text": "".join(char["text"] for char in characters),
                    "font": span.get("font"),
                    "font_size_pt": span.get("size"),
                    "line_direction_unrotated": list(line.get("dir", (1, 0))),
                    **bbox_record(span["bbox"], matrix),
                    "characters": characters,
                })
    words = []
    for word in page.get_text("words", sort=False):
        words.append({
            "text": word[4],
            "block_index": word[5],
            "line_index": word[6],
            "word_index": word[7],
            **bbox_record(word[:4], matrix),
        })
    return spans, words


def normalize_page(source, page_index):
    """Bake a cloned page's visible appearances, then re-place its vectors at origin.

    show_pdf_page uses counterclockwise rotation in PDF coordinates. Clearing the
    cloned /Rotate, then applying -source.rotation reproduces the displayed page.
    Explicitly leaving the cloned CropBox intact avoids the crop loss associated
    with replacing its MediaBox before this placement.
    """
    original_page = source[page_index]
    width, height = original_page.rect.width, original_page.rect.height
    rotation = original_page.rotation
    clone = fitz.open()
    normalized = fitz.open()
    try:
        clone.insert_pdf(source, from_page=page_index, to_page=page_index)
        has_appearances = bool(list(clone[0].annots() or [])) or bool(list(clone[0].widgets() or []))
        if has_appearances:
            if not hasattr(clone, "bake"):
                raise RuntimeError("本页含批注/表单，当前 PyMuPDF 不支持 bake；请升级后归一化，以免丢失可见内容。")
            clone.bake(annots=True, widgets=True)
        clone[0].set_rotation(0)
        target = normalized.new_page(width=width, height=height)
        if clone[0].get_contents():
            target.show_pdf_page(
                target.rect, clone, 0, keep_proportion=True,
                rotate=-rotation, clip=clone[0].rect,
            )
        return normalized, has_appearances
    except Exception:
        normalized.close()
        raise
    finally:
        clone.close()


def inspect(input_path: Path, page_number: int, output_dir: Path, overwrite: bool):
    input_path = input_path.expanduser().resolve(strict=True)
    if not input_path.is_file():
        raise ValueError("输入必须是 PDF 文件。")
    output_dir = output_dir.expanduser().resolve()
    if output_dir == input_path:
        raise ValueError("--out 必须是输出目录，不能指向输入 PDF。")
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError("--out 已存在且不是目录。")
    outputs = {name: output_dir / name for name in OUTPUT_NAMES}
    for output in outputs.values():
        if output.resolve() == input_path:
            raise ValueError("输出路径与输入 PDF 重合；请指定另一个 --out 目录。")
        if output.exists() or output.is_symlink():
            if not overwrite:
                raise FileExistsError(f"输出已存在：{output}；如需替换本脚本的输出，请显式添加 --overwrite。")
            if output.is_dir():
                raise IsADirectoryError(str(output))
    digest_before = source_sha256(input_path)
    with fitz.open(input_path) as document:
        if not document.is_pdf:
            raise ValueError("输入不是 PDF。")
        if document.needs_pass:
            raise ValueError("PDF 已加密，需要先提供已授权解锁的副本。")
        if page_number < 1 or page_number > len(document):
            raise ValueError(f"--page 应在 1–{len(document)} 之间。")
        page = document[page_number - 1]
        spans, words = collect_text(page)
        extracted_text = page.get_text("text", sort=False)
        character_count = sum(len(span["characters"]) for span in spans)
        drawings = page.get_drawings()
        images = page.get_images(full=True)
        image_instances = page.get_image_info(xrefs=False)
        annotations = list(page.annots() or [])
        widgets = list(page.widgets() or [])
        links = page.get_links()
        preview = page.get_pixmap(dpi=DPI, alpha=False, annots=True)
        normalized, baked = normalize_page(document, page_number - 1)
        try:
            normalization = {
                "output": "normalized_plan.pdf",
                "page_count": 1,
                "rotation": 0,
                "media_box_pt": rect_list(normalized[0].mediabox),
                "crop_box_pt": rect_list(normalized[0].cropbox),
                "preserves_vector_page_content": True,
                "steps": [
                    "复制指定页到内存文档，不保存或修改源 PDF。",
                    "在内存副本中烘焙批注/表单的可见外观。" if baked else "本页无需烘焙批注/表单外观。",
                    "保留副本 CropBox，清除副本 /Rotate，按原旋转角的负值置入新页。",
                    "新页尺寸等于源页显示尺寸；MediaBox/CropBox 从 (0,0) 起；保持矢量，未栅格化底图。",
                ],
                "limitations": [
                    "归一化文件仅供底图置入；不保留原交互链接、表单可编辑性、签名或批注交互对象。",
                    "材质、房间边界、房名含义未识别；归一化不会把 PDF 对象变成 InDesign 原生路径。",
                    "透明度、字体和线条的视觉等同性仍需在 InDesign 置入后检查。",
                ],
            }
            report = {
                "schema_version": 1,
                "source": {
                    "path": str(input_path), "sha256": digest_before,
                    "page_number_1based": page_number, "page_count": len(document),
                    "media_box_pt": rect_list(page.mediabox),
                    "crop_box_unrotated_pt": rect_list(page.cropbox),
                    "crop_box_position_pt": [float(v) for v in page.cropbox_position],
                    "display_rect_pt": rect_list(page.rect), "rotation": page.rotation,
                    "rotation_matrix": [float(v) for v in page.rotation_matrix],
                    "pymupdf_version": fitz.VersionBind,
                },
                "coordinates": {
                    "unit": "pt", "points_per_inch": 72,
                    "display_origin": "显示 CropBox 左上角 (0,0)，x 向右，y 向下。",
                    "bbox_order": ["x0", "y0", "x1", "y1"],
                    "conversion": "bbox_display_pt = bbox_source_unrotated_pt * source.rotation_matrix",
                    "preview_pixel_conversion": "bbox_preview_px = bbox_display_pt * 150 / 72",
                    "normalized_pdf_coordinates": "与 bbox_display_pt 相同；适用于归一化 PDF 的原始 100% pt 坐标。",
                    "note": "原页框边缘可能存在部分不可见字形；bbox 为提取结果，需按显示页范围复核。",
                },
                "preview": {"file": "preview.png", "dpi": DPI, "width_px": preview.width,
                            "height_px": preview.height, "annotations_rendered": True},
                "inventory": {
                    "copyable_character_count": character_count, "text_span_count": len(spans),
                    "word_count": len(words),
                    "raster_image_reference_count": len(images),
                    "raster_image_placement_count": len(image_instances),
                    "vector_path_record_count": len(drawings),
                    "annotation_count": len(annotations), "widget_count": len(widgets), "link_count": len(links),
                    "count_note": "路径数是 get_drawings 的绘制记录数，不是房间数或闭合区域数；图像引用数可能含重复或未使用资源。",
                },
                "reading": {
                    "ocr_performed": False, "room_inference_performed": False,
                    "visual_review_required": True,
                    "copyable_text_available": bool(character_count),
                    "guidance": "已有可复制文字，仍须对照预览识读与核对房名。" if character_count else
                                "本页未提取到可复制文字，需要视觉识读；必要时另行 OCR 并逐项核对。",
                },
                "text_spans": spans, "words": words,
                "normalization": normalization,
            }
            if source_sha256(input_path) != digest_before:
                raise RuntimeError("源文件在检查期间发生变化；未发布输出，请基于稳定版本重试。")
            output_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".inspect_pdf_", dir=output_dir) as staging:
                staging = Path(staging)
                (staging / "inspect.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                (staging / "extracted_text.txt").write_text(extracted_text, encoding="utf-8")
                preview.save(staging / "preview.png")
                normalized.save(staging / "normalized_plan.pdf", garbage=4, deflate=True)
                # Recheck before publishing: fail safely if another run wrote outputs.
                if not overwrite and any(path.exists() or path.is_symlink() for path in outputs.values()):
                    raise FileExistsError("输出在检查期间已被其他任务创建；未覆盖。")
                published = []
                try:
                    for name, output in outputs.items():
                        if output.resolve() == input_path:
                            raise ValueError("输出与源文件重合；未覆盖源文件。")
                        if overwrite:
                            os.replace(staging / name, output)
                        else:
                            # A hard link is atomic and fails if the target exists,
                            # unlike os.replace after a non-atomic existence check.
                            os.link(staging / name, output)
                            published.append((output, os.stat(output)))
                except Exception:
                    # Roll back only the no-overwrite files this run created.
                    for output, identity in published:
                        try:
                            current = os.stat(output)
                            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                                output.unlink()
                        except FileNotFoundError:
                            pass
                    raise
            return {"outputs": [str(path) for path in outputs.values()], "source_sha256": digest_before,
                    "page_number_1based": page_number, "text_span_count": len(spans)}
        finally:
            normalized.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("--page", type=int, default=1, help="1-based page number (default: 1)")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("--overwrite", action="store_true", help="explicitly replace this script's existing outputs")
    args = parser.parse_args()
    try:
        result = inspect(args.input_pdf, args.page, args.out, args.overwrite)
    except Exception as exc:
        parser.exit(1, f"检查失败：{exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
