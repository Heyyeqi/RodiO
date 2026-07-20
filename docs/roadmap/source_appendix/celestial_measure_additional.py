#!/usr/bin/env python3
"""
celestial_measure_additional.py
#53/#54 Step 0 补充资源测量：太阳日面 / 木·天·海三行星环 / 月球清晰度升级对比
测量方法（可复现）：
  - DISK（盘状物：太阳、月球）：亮度阈值抠出天体 → 质心 → 内盘(0.85R) → 剔除最暗/最亮 2% → 均值 RGB
  - RING（环带）：中带水平径向条带 → 24 段 → 排除纯黑边(亮度<8) → 逐段 RGB/亮度
全部色值从已下载图片直接测算，不编造。
"""
import numpy as np
from PIL import Image
import json, os

BASE = "pwa/assets/textures"

def measure_disk(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=float)            # H x W x 3
    H, W = a.shape[:2]
    lum = (a[:, :, 0] + a[:, :, 1] + a[:, :, 2]) / 3
    mx = lum.max()
    if mx < 5:
        return None
    mask = lum > 0.06 * mx
    ys, xs = mask.nonzero()
    if len(xs) < 50:
        return None
    cx, cy = float(xs.mean()), float(ys.mean())
    dx = xs.astype(float) - cx
    dy = ys.astype(float) - cy
    r = np.sqrt(dx * dx + dy * dy)
    rmax = r.max()
    frac = len(xs) / (H * W)
    if frac > 0.35:
        keep = r < 0.85 * rmax                  # 全圆盘：取内盘避临边暗角
    else:
        keep = np.ones(len(xs), dtype=bool)     # 表面近景：取全部天体像素
    # flat-index 向量化（避免逐元素 listcomp 陷阱）
    flat = (ys[keep].astype(np.int64) * W + xs[keep].astype(np.int64))
    cols = a.reshape(-1, 3)[flat]               # N x 3
    if cols.ndim == 1:
        cols = cols.reshape(1, 3)
    cl = cols.mean(1)
    lo, hi = np.percentile(cl, [2, 98])
    sel = cols[(cl > lo) & (cl < hi)]
    if len(sel) < 20:
        return None
    m = sel.mean(axis=0)
    return {
        "file": os.path.basename(path),
        "size": f"{W}x{H}",
        "body_frac": round(float(frac), 3),
        "sample_pixels": int(len(sel)),
        "rgb": [round(float(m[0]), 1), round(float(m[1]), 1), round(float(m[2]), 1)],
        "hex": "#%02X%02X%02X" % (int(m[0]), int(m[1]), int(m[2])),
        "mean_abs_RG": round(float(np.abs(sel[:, 0] - sel[:, 1]).mean()), 1),
        "mean_abs_RB": round(float(np.abs(sel[:, 0] - sel[:, 2]).mean()), 1),
        "grayscale_risk": bool(np.abs(sel[:, 0] - sel[:, 1]).mean() < 4 and np.abs(sel[:, 0] - sel[:, 2]).mean() < 4),
    }

def measure_ring(path, bands=24):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=float)
    H, W = a.shape[:2]
    y0, y1 = int(H * 0.35), int(H * 0.65)
    strip = a[y0:y1]
    perx = strip.reshape(-1, W, 3).mean(0)      # W x 3
    edges = np.linspace(0, W, bands + 1).astype(int)
    prof = []
    for i in range(bands):
        s, e = edges[i], edges[i + 1]
        seg = perx[s:e]
        lum_seg = seg.mean(1).mean()
        if lum_seg < 8:                           # 排除图像黑边
            continue
        prof.append({
            "seg": i + 1,
            "x_range": f"{s}-{e}",
            "rgb": [round(float(seg[:, 0].mean()), 1), round(float(seg[:, 1].mean()), 1), round(float(seg[:, 2].mean()), 1)],
            "lum": round(float(lum_seg), 1),
        })
    return {"file": os.path.basename(path), "size": f"{W}x{H}", "bands": len(prof), "profile": prof}

def main():
    disk_targets = [
        ("SUN (去色日面)", f"{BASE}/sun/sun_sdo_hmi_luminance.jpg"),
        ("MOON 2K (升级)", f"{BASE}/moon/moon_lroc_color_2k.jpg"),
        ("MOON 1K (旧)", f"{BASE}/moon/moon_1024.jpg"),
    ]
    ring_targets = [
        ("JUPITER 环", f"{BASE}/jupiter_rings/jupiter_main_ring_grayscale.jpg"),
        ("URANUS 环", f"{BASE}/uranus_rings/PIA00142_uranus_ring_system.jpg"),
        ("NEPTUNE 环", f"{BASE}/neptune_rings/PIA01493_neptune_rings.jpg"),
    ]

    out = {"disk": [], "rings": []}
    print("=" * 72)
    print("DISK 测量")
    print("=" * 72)
    for label, path in disk_targets:
        r = measure_disk(path)
        if r:
            gr = "  [近灰度]" if r["grayscale_risk"] else ""
            print(f"\n  [{label}] {r['file']}")
            print(f"    size={r['size']}  body_frac={r['body_frac']}  samples={r['sample_pixels']}")
            print(f"    RGB={r['rgb']} {r['hex']}  |RG|={r['mean_abs_RG']}  |RB|={r['mean_abs_RB']}{gr}")
            out["disk"].append({"label": label, **r})
        else:
            print(f"\n  [{label}] 测量跳过")

    print("\n" + "=" * 72)
    print("RING 径向条带测量")
    print("=" * 72)
    for label, path in ring_targets:
        r = measure_ring(path)
        print(f"\n  [{label}] {r['file']} ({r['size']}, {r['bands']} 有效段)")
        for p in r["profile"]:
            print(f"    seg{p['seg']:2d} [{p['x_range']:>8s}] RGB={p['rgb']} L={p['lum']}")
        out["rings"].append({"label": label, **r})

    with open(os.path.join(os.path.dirname(__file__), "celestial_measure_additional.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("\n[OK] 结果已写入 celestial_measure_additional.json")

if __name__ == "__main__":
    main()
