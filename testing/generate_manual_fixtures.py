"""
Generate manual-testing fixture sets for every DPA Image Toolkit tool.

Produces testing/manual/ with one folder per tool, ready to point the web UI at.

Usage:
    python3 testing/generate_manual_fixtures.py

Output:
    testing/manual/
        01_auto_crop/           8 scanned-doc JPEGs with large white margins
        02_auto_crop_skewed/    same 8 docs rotated ±2–7° (for Straighten test)
        03_add_border/          8 tight-cropped docs (minimal margins, need a border)
        04_merge_tiffs/         20 single-page TIFFs in 5 named merge groups
        05_split_tiffs/         4 multi-page TIFFs (3–6 pages each)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont

MANUAL_DIR = Path(__file__).resolve().parent / "manual"
DPI = (200, 200)
CANVAS_W, CANVAS_H = 1700, 2200  # portrait "letter" scan bed

# ── helpers ───────────────────────────────────────────────────────────────────

def _clear(folder: Path, pattern: str = "*") -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for f in folder.glob(pattern):
        if f.is_file():
            f.unlink()


def _draw_document_body(draw: ImageDraw.ImageDraw, margin: int, variant: int) -> None:
    """Draw a simple scanned-document interior at the given margin."""
    w, h = CANVAS_W, CANVAS_H
    doc_x0 = margin
    doc_y0 = margin
    doc_x1 = w - margin
    doc_y1 = h - margin

    # Document background (off-white)
    draw.rectangle([doc_x0, doc_y0, doc_x1, doc_y1], fill=(248, 246, 242))

    # Header bar
    hdr_h = 120
    draw.rectangle([doc_x0, doc_y0, doc_x1, doc_y0 + hdr_h], fill=(60 + variant * 8, 60, 90))

    # Simulated text lines
    line_x0 = doc_x0 + 80
    line_x1 = doc_x1 - 80
    line_y = doc_y0 + hdr_h + 80
    line_gap = 48
    line_h = 14
    colors = [(30, 30, 30), (60, 60, 60), (45, 45, 45)]
    for i in range(22):
        if i % 6 == 5:
            line_y += 30  # paragraph break
            continue
        w_factor = 0.6 + 0.4 * ((i * 37 + variant * 13) % 100) / 100
        draw.rectangle(
            [line_x0, line_y, line_x0 + int((line_x1 - line_x0) * w_factor), line_y + line_h],
            fill=colors[i % 3],
        )
        line_y += line_gap
        if line_y + line_h > doc_y1 - 80:
            break

    # Footer line
    draw.rectangle([doc_x0 + 60, doc_y1 - 60, doc_x1 - 60, doc_y1 - 46], fill=(120, 120, 120))


def _make_scan(variant: int, margin: int = 300) -> Image.Image:
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    _draw_document_body(draw, margin, variant)
    return img


def _rotate_image(img: Image.Image, angle_deg: float) -> Image.Image:
    """Rotate image by angle (degrees, clockwise positive) with white fill."""
    import cv2
    import numpy as np

    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    h, w = cv_img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), -angle_deg, 1.0)
    rotated = cv2.warpAffine(
        cv_img, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    return Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))


# ── 01 auto_crop ──────────────────────────────────────────────────────────────

def _generate_auto_crop() -> Path:
    out = MANUAL_DIR / "01_auto_crop"
    _clear(out, "*.jpg")
    for i in range(8):
        img = _make_scan(variant=i, margin=300)
        img.save(out / f"scan_{i + 1:02d}.jpg", "JPEG", quality=92, dpi=DPI)
    return out


# ── 02 auto_crop_skewed ───────────────────────────────────────────────────────

SKEW_ANGLES = [2.5, -3.0, 4.5, -2.0, 6.0, -4.5, 3.5, -5.5]

def _generate_auto_crop_skewed() -> Path:
    out = MANUAL_DIR / "02_auto_crop_skewed"
    _clear(out, "*.jpg")
    for i, angle in enumerate(SKEW_ANGLES):
        base = _make_scan(variant=i, margin=280)
        skewed = _rotate_image(base, angle)
        label = f"pos{abs(angle):.1f}" if angle > 0 else f"neg{abs(angle):.1f}"
        skewed.save(out / f"skewed_{i + 1:02d}_{label}deg.jpg", "JPEG", quality=92, dpi=DPI)
    return out


# ── 03 add_border ─────────────────────────────────────────────────────────────

def _generate_add_border() -> Path:
    out = MANUAL_DIR / "03_add_border"
    _clear(out, "*.jpg")
    for i in range(8):
        # Tight margin — content almost fills the frame, ready to receive a border
        img = _make_scan(variant=i, margin=30)
        img.save(out / f"tight_{i + 1:02d}.jpg", "JPEG", quality=92, dpi=DPI)
    return out


# ── 04 merge_tiffs ────────────────────────────────────────────────────────────

MERGE_GROUPS = [
    ("invoice", "grpA", 3),
    ("invoice", "grpB", 2),
    ("report",  "grpC", 4),
    ("report",  "grpD", 2),
    ("letter",  "grpE", 3),
]

_PAGE_COLORS = [
    (220, 230, 245),
    (230, 245, 220),
    (245, 220, 230),
    (245, 240, 210),
    (210, 240, 245),
]


def _make_tiff_page(label: str, color: tuple) -> Image.Image:
    img = Image.new("RGB", (850, 1100), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 810, 1060], fill=color)
    draw.rectangle([60, 60, 790, 140], fill=(80, 80, 110))
    # Simulated text lines
    for row in range(18):
        y = 180 + row * 46
        w = int(700 * (0.5 + 0.5 * ((row * 17 + hash(label)) % 100) / 100))
        draw.rectangle([80, y, 80 + w, y + 12], fill=(40, 40, 40))
    return img


def _generate_merge_tiffs() -> Path:
    out = MANUAL_DIR / "04_merge_tiffs"
    _clear(out, "*.tif")
    for color_idx, (prefix, group, count) in enumerate(MERGE_GROUPS):
        color = _PAGE_COLORS[color_idx % len(_PAGE_COLORS)]
        for seq in range(1, count + 1):
            fname = f"{prefix}_{group}_{seq:03d}.tif"
            page = _make_tiff_page(fname, color)
            page.save(out / fname, "TIFF", dpi=DPI)
    return out


# ── 05 split_tiffs ────────────────────────────────────────────────────────────

SPLIT_SPECS = [
    ("ledger_vol1", 4),
    ("ledger_vol2", 3),
    ("archive_box1", 6),
    ("archive_box2", 5),
]

_SPLIT_COLORS = [
    [(200, 215, 235), (215, 230, 250), (185, 200, 225), (230, 240, 255)],
    [(215, 235, 210), (230, 250, 225), (200, 220, 195), (245, 255, 240)],
    [(235, 210, 215), (250, 225, 230), (220, 195, 200), (255, 240, 245)],
    [(235, 230, 200), (250, 245, 215), (220, 215, 185), (255, 255, 230)],
]


def _generate_split_tiffs() -> Path:
    out = MANUAL_DIR / "05_split_tiffs"
    _clear(out, "*.tif")
    for vol_idx, (name, page_count) in enumerate(SPLIT_SPECS):
        pages = []
        palette = _SPLIT_COLORS[vol_idx % len(_SPLIT_COLORS)]
        for p in range(page_count):
            color = palette[p % len(palette)]
            page = _make_tiff_page(f"{name} p{p + 1}", color)
            pages.append(page)
        first = pages[0]
        rest = pages[1:]
        first.save(
            out / f"{name}.tif",
            "TIFF",
            save_all=True,
            append_images=rest,
            dpi=DPI,
        )
    return out


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Generating manual test fixtures…")

    dirs = [
        ("01 auto_crop",         _generate_auto_crop),
        ("02 auto_crop_skewed",  _generate_auto_crop_skewed),
        ("03 add_border",        _generate_add_border),
        ("04 merge_tiffs",       _generate_merge_tiffs),
        ("05 split_tiffs",       _generate_split_tiffs),
    ]

    for label, fn in dirs:
        out = fn()
        files = list(out.iterdir())
        print(f"  {label}: {len(files)} files → {out}")

    print("Done.")


if __name__ == "__main__":
    main()
