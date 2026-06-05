# preview.py
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from config import OUTPUT

def crop_region(img_pil, bounds):
    """支持跨180°经线裁剪"""
    width, height = img_pil.size
    lon_min, lon_max, lat_min, lat_max = bounds
    y0 = max(0, int((90.0 - lat_max) / 180.0 * height))
    y1 = min(height, int((90.0 - lat_min) / 180.0 * height))
    if y1 <= y0:
        return None

    if lon_min <= lon_max:
        x0 = max(0, int((lon_min + 180.0) / 360.0 * width))
        x1 = min(width, int((lon_max + 180.0) / 360.0 * width))
        if x1 <= x0:
            return None
        return img_pil.crop((x0, y0, x1, y1))
    else:
        x0 = int((lon_min + 180.0) / 360.0 * width)
        x1 = int((lon_max + 180.0) / 360.0 * width)
        left  = img_pil.crop((x0, y0, width, y1))
        right = img_pil.crop((0,  y0, x1,   y1))
        merged = Image.new("RGB", (left.width + right.width, left.height))
        merged.paste(left,  (0, 0))
        merged.paste(right, (left.width, 0))
        return merged

def make_compare(in_pil, out_pil, bounds, label=""):
    """生成 D5a vs D5b 左右对比图"""
    left  = crop_region(in_pil,  bounds)
    right = crop_region(out_pil, bounds)
    if left is None or right is None:
        return None

    max_w = 800
    left.thumbnail((max_w, max_w), Image.LANCZOS)
    right = right.resize(left.size, Image.LANCZOS)

    sep = 4
    canvas = Image.new("RGB", (left.width * 2 + sep, left.height), (40, 40, 40))
    canvas.paste(left,  (0, 0))
    canvas.paste(right, (left.width + sep, 0))
    return canvas

def save_all_previews(in_pil, out_pil, out_dir):
    if not OUTPUT.get("generate_region_previews"):
        return
    for r in OUTPUT["region_preview_regions"]:
        name = r["name"]
        cmp = make_compare(in_pil, out_pil, r["bounds"], label=name)
        if cmp is None:
            print(f"  [preview] 跳过 {name}")
            continue
        path = os.path.join(out_dir, f"compare_{name}.jpg")
        cmp.save(path, "JPEG", quality=88)
        print(f"  [preview] {path}")
