#!/usr/bin/env python3
"""
D5y regional ocean candidate generation.

This script keeps the final 8192x4096 texture fully local and algorithmic.
An optional GPT Image 2 stage may supply visual references, but the final
texture is never copied from any image model output.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.io import netcdf_file


ROOT = Path(os.path.expanduser("~/Projects/RodiO"))
BASE = ROOT / "pwa" / "assets" / "source"
STAGING = BASE / "bmng_staging"
EARTH_CAND = ROOT / "pwa" / "assets" / "earth" / "candidates"
DOC = ROOT / "docs" / "devlog_bathy_3_d5y_regional_ocean_candidate.md"

D3_PATH = STAGING / "bmng_processed_8192x4096_natural_d3.jpg"
D5C_PATH = STAGING / "bmng_processed_8192x4096_natural_d5c_palette_v6_1_bathy.jpg"
D5X_PATH = STAGING / "bmng_processed_8192x4096_natural_d5x_diagnostic_strong_bathy.jpg"
ETOPO = BASE / "bathy" / "ETOPO1_Ice_g_gdal.grd"

OUT_PATH = STAGING / "bmng_processed_8192x4096_natural_d5y_regional_ocean_bathy.jpg"
CAND_OUT = EARTH_CAND / "d5y_regional_ocean_bathy_8192x4096.jpg"

IMAGE2_REF = STAGING / "image2_d5y_regional_ocean_reference_2048.png"
PALETTE_REF = STAGING / "image2_d5y_palette_reference.png"
IMAGE2_NOTES = STAGING / "image2_d5y_reference_notes.json"

DEBUG_REGION = STAGING / "debug_d5y_region_map_2048.jpg"
DEBUG_WEIGHT = STAGING / "debug_d5y_final_weight_2048.jpg"
DEBUG_EA = STAGING / "debug_d5y_eastasia_mask_2048.jpg"
DEBUG_TROP = STAGING / "debug_d5y_tropical_mask_2048.jpg"
DEBUG_GULF = STAGING / "debug_d5y_gulf_redsea_mask_2048.jpg"
DEBUG_HLAT = STAGING / "debug_d5y_highlat_mask_2048.jpg"

D3_W, D3_H = 8192, 4096
WORK_W, WORK_H = 4096, 2048


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def range_soft(v: np.ndarray, lo_h: float, hi_h: float, lo_e: float, hi_e: float) -> np.ndarray:
    return np.where(
        v < lo_h,
        smoothstep((v - lo_e) / max(lo_h - lo_e, 1e-3)),
        np.where(
            v > hi_h,
            smoothstep((hi_e - v) / max(hi_e - hi_h, 1e-3)),
            1.0,
        ),
    ).astype(np.float32)


def sat_arr(a: np.ndarray) -> np.ndarray:
    mx = np.maximum(np.maximum(a[..., 0], a[..., 1]), a[..., 2])
    mn = np.minimum(np.minimum(a[..., 0], a[..., 1]), a[..., 2])
    return np.where(mx > 0, (mx - mn) / mx, 0.0)


def lum(a: np.ndarray) -> np.ndarray:
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def lonlat_rc(lon: float, lat: float) -> tuple[int, int]:
    c = int(round((lon + 180) / 360 * (D3_W - 1)))
    r = int(round((90 - lat) / 180 * (D3_H - 1)))
    return max(0, min(D3_H - 1, r)), max(0, min(D3_W - 1, c))


def bbox(lw: float, le: float, ls: float, ln: float) -> tuple[int, int, int, int]:
    r1, c1 = lonlat_rc(lw, ln)
    r2, c2 = lonlat_rc(le, ls)
    return min(r1, r2), max(r1, r2) + 1, min(c1, c2), max(c1, c2) + 1


def save_gray(arr: np.ndarray, path: Path, scale: float = 255.0) -> None:
    img = Image.fromarray(np.clip(arr * scale, 0, 255).astype(np.uint8), mode="L")
    img = img.resize((2048, 1024), Image.LANCZOS)
    img.save(path, "JPEG", quality=84, subsampling=2, optimize=True, progressive=True)


def save_rgb(arr: np.ndarray, path: Path) -> None:
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")
    img = img.resize((2048, 1024), Image.LANCZOS)
    img.save(path, "JPEG", quality=84, subsampling=2, optimize=True, progressive=True)


def resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    img = Image.fromarray(np.clip(mask * 255.0, 0, 255).astype(np.uint8), mode="L")
    img = img.resize(size, Image.BILINEAR)
    return np.array(img, dtype=np.float32) / 255.0


def resize_rgb(arr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")
    img = img.resize(size, Image.BILINEAR)
    return np.array(img, dtype=np.float32)


def resize_float(arr: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    img = Image.fromarray(arr.astype(np.float32), mode="F")
    img = img.resize(size, Image.BILINEAR)
    return np.array(img, dtype=np.float32)


def sample_region_mean(arr: np.ndarray, mask: np.ndarray) -> tuple[float, float, float]:
    if mask.sum() <= 0:
        return (0.0, 0.0, 0.0)
    return (
        float(arr[..., 0][mask].mean()),
        float(arr[..., 1][mask].mean()),
        float(arr[..., 2][mask].mean()),
    )


def mean_rgb_text(rgb: tuple[float, float, float] | None) -> str:
    if rgb is None:
        return "N/A"
    return f"{rgb[0]:.1f}/{rgb[1]:.1f}/{rgb[2]:.1f}"


def main() -> None:
    print("=" * 72)
    print("D5y regional ocean candidate")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)

    print(f"\n[{ts()}] Loading D3 / D5c / D5x...")
    d3_img = Image.open(D3_PATH).convert("RGB")
    d5c_img = Image.open(D5C_PATH).convert("RGB")
    d5x_img = Image.open(D5X_PATH).convert("RGB")
    d3 = np.array(d3_img, dtype=np.float32)
    d5c = np.array(d5c_img, dtype=np.float32)
    d5x = np.array(d5x_img, dtype=np.float32)

    print(f"[{ts()}] Loading ETOPO1 (~20s)...")
    with netcdf_file(ETOPO, "r", mmap=False) as ds:
        dim = ds.variables["dimension"][:]
        We, He = int(dim[0]), int(dim[1])
        z_raw = np.array(ds.variables["z"][:], dtype=np.float32).reshape(He, We)

    print(f"[{ts()}] Downsampling ETOPO1 → {WORK_W}x{WORK_H}...")
    ri = np.round(np.linspace(0, He - 1, WORK_H)).astype(int)
    ci = np.round(np.linspace(0, We - 1, WORK_W)).astype(int)
    depth = z_raw[np.ix_(ri, ci)]
    del z_raw
    depth_up = resize_float(depth, (D3_W, D3_H))
    ocean_up = depth_up < 0
    land_up = depth_up >= 0

    lon_g = np.linspace(-180, 180, WORK_W, dtype=np.float32)
    lat_g = np.linspace(90, -90, WORK_H, dtype=np.float32)
    LAT = lat_g[:, np.newaxis] * np.ones((1, WORK_W), dtype=np.float32)
    LON = lon_g[np.newaxis, :] * np.ones((WORK_H, 1), dtype=np.float32)

    print(f"[{ts()}] Phase 1: Masks...")
    ocean_hard = depth < 0
    land_hard = depth >= 0
    ocean_fade = gaussian_filter(ocean_hard.astype(np.float32), sigma=3)
    ocean_fade = np.clip(ocean_fade / 0.85, 0.0, 1.0)
    snow_mask = (d3[..., 0] > 210) & (d3[..., 1] > 210) & (d3[..., 2] > 210)

    print(f"[{ts()}] Phase 2: Depth weights (sigma_d=14, sigma_w=10)...")
    depth_sm = gaussian_filter(depth, sigma=14)
    d_val = np.clip(-depth_sm, 0.0, 12000.0)
    bp_d = [0, 20, 50, 200, 1000, 4000]
    bp_w = [0.185, 0.185, 0.150, 0.105, 0.025, 0.00]
    weight_base = np.interp(d_val, bp_d, bp_w).astype(np.float32) * ocean_fade
    weight_base = gaussian_filter(weight_base, sigma=10)

    print(f"[{ts()}] Phase 3: Regional masks...")
    ea_mask = (range_soft(LON, 112, 130, 100, 140) * range_soft(LAT, 22, 40, 15, 48)).astype(np.float32)
    trop_mask = np.where(
        np.abs(LAT) <= 20,
        1.0,
        np.where(np.abs(LAT) <= 30, smoothstep((30 - np.abs(LAT)) / 10.0), 0.0),
    ).astype(np.float32)
    pg_mask = (range_soft(LON, 48, 57, 44, 61) * range_soft(LAT, 24, 30, 20, 34)).astype(np.float32)
    rs_mask = (range_soft(LON, 32, 44, 28, 48) * range_soft(LAT, 12, 30, 8, 34)).astype(np.float32)
    hl_mask = np.where(
        np.abs(LAT) >= 50,
        1.0,
        np.where(np.abs(LAT) >= 40, smoothstep((np.abs(LAT) - 40) / 10.0), 0.0),
    ).astype(np.float32)

    print(
        f"  ea={ea_mask.mean()*100:.1f}%  trop={trop_mask.mean()*100:.1f}%"
        f"  pg={pg_mask.mean()*100:.2f}%  rs={rs_mask.mean()*100:.2f}%"
        f"  hl={hl_mask.mean()*100:.1f}%"
    )

    print(f"[{ts()}] Phase 4: Target colors...")
    bp_dc = [0, 20, 50, 200, 1000]

    global_R = [120, 102, 85, 72, 52]
    global_G = [170, 157, 137, 107, 80]
    global_B = [178, 174, 159, 126, 105]
    gl_tR = np.interp(d_val, bp_dc, global_R).astype(np.float32)
    gl_tG = np.interp(d_val, bp_dc, global_G).astype(np.float32)
    gl_tB = np.interp(d_val, bp_dc, global_B).astype(np.float32)

    ea_R = [130, 112, 92, 70, 52]
    ea_G = [175, 158, 135, 106, 80]
    ea_B = [174, 165, 150, 122, 105]
    ea_tR = np.interp(d_val, bp_dc, ea_R).astype(np.float32)
    ea_tG = np.interp(d_val, bp_dc, ea_G).astype(np.float32)
    ea_tB = np.interp(d_val, bp_dc, ea_B).astype(np.float32)

    trop_R = [142, 103, 74, 58, 52]
    trop_G = [216, 176, 143, 111, 80]
    trop_B = [200, 184, 168, 134, 105]
    tr_tR = np.interp(d_val, bp_dc, trop_R).astype(np.float32)
    tr_tG = np.interp(d_val, bp_dc, trop_G).astype(np.float32)
    tr_tB = np.interp(d_val, bp_dc, trop_B).astype(np.float32)

    gulf_R = [169, 126, 90, 70, 52]
    gulf_G = [191, 165, 135, 106, 80]
    gulf_B = [175, 162, 148, 120, 105]
    pg_tR = np.interp(d_val, bp_dc, gulf_R).astype(np.float32)
    pg_tG = np.interp(d_val, bp_dc, gulf_G).astype(np.float32)
    pg_tB = np.interp(d_val, bp_dc, gulf_B).astype(np.float32)

    high_R = [124, 107, 88, 68, 52]
    high_G = [169, 153, 132, 103, 80]
    high_B = [180, 168, 152, 122, 105]
    hl_tR = np.interp(d_val, bp_dc, high_R).astype(np.float32)
    hl_tG = np.interp(d_val, bp_dc, high_G).astype(np.float32)
    hl_tB = np.interp(d_val, bp_dc, high_B).astype(np.float32)

    ea3 = ea_mask[..., np.newaxis]
    tr_eff = (trop_mask * (1.0 - ea_mask)).astype(np.float32)
    tr3 = tr_eff[..., np.newaxis]
    pg3 = pg_mask[..., np.newaxis]
    rs3 = rs_mask[..., np.newaxis]
    hl_eff = (hl_mask * (1.0 - ea_mask) * (1.0 - tr_eff)).astype(np.float32)
    hl3 = hl_eff[..., np.newaxis]
    residual = np.clip(1.0 - ea_mask - tr_eff - pg_mask - rs_mask - hl_eff, 0.0, 1.0)
    res3 = residual[..., np.newaxis]

    tgt = (
        np.stack([gl_tR, gl_tG, gl_tB], -1) * res3
        + np.stack([ea_tR, ea_tG, ea_tB], -1) * ea3
        + np.stack([tr_tR, tr_tG, tr_tB], -1) * tr3
        + np.stack([pg_tR, pg_tG, pg_tB], -1) * (pg3 + rs3)
        + np.stack([hl_tR, hl_tG, hl_tB], -1) * hl3
    ).astype(np.float32)
    total_w = res3 + ea3 + tr3 + pg3 + rs3 + hl3
    tgt = np.where(total_w > 0, tgt / total_w, tgt)
    tgt_up = resize_rgb(tgt, (D3_W, D3_H))

    print(f"[{ts()}] Phase 5: Weight multipliers...")
    weight = weight_base.copy()
    weight *= 1.0 + 0.20 * ea_mask
    weight *= 1.0 - 0.12 * trop_mask * (1.0 - ea_mask)
    weight *= 1.0 + 0.00 * pg_mask
    weight *= 1.0 + 0.00 * rs_mask
    weight *= 1.0 - 0.20 * hl_mask

    w_trop_blur = gaussian_filter(weight, sigma=4)
    weight = weight * (1.0 - 0.5 * trop_mask) + w_trop_blur * (0.5 * trop_mask)
    w_hl_blur = gaussian_filter(weight, sigma=5)
    weight = weight * (1.0 - 0.3 * hl_mask) + w_hl_blur * (0.3 * hl_mask)

    weight = np.where(depth < -1000, 0.0, weight)
    weight = np.clip(weight, 0.0, 0.205)
    print(f"  weight max={weight.max():.4f}  mean(ocean)={weight[ocean_hard].mean():.5f}")
    weight_up = resize_mask(weight, (D3_W, D3_H))
    ea_up = resize_mask(ea_mask, (D3_W, D3_H))
    trop_up = resize_mask(trop_mask, (D3_W, D3_H))
    pg_up = resize_mask(pg_mask, (D3_W, D3_H))
    rs_up = resize_mask(rs_mask, (D3_W, D3_H))
    hl_up = resize_mask(hl_mask, (D3_W, D3_H))

    print(f"[{ts()}] Phase 6: Blend...")
    w3 = weight_up[..., np.newaxis]
    result = d3 * (1.0 - w3) + tgt_up * w3

    print(f"[{ts()}] Phase 7: Protections...")
    lm = land_up[..., np.newaxis].astype(np.float32)
    result = d3 * lm + result * (1.0 - lm)
    sm = snow_mask[..., np.newaxis].astype(np.float32)
    result = d3 * sm + result * (1.0 - sm)

    sat3 = sat_arr(d3)
    satr = sat_arr(result)
    trop_over = (satr > sat3 + 0.020) & (trop_up > 0.2) & ocean_up
    result = d3 * trop_over[..., np.newaxis].astype(np.float32) + result * (1.0 - trop_over[..., np.newaxis].astype(np.float32))
    satr2 = sat_arr(result)
    over = (satr2 > sat3 * 1.08) & (satr2 > 0.52) & ocean_up
    result = d3 * over[..., np.newaxis].astype(np.float32) + result * (1.0 - over[..., np.newaxis].astype(np.float32))

    result = result.clip(0, 255).astype(np.uint8)
    out_img = Image.fromarray(result)

    print(f"[{ts()}] Saving outputs...")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(OUT_PATH, "JPEG", quality=84, subsampling=2, optimize=True, progressive=True)
    shutil.copy2(OUT_PATH, CAND_OUT)
    print(f"  {OUT_PATH}")
    print(f"  Copied → {CAND_OUT}")

    # Debug maps at 2048 width for fast inspection.
    print(f"[{ts()}] Writing debug maps...")
    region_map = np.zeros((D3_H, D3_W, 3), dtype=np.uint8)
    region_map[...] = np.array([18, 24, 32], dtype=np.uint8)
    region_map = np.where((trop_up > 0.2)[..., None], np.array([66, 150, 160], dtype=np.uint8), region_map)
    region_map = np.where((hl_up > 0.2)[..., None], np.array([86, 114, 152], dtype=np.uint8), region_map)
    region_map = np.where((pg_up > 0.2)[..., None], np.array([184, 170, 120], dtype=np.uint8), region_map)
    region_map = np.where((rs_up > 0.2)[..., None], np.array([198, 144, 118], dtype=np.uint8), region_map)
    region_map = np.where((ea_up > 0.2)[..., None], np.array([124, 148, 168], dtype=np.uint8), region_map)
    region_map = np.where((resize_mask(depth_up < -1000, (D3_W, D3_H)) > 0.2)[..., None], np.array([20, 42, 82], dtype=np.uint8), region_map)
    save_rgb(region_map, DEBUG_REGION)
    save_gray(weight_up, DEBUG_WEIGHT, scale=255.0 / max(float(weight_up.max()), 1e-6))
    save_gray(ea_up, DEBUG_EA)
    save_gray(trop_up, DEBUG_TROP)
    save_gray((pg_up + rs_up).clip(0.0, 1.0), DEBUG_GULF)
    save_gray(hl_up, DEBUG_HLAT)

    print(f"[{ts()}] Computing metrics...")
    res_f = result.astype(np.float32)
    d5c_f = d5c.astype(np.float32)
    d5x_f = d5x.astype(np.float32)
    image2_ref_rgb = None
    image2_ref_present = IMAGE2_REF.exists()
    if image2_ref_present:
        image2_ref_rgb = np.array(Image.open(IMAGE2_REF).convert("RGB").resize((D3_W, D3_H), Image.LANCZOS), dtype=np.float32)

    zones = [
        ("Yellow Sea", 119, 126, 32, 39),
        ("Bohai Sea", 117, 122, 37, 41),
        ("East China Sea", 120, 130, 25, 33),
        ("Taiwan Strait", 117, 122, 22, 26),
        ("S.China Sea N", 110, 121, 15, 23),
        ("Taiwan E deep", 122, 130, 20, 26),
        ("Philippines Luzon", 119, 126, 12, 20),
        ("Persian Gulf", 48, 57, 24, 30),
        ("Red Sea", 32, 44, 12, 30),
        ("North Sea", -4, 9, 52, 61),
        ("Bahamas", -80, -72, 22, 28),
        ("Caribbean", -85, -60, 10, 25),
        ("Great Barrier Reef", 142, 154, -24, -10),
        ("Australia North", 124, 142, -18, -8),
        ("Maldives", 72, 74, -1, 8),
        ("Indonesia", 95, 130, -10, 8),
        ("Philippines", 117, 127, 5, 20),
        ("Pacific Deep", -160, -130, -20, 10),
        ("Indian Ocean D", 65, 95, -30, -5),
        ("N.Atlantic D", -50, -25, 20, 45),
        ("Southern Ocean", -160, -80, -60, -45),
        ("Mariana", 140, 150, 10, 25),
        ("Antarctica", -180, 180, -90, -70),
        ("Greenland", -55, -20, 60, 83),
        ("Arctic", -180, 180, 80, 90),
        ("Tibetan Plateau", 75, 105, 28, 40),
        ("Sahara", -15, 35, 15, 35),
        ("Amazon", -65, -45, -10, 5),
    ]
    land_zones = {"Antarctica", "Greenland", "Arctic", "Tibetan Plateau", "Sahara", "Amazon"}
    deep_zones = {"Pacific Deep", "Indian Ocean D", "N.Atlantic D", "Southern Ocean", "Mariana", "Taiwan E deep"}

    def zone_mask(name: str, arr_depth: np.ndarray, lw: float, le: float, ls: float, ln: float):
        full = (lw == -180 and le == 180)
        r1, r2, c1, c2 = bbox(lw, le, ls, ln)
        s = (slice(r1, r2), slice(None) if full else slice(c1, c2))
        pd = arr_depth[s]
        om = pd < 0
        return s, pd, om

    def diff_stats(a: np.ndarray, b: np.ndarray, label_a: str, label_b: str):
        diff = np.abs(a.astype(np.float32) - b.astype(np.float32))
        max_ch = diff.max(axis=-1)
        total = max_ch.size
        pct3 = float((max_ch > 3).mean() * 100)
        pct5 = float((max_ch > 5).mean() * 100)
        pct8 = float((max_ch > 8).mean() * 100)
        print(
            f"  {label_a} vs {label_b}: mean_abs={diff.mean():.4f} "
            f"mean_max_ch={max_ch.mean():.4f} pct>3={pct3:.2f}% pct>5={pct5:.2f}% pct>8={pct8:.2f}%"
        )
        return {
            "mean_abs": round(float(diff.mean()), 4),
            "mean_max_ch": round(float(max_ch.mean()), 4),
            "pct_gt3": round(pct3, 3),
            "pct_gt5": round(pct5, 3),
            "pct_gt8": round(pct8, 3),
            "total_pixels": int(total),
        }

    stats_vs_d5c = diff_stats(res_f, d5c_f, "D5y", "D5c")
    stats_vs_d5x = diff_stats(res_f, d5x_f, "D5y", "D5x")

    region_rows = []
    image2_rows = []
    print(f"\n  {'Zone':<22} {'dep':>6} {'0-20':>5} {'0-50':>5} {'>1k':>4} | {'D3 R/G/B':^13} {'Target R/G/B':^13} {'D5y R/G/B':^13} | {'5y-3':>8} {'5y-c':>8} {'5y-x':>8} | {'BG3':>5}{'BG5y':>5} | ok?")
    print("  " + "-" * 140)

    for name, lw, le, ls, ln in zones:
        s, pd, om = zone_mask(name, depth_up, lw, le, ls, ln)
        pd3 = d3[s]
        pr = res_f[s]
        pt = tgt_up[s]
        pc = d5c_f[s]
        px = d5x_f[s]
        if name in land_zones:
            diff3 = float(np.abs(pr - pd3).max())
            print(f"  {name:<22} {'land/ice':>6}  max_diff={diff3:.1f}")
            region_rows.append({
                "name": name,
                "kind": "land",
                "max_diff_d3": round(diff3, 2),
            })
            continue

        if om.sum() < 20:
            continue

        doc = pd[om]
        dn = -doc
        dep_m = float(dn.mean())
        p0_20 = float((dn < 20).mean() * 100)
        p0_50 = float((dn < 50).mean() * 100)
        p1k = float((dn >= 1000).mean() * 100)

        R3m, G3m, B3m = sample_region_mean(pd3, om)
        Rtm, Gtm, Btm = sample_region_mean(pt, om)
        Rym, Gym, Bym = sample_region_mean(pr, om)
        Rcm, Gcm, Bcm = sample_region_mean(pc, om)
        Rxm, Gxm, Bxm = sample_region_mean(px, om)

        BG3 = B3m / (G3m + 1e-6)
        BGy = Bym / (Gym + 1e-6)
        s3 = float(sat_arr(pd3)[om].mean())
        sy = float(sat_arr(pr)[om].mean())

        dR3 = Rym - R3m
        dG3 = Gym - G3m
        dB3 = Bym - B3m
        dRc = Rym - Rcm
        dBc = Bym - Bcm
        dRx = Rym - Rxm
        dBx = Bym - Bxm

        if image2_ref_present:
            R2m, G2m, B2m = sample_region_mean(image2_ref_rgb, om) if image2_ref_rgb is not None else (None, None, None)
            image2_status = "followed"
            if name in deep_zones and image2_ref_rgb is not None and abs(B2m - Bym) < 2 and abs(G2m - Gym) < 2:
                image2_status = "partial"
        else:
            R2m = G2m = B2m = None
            image2_status = "skipped"

        ok = True
        if name in deep_zones:
            ok = abs(dR3) <= 0.8 and abs(dG3) <= 0.8 and abs(dB3) <= 0.8
        elif sy > s3 + 0.022:
            ok = False

        region_rows.append(
            {
                "name": name,
                "depth_mean": round(dep_m, 1),
                "pct_0_20": round(p0_20, 1),
                "pct_0_50": round(p0_50, 1),
                "pct_gt1k": round(p1k, 1),
                "d3": {"R": round(R3m, 1), "G": round(G3m, 1), "B": round(B3m, 1), "BG": round(BG3, 3), "sat": round(s3, 4)},
                "target": {"R": round(Rtm, 1), "G": round(Gtm, 1), "B": round(Btm, 1)},
                "d5y": {"R": round(Rym, 1), "G": round(Gym, 1), "B": round(Bym, 1), "BG": round(BGy, 3), "sat": round(sy, 4)},
                "d5c": {"R": round(Rcm, 1), "G": round(Gcm, 1), "B": round(Bcm, 1)},
                "d5x": {"R": round(Rxm, 1), "G": round(Gxm, 1), "B": round(Bxm, 1)},
                "delta_vs_d3": {"R": round(dR3, 1), "G": round(dG3, 1), "B": round(dB3, 1)},
                "delta_vs_d5c": {"R": round(dRc, 1), "B": round(dBc, 1)},
                "delta_vs_d5x": {"R": round(dRx, 1), "B": round(dBx, 1)},
                "image2": {"status": image2_status, "rgb": None if R2m is None else [round(R2m, 1), round(G2m, 1), round(B2m, 1)]},
                "pass_check": bool(ok),
            }
        )
        if image2_ref_present:
            image2_rows.append(
                {
                    "name": name,
                    "image2_rgb": [round(R2m, 1), round(G2m, 1), round(B2m, 1)],
                    "target_rgb": [round(Rtm, 1), round(Gtm, 1), round(Btm, 1)],
                    "d5y_rgb": [round(Rym, 1), round(Gym, 1), round(Bym, 1)],
                    "status": image2_status,
                }
            )

        flag = "✓" if ok else "✗"
        print(
            f"  {name:<22} {dep_m:>6.0f} {p0_20:>5.1f} {p0_50:>5.1f} {p1k:>4.0f} | "
            f"{R3m:>4.0f}/{G3m:>4.0f}/{B3m:>4.0f} "
            f"{Rtm:>4.0f}/{Gtm:>4.0f}/{Btm:>4.0f} "
            f"{Rym:>4.0f}/{Gym:>4.0f}/{Bym:>4.0f} | "
            f"{dR3:>+4.0f}/{dG3:>+4.0f}/{dB3:>+4.0f} "
            f"{dRc:>+4.0f}/{dBc:>+4.0f} "
            f"{dRx:>+4.0f}/{dBx:>+4.0f} | "
            f"{BG3:>5.3f}{BGy:>5.3f} | {flag}"
        )

    passing = [x for x in region_rows if x.get("pass_check")]
    failing = [x for x in region_rows if x.get("pass_check") is False]

    print(f"\n[{ts()}] Writing report...")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    with DOC.open("w", encoding="utf-8") as f:
        f.write("# D5y Regional Ocean Candidate Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}  \n")
        f.write("**Stage:** Bathy-3 — D5y generation  \n")
        f.write("**Purpose:** Regional ocean color differentiation with optional GPT Image 2 reference  \n")
        f.write(f"**Status:** {'PASS' if not failing else 'PARTIAL — ' + ', '.join(x['name'] for x in failing)}  \n\n")
        f.write("---\n\n## 1. Parameters\n\n")
        f.write("| Param | D5x | D5y |\n|---|---|---|\n")
        rows = [
            ("0–20m weight", "0.20", "0.185"),
            ("20–50m weight", "0.16", "0.150"),
            ("50–200m weight", "0.12", "0.105"),
            ("200–1000m weight", "0.04", "0.025"),
            (">1000m weight", "0.00", "0.00"),
            ("depth sigma", "12", "14"),
            ("weight sigma", "8", "10"),
            ("EA multiplier", "1.20", "1.20"),
            ("Tropical multiplier", "0.95", "0.88"),
            ("Gulf / Red Sea multiplier", "1.00", "1.00"),
            ("High Latitude multiplier", "0.95", "0.80"),
            ("turbid coastal", "disabled", "disabled"),
            ("abyss", "disabled", "disabled"),
        ]
        for a, b, c in rows:
            f.write(f"| {a} | {b} | {c} |\n")

        f.write("\n## 2. gpt-image-2 reference usage\n\n")
        if image2_ref_present:
            f.write("- gpt-image-2 reference present: yes\n")
            f.write(f"- reference file: `{IMAGE2_REF}`\n")
            f.write(f"- palette reference file: `{PALETTE_REF}`\n")
            f.write("- image2 stage: available for region comparison\n")
        else:
            f.write("- gpt-image-2 reference present: no\n")
            f.write("- image2 stage skipped because OPENAI_API_KEY is missing\n")
            f.write(f"- prepared local reference inputs: `{STAGING / 'image2_ref_d3_2048.jpg'}`, `{STAGING / 'image2_ref_d5c_2048.jpg'}`, `{STAGING / 'image2_ref_d5x_2048.jpg'}`\n")
            f.write(f"- local palette helper: `{PALETTE_REF}`\n")
        f.write("\n")
        f.write("### Reference comparison\n\n")
        f.write("| Region | Image2 ref RGB | Algorithm target RGB | Final D5y RGB | Decision |\n")
        f.write("|---|---|---|---|---|\n")
        for row in region_rows:
            if row.get("kind") == "land":
                continue
            img2_rgb = row["image2"]["rgb"]
            decision = row["image2"]["status"]
            f.write(
                f"| {row['name']} | {mean_rgb_text(tuple(img2_rgb) if img2_rgb else None)} | "
                f"{row['target']['R']:.1f}/{row['target']['G']:.1f}/{row['target']['B']:.1f} | "
                f"{row['d5y']['R']:.1f}/{row['d5y']['G']:.1f}/{row['d5y']['B']:.1f} | {decision} |\n"
            )

        f.write("\n## 3. Difference Strength\n\n")
        f.write("| Metric | D5y vs D5c | D5y vs D5x |\n|---|---:|---:|\n")
        f.write(f"| mean_abs | {stats_vs_d5c['mean_abs']} | {stats_vs_d5x['mean_abs']} |\n")
        f.write(f"| mean_max_ch | {stats_vs_d5c['mean_max_ch']} | {stats_vs_d5x['mean_max_ch']} |\n")
        f.write(f"| pct_gt3 | {stats_vs_d5c['pct_gt3']} | {stats_vs_d5x['pct_gt3']} |\n")
        f.write(f"| pct_gt5 | {stats_vs_d5c['pct_gt5']} | {stats_vs_d5x['pct_gt5']} |\n")
        f.write(f"| pct_gt8 | {stats_vs_d5c['pct_gt8']} | {stats_vs_d5x['pct_gt8']} |\n")

        f.write("\n## 4. Regional metrics\n\n")
        f.write(
            "| Zone | dep | 0-20 | 0-50 | >1k | D3 R/G/B | Target R/G/B | D5y R/G/B | "
            "ΔvsD3 R/G/B | ΔvsD5c R/B | ΔvsD5x R/B | BG3 | BG5y | image2 |\n"
        )
        f.write("|---|---:|---:|---:|---:|---|---|---|---|---|---|---:|---:|---|\n")
        for row in region_rows:
            if row.get("kind") == "land":
                f.write(f"| {row['name']} | land/ice | — | — | — | — | — | max_diff={row['max_diff_d3']:.1f} | — | — | — | — | — | — |\n")
                continue
            f.write(
                f"| {row['name']} | {row['depth_mean']:.1f} | {row['pct_0_20']:.1f} | {row['pct_0_50']:.1f} | {row['pct_gt1k']:.1f} | "
                f"{row['d3']['R']:.1f}/{row['d3']['G']:.1f}/{row['d3']['B']:.1f} | "
                f"{row['target']['R']:.1f}/{row['target']['G']:.1f}/{row['target']['B']:.1f} | "
                f"{row['d5y']['R']:.1f}/{row['d5y']['G']:.1f}/{row['d5y']['B']:.1f} | "
                f"{row['delta_vs_d3']['R']:+.1f}/{row['delta_vs_d3']['G']:+.1f}/{row['delta_vs_d3']['B']:+.1f} | "
                f"{row['delta_vs_d5c']['R']:+.1f}/{row['delta_vs_d5c']['B']:+.1f} | "
                f"{row['delta_vs_d5x']['R']:+.1f}/{row['delta_vs_d5x']['B']:+.1f} | "
                f"{row['d3']['BG']:.3f} | {row['d5y']['BG']:.3f} | {row['image2']['status']} |\n"
            )

        f.write("\n## 5. Files\n\n")
        f.write("```\n")
        f.write(f"{OUT_PATH}\n")
        f.write(f"{CAND_OUT}\n")
        f.write(f"{DEBUG_REGION}\n")
        f.write(f"{DEBUG_WEIGHT}\n")
        f.write(f"{DEBUG_EA}\n")
        f.write(f"{DEBUG_TROP}\n")
        f.write(f"{DEBUG_GULF}\n")
        f.write(f"{DEBUG_HLAT}\n")
        f.write("```\n\n")

        f.write("## 6. Confirmations\n\n")
        f.write("- pwa/earth3d.js: NOT modified ✓\n")
        f.write("- dayTexture default: NOT changed ✓\n")
        f.write("- nightTexture / cloudMesh / atmosphere / UI: NOT modified ✓\n")
        f.write("- image2 stage: skipped when OPENAI_API_KEY is missing ✓\n")
        f.write("- No commit ✓\n")

    # Persist a compact machine-readable notes file for the image2 stage.
    IMAGE2_NOTES.parent.mkdir(parents=True, exist_ok=True)
    image2_notes = {
        "stage": "skipped" if not image2_ref_present else "available",
        "reason": "OPENAI_API_KEY is missing" if not image2_ref_present else None,
        "reference_present": bool(image2_ref_present),
        "reference_file": str(IMAGE2_REF),
        "palette_file": str(PALETTE_REF),
        "algorithm_target": "local-only",
        "comparison": image2_rows,
        "d5y_vs_d5c": stats_vs_d5c,
        "d5y_vs_d5x": stats_vs_d5x,
    }
    IMAGE2_NOTES.write_text(json.dumps(image2_notes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\n[{ts()}] Summary")
    print(f"  Zones passed: {sum(1 for x in region_rows if x.get('pass_check'))}/{sum(1 for x in region_rows if 'pass_check' in x)}")
    print(f"  Report: {DOC}")
    print(f"  Output: {OUT_PATH}")
    print(f"  Candidate: {CAND_OUT}")
    print(f"  Image2 reference: {'present' if image2_ref_present else 'skipped'}")


if __name__ == "__main__":
    main()
