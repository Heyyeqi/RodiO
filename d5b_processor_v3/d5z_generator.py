#!/usr/bin/env python3
"""
D5z Candidate Generation — Standalone correction pass on d5b_design_v3_2_1 baseline.

PROHIBITIONS (enforced):
  - Does NOT modify earth3d.js or DAY_TEXTURE_VARIANT
  - Does NOT write to pwa/assets/earth/production/ or pwa/assets/earth/candidates/
  - Does NOT commit
  - Output ONLY to: d5b_processor_v3/d5b_output/d5z_candidates/
  - D5z is NOT a final master, NOT production

Candidates:
  d5z_a — conservative: polar compress + deep ocean desaturate
  d5z_b — balanced:     d5z_a + Sahara/Arabia mild darken + Color Harmony Guard
"""

import os, sys, json, math
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from pathlib import Path
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
INPUT_PATH = REPO_ROOT / "pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg"
OUT_DIR    = REPO_ROOT / "d5b_processor_v3/d5b_output/d5z_candidates"
CROPS_DIR  = OUT_DIR / "compare_crops"

# Safety assertions — never touch production or candidates
assert "production" not in str(OUT_DIR)
assert str(OUT_DIR) != str(REPO_ROOT / "pwa/assets/earth/candidates")

# ── Region definitions ────────────────────────────────────────────────────────
PROTECTED = {
    "japan":           dict(lat_min=30,  lat_max=46,  lon_min=128, lon_max=148),
    "mediterranean":   dict(lat_min=30,  lat_max=48,  lon_min=-10, lon_max=42),
    "caribbean":       dict(lat_min=10,  lat_max=28,  lon_min=-90, lon_max=-60),
    "pacific_islands": dict(lat_min=-15, lat_max=20,  lon_min=-180,lon_max=-120),
}

# For compare crops: (center lon, center lat, crop_w, crop_h) from full-res image
CROP_SPECS = {
    "antarctica":      dict(lon=0,    lat=-75, w=640, h=320),
    "greenland":       dict(lon=-42,  lat=72,  w=640, h=320),
    "sahara":          dict(lon=20,   lat=25,  w=640, h=320),
    "indian_ocean":    dict(lon=75,   lat=-15, w=640, h=320),
    "japan":           dict(lon=136,  lat=37,  w=640, h=320),
    "mediterranean":   dict(lon=16,   lat=39,  w=640, h=320),
    "caribbean":       dict(lon=-75,  lat=18,  w=640, h=320),
    "pacific_islands": dict(lon=-155, lat=5,   w=640, h=320),
}


# ── Grid helpers ──────────────────────────────────────────────────────────────
def build_grids(h, w):
    lat = np.linspace(90, -90, h, dtype=np.float32)
    lon = np.linspace(-180, 180, w, dtype=np.float32)
    LON, LAT = np.meshgrid(lon, lat)
    return LAT, LON


def region_mask(LAT, LON, lat_min, lat_max, lon_min, lon_max, feather_px=0):
    """Build float32 [0,1] mask; handles cross-meridian (lon_max > 180)."""
    if lon_max > 180:
        wrap = lon_max - 360
        m = (LAT >= lat_min) & (LAT <= lat_max) & (
            ((LON >= lon_min) & (LON <= 180)) | ((LON >= -180) & (LON <= wrap))
        )
    else:
        m = (LAT >= lat_min) & (LAT <= lat_max) & (LON >= lon_min) & (LON <= lon_max)
    mask = m.astype(np.float32)
    if feather_px > 0:
        pil_m = Image.fromarray((mask * 255).astype(np.uint8))
        pil_m = pil_m.filter(ImageFilter.GaussianBlur(radius=feather_px))
        mask = np.array(pil_m, dtype=np.float32) / 255.0
    return mask


# ── Pixel classifiers ─────────────────────────────────────────────────────────
def luminance(f32):
    return f32[:,:,0]*0.299 + f32[:,:,1]*0.587 + f32[:,:,2]*0.114


def sat_hsv(f32):
    mx = f32.max(axis=2)
    mn = f32.min(axis=2)
    return np.where(mx > 1e-6, (mx - mn) / mx, 0.0)


def deep_ocean_px(f32):
    """True for clearly deep-ocean pixels: dark blue, not coastal transition."""
    R, G, B = f32[:,:,0], f32[:,:,1], f32[:,:,2]
    return ((R < 80) & (B > 85) & (B > R + 30) & (G < B * 0.65)).astype(np.float32)


def land_px(f32):
    """True for non-ocean, non-ice pixels."""
    R, G, B = f32[:,:,0], f32[:,:,1], f32[:,:,2]
    is_ocean = (B > R + 20) & (B > G + 10) & (R < 100)
    is_ice   = (R > 220) & (G > 220) & (B > 220)
    return (~is_ocean & ~is_ice).astype(np.float32)


def ice_px(f32):
    """True for snow/ice pixels: near-white and near-neutral (low channel spread)."""
    lum    = luminance(f32)
    spread = f32.max(axis=2) - f32.min(axis=2)
    return ((lum > 155) & (spread < 55)).astype(np.float32)


# ════════════════════════════════════════════════════════════════════════════
# CORRECTION A — Polar ice brightness scaling (both poles)
#
# Replaces threshold-compress approach (which only moved pixels by 1-3 units).
# Direct multiplicative scaling on ice pixels, smooth 5° latitude transition.
# South: 0.87 (13% reduction) at lat<-70°; North: 0.90 (10% reduction) at lat>70°
# ════════════════════════════════════════════════════════════════════════════
def polar_compress(f32, LAT):
    out = f32.copy()
    ice = ice_px(f32)  # detect from original (not out, so ice map stays stable)

    # Each entry: (outer_lat, inner_lat, scale_factor)
    # outer = deep polar = full strength; inner = boundary = zero strength
    # transition width = |outer - inner| degrees
    for outer, inner, sf in [
        (-70, -65, 0.87),   # South pole ice: full scale at lat<-70°, ramp to 0 at lat=-65°
        ( 70,  65, 0.90),   # North pole ice: full scale at lat>70°, ramp to 0 at lat=65°
    ]:
        if outer < 0:
            strength = np.clip((inner - LAT) / abs(inner - outer), 0.0, 1.0)
        else:
            strength = np.clip((LAT - inner) / abs(outer - inner), 0.0, 1.0)

        # blend = how much to scale this pixel (ice pixels only, zone-weighted)
        blend = (ice * strength)[:, :, np.newaxis]
        # new = original * (1 - blend*(1-sf))  →  full ice+zone → original*sf
        out = out * (1.0 - blend * (1.0 - sf))

    return np.clip(out, 0, 255)


# ════════════════════════════════════════════════════════════════════════════
# CORRECTION B — Deep ocean desaturate + mild brightness reduction
# ════════════════════════════════════════════════════════════════════════════
def deep_ocean_desaturate(f32, LAT, LON):
    out = f32.copy()
    deep = deep_ocean_px(f32)
    for lat_min, lat_max, lon_min, lon_max in [
        (-30, 15,  50, 110),   # Indian Ocean central
        (-45,  0, 160, 230),   # Pacific deep (cross-meridian 160E–130W)
    ]:
        rm   = region_mask(LAT, LON, lat_min, lat_max, lon_min, lon_max, feather_px=20)
        dm3  = (deep * rm)[:, :, np.newaxis]
        lum  = luminance(out)[:, :, np.newaxis]
        desat = out * 0.93 + lum * 0.07   # reduce chroma ~7%
        corrected = desat * 0.97           # reduce brightness ~3%
        out = out * (1 - dm3) + corrected * dm3
    return np.clip(out, 0, 255)


# ════════════════════════════════════════════════════════════════════════════
# CORRECTION C — Sahara / Arabia mild land darken (D5z_b only)
# ════════════════════════════════════════════════════════════════════════════
def sahara_land_darken(f32, LAT, LON):
    out = f32.copy()
    land = land_px(f32)
    # Hard exclusion: Mediterranean protected zone — no feather
    med_excl = region_mask(LAT, LON, 30, 48, -10, 42, feather_px=0)
    for lat_min, lat_max, lon_min, lon_max in [
        (15, 35, -15, 45),   # Sahara / Egypt
        (10, 32,  35, 65),   # Arabian Peninsula
    ]:
        rm   = region_mask(LAT, LON, lat_min, lat_max, lon_min, lon_max, feather_px=10)
        safe = rm * (1.0 - med_excl)
        apply3 = (land * safe)[:, :, np.newaxis]
        out = out * (1 - apply3) + (out * 0.97) * apply3
    return np.clip(out, 0, 255)


# ════════════════════════════════════════════════════════════════════════════
# COLOR HARMONY GUARD — D5z_b post-process
# ════════════════════════════════════════════════════════════════════════════
def color_harmony_guard(d5zb_f32, baseline_f32, LAT, LON):
    result = d5zb_f32.copy()
    log = {"regions": {}, "global": {}}

    for name, bounds in PROTECTED.items():
        rm  = region_mask(LAT, LON, **bounds, feather_px=0)
        npx = int(rm.sum())
        if npx < 100:
            continue
        rm3 = rm[:, :, np.newaxis]

        mean_rgb_diff = float((np.abs(result - baseline_f32).mean(axis=2) * rm).sum() / npx)
        mean_br_diff  = float((np.abs(luminance(result) - luminance(baseline_f32)) * rm).sum() / npx)
        activated = mean_rgb_diff > 2.0 or mean_br_diff > 2.0

        if activated:
            excess = max(mean_rgb_diff / 2.0, mean_br_diff / 2.0)
            blend_back = min((excess - 1.0) * 0.5, 0.8)
            blended = result * (1.0 - blend_back) + baseline_f32 * blend_back
            result  = result * (1 - rm3) + blended * rm3
            after_rgb = float((np.abs(result - baseline_f32).mean(axis=2) * rm).sum() / npx)
            after_br  = float((np.abs(luminance(result) - luminance(baseline_f32)) * rm).sum() / npx)
        else:
            after_rgb, after_br = mean_rgb_diff, mean_br_diff

        log["regions"][name] = {
            "before_rgb_diff": round(mean_rgb_diff, 3),
            "before_br_diff":  round(mean_br_diff,  3),
            "activated":       activated,
            "after_rgb_diff":  round(after_rgb, 3),
            "after_br_diff":   round(after_br,  3),
        }

    base_lum   = float(luminance(baseline_f32).mean())
    result_lum = float(luminance(result).mean())
    global_br_chg_pct = abs(result_lum - base_lum) / (base_lum + 1e-6) * 100
    log["global"]["brightness_change_pct"] = round(global_br_chg_pct, 3)
    log["global"]["within_2pct_limit"]     = global_br_chg_pct <= 2.0

    return np.clip(result, 0, 255), log


# ════════════════════════════════════════════════════════════════════════════
# METRICS
# ════════════════════════════════════════════════════════════════════════════
def compute_metrics(cand_f32, base_f32, LAT, LON, name):
    m = {"candidate": name, "generated": datetime.now().isoformat()}

    def lum_stats(rm):
        npx = rm.sum()
        if npx < 100:
            return None
        bl = float((luminance(base_f32) * rm).sum() / npx)
        cl = float((luminance(cand_f32) * rm).sum() / npx)
        return {"baseline_L": round(bl, 2), "candidate_L": round(cl, 2),
                "change_pct": round((cl - bl) / (bl + 1e-6) * 100, 2)}

    # Polar brightness — ice pixels only (avoids dilution by dark ocean in zone)
    ice = ice_px(base_f32)
    for key, lat_min, lat_max in [("antarctica_ice", -90, -65), ("greenland_ice", 65, 90)]:
        zm  = region_mask(LAT, LON, lat_min, lat_max, -180, 180)
        ice_zone = ice * zm
        m[key] = lum_stats(ice_zone)

    # Also whole-zone brightness for reference
    m["antarctica"] = lum_stats(region_mask(LAT, LON, -90, -60, -180, 180))
    m["greenland"]  = lum_stats(region_mask(LAT, LON,  60,  90, -180, 180))

    # Sahara land brightness
    sr = region_mask(LAT, LON, 15, 35, -15, 45)
    sl = land_px(base_f32) * sr
    m["sahara"] = lum_stats(sl) if sl.sum() > 100 else None

    # Indian Ocean deep saturation
    io_rm = region_mask(LAT, LON, -30, 15, 50, 110)
    io_d  = deep_ocean_px(base_f32) * io_rm
    npx   = io_d.sum()
    if npx > 100:
        sb = float((sat_hsv(base_f32) * io_d).sum() / npx)
        sc = float((sat_hsv(cand_f32) * io_d).sum() / npx)
        m["indian_ocean_deep_sat"] = {
            "baseline_S": round(sb, 4), "candidate_S": round(sc, 4),
            "change_pct": round((sc - sb) / (sb + 1e-6) * 100, 2),
        }

    # Polar gray check (channel balance)
    m["polar_gray_check"] = {}
    for pole, lat_min, lat_max in [("south", -90, -65), ("north", 65, 90)]:
        pm  = region_mask(LAT, LON, lat_min, lat_max, -180, 180)
        npx = int(pm.sum())
        if npx < 100:
            continue
        def ch_spread(f):
            R = float((f[:,:,0] * pm).sum() / npx)
            G = float((f[:,:,1] * pm).sum() / npx)
            B = float((f[:,:,2] * pm).sum() / npx)
            return round(max(R,G,B) - min(R,G,B), 2), round(R,1), round(G,1), round(B,1)
        b_sp, bR, bG, bB = ch_spread(base_f32)
        c_sp, cR, cG, cB = ch_spread(cand_f32)
        m["polar_gray_check"][pole] = {
            "baseline":  {"channel_spread": b_sp, "R": bR, "G": bG, "B": bB},
            "candidate": {"channel_spread": c_sp, "R": cR, "G": cG, "B": cB},
            "spread_delta": round(c_sp - b_sp, 2),
            "gray_check_pass": (c_sp - b_sp) < 5,  # spread must not significantly increase
        }

    # Protected region regression
    m["protected"] = {}
    for pname, bounds in PROTECTED.items():
        rm  = region_mask(LAT, LON, **bounds)
        npx = int(rm.sum())
        if npx < 100:
            m["protected"][pname] = {"error": "no pixels"}
            continue
        rm3  = rm[:, :, np.newaxis]
        mse  = float(((cand_f32 - base_f32)**2 * rm3).sum() / (npx * 3))
        psnr = round(10 * math.log10(255**2 / mse), 2) if mse > 1e-8 else 999.0
        rgb_diff = float((np.abs(cand_f32 - base_f32).mean(axis=2) * rm).sum() / npx)
        br_diff  = float((np.abs(luminance(cand_f32) - luminance(base_f32)) * rm).sum() / npx)
        m["protected"][pname] = {
            "PSNR_dB":       psnr,
            "mean_rgb_diff": round(rgb_diff, 3),
            "mean_br_diff":  round(br_diff, 3),
            "PSNR_pass":     psnr >= 42.0,
            "rgb_diff_pass": rgb_diff <= 2.0,
            "br_diff_pass":  br_diff <= 2.0,
            "all_pass":      psnr >= 42.0 and rgb_diff <= 2.0 and br_diff <= 2.0,
        }

    return m


# ════════════════════════════════════════════════════════════════════════════
# COMPARE CROPS
# ════════════════════════════════════════════════════════════════════════════
def extract_crop(arr, lon, lat, w, h):
    H, W = arr.shape[:2]
    cx = int((lon + 180) / 360 * W)
    cy = int((90 - lat) / 180 * H)
    x0, x1 = cx - w//2, cx + w//2
    y0, y1 = cy - h//2, cy + h//2
    pad_l, pad_r = max(0, -x0), max(0, x1 - W)
    pad_t, pad_b = max(0, -y0), max(0, y1 - H)
    crop = arr[max(0,y0):min(H,y1), max(0,x0):min(W,x1)]
    if pad_l or pad_r or pad_t or pad_b:
        crop = np.pad(crop, ((pad_t,pad_b),(pad_l,pad_r),(0,0)), mode='edge')
    return crop


def make_compare_crop(base_arr, a_arr, b_arr, region_name, spec):
    lon, lat, w, h = spec['lon'], spec['lat'], spec['w'], spec['h']
    panels = [
        ("baseline (d5b_design_v3_2_1)", base_arr),
        ("D5z_a (conservative)",         a_arr),
        ("D5z_b (balanced)",             b_arr),
    ]
    label_h = 26
    gap     = 3
    total_w = w * 3 + gap * 2
    total_h = h + label_h
    canvas = Image.new("RGB", (total_w, total_h), (20, 20, 20))
    draw   = ImageDraw.Draw(canvas)
    for i, (label, arr) in enumerate(panels):
        crop = extract_crop(arr, lon, lat, w, h)
        x = i * (w + gap)
        canvas.paste(Image.fromarray(crop), (x, label_h))
        draw.rectangle([x, 0, x + w - 1, label_h - 2], fill=(40, 40, 40))
        draw.text((x + 4, 5), f"[{region_name}] {label}", fill=(210, 210, 210))
    return canvas


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    print(f"[D5z] Input: {INPUT_PATH}")
    if not INPUT_PATH.exists():
        sys.exit(f"[D5z] ERROR: input not found: {INPUT_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CROPS_DIR.mkdir(parents=True, exist_ok=True)

    print("[D5z] Loading baseline...")
    baseline_pil = Image.open(INPUT_PATH).convert("RGB")
    baseline_arr = np.array(baseline_pil, dtype=np.uint8)
    H, W = baseline_arr.shape[:2]
    assert W == 8192 and H == 4096, f"Expected 8192×4096, got {W}×{H}"
    print(f"[D5z] Baseline: {W}×{H} loaded.")

    print("[D5z] Building lat/lon grids...")
    LAT, LON = build_grids(H, W)
    base_f32 = baseline_arr.astype(np.float32)

    # ── D5z_a ──────────────────────────────────────────────────────────────
    print("[D5z] [A] Polar compress...")
    a_f32 = polar_compress(base_f32, LAT)
    print("[D5z] [B] Deep ocean desaturate...")
    a_f32 = deep_ocean_desaturate(a_f32, LAT, LON)
    a_arr = a_f32.astype(np.uint8)

    a_path = OUT_DIR / "d5z_a_8192x4096.jpg"
    Image.fromarray(a_arr).save(a_path, "JPEG", quality=92, subsampling=0)
    print(f"[D5z] Saved d5z_a: {a_path.stat().st_size // 1024}KB")

    # ── D5z_b ──────────────────────────────────────────────────────────────
    print("[D5z] [C] Sahara/Arabia darken...")
    b_f32 = sahara_land_darken(a_f32, LAT, LON)
    print("[D5z] [Guard] Color Harmony Guard...")
    b_f32, guard_log = color_harmony_guard(b_f32, base_f32, LAT, LON)
    b_arr = b_f32.astype(np.uint8)

    b_path = OUT_DIR / "d5z_b_8192x4096.jpg"
    Image.fromarray(b_arr).save(b_path, "JPEG", quality=92, subsampling=0)
    print(f"[D5z] Saved d5z_b: {b_path.stat().st_size // 1024}KB")

    # ── Metrics ────────────────────────────────────────────────────────────
    print("[D5z] Computing metrics d5z_a...")
    m_a = compute_metrics(a_f32, base_f32, LAT, LON, "d5z_a")
    print("[D5z] Computing metrics d5z_b...")
    m_b = compute_metrics(b_f32, base_f32, LAT, LON, "d5z_b")
    m_b["color_harmony_guard"] = guard_log

    (OUT_DIR / "metrics_d5z_a.json").write_text(json.dumps(m_a, indent=2))
    (OUT_DIR / "metrics_d5z_b.json").write_text(json.dumps(m_b, indent=2))
    print("[D5z] Metrics saved.")

    # ── Compare crops ──────────────────────────────────────────────────────
    print("[D5z] Generating compare crops...")
    for region_name, spec in CROP_SPECS.items():
        img = make_compare_crop(baseline_arr, a_arr, b_arr, region_name, spec)
        out = CROPS_DIR / f"{region_name}_baseline_vs_d5za_vs_d5zb.jpg"
        img.save(out, "JPEG", quality=90)
        print(f"  {out.name}")

    # ── Variant key check ──────────────────────────────────────────────────
    print("\n[D5z] ─── VARIANT KEY CHECK ───")
    print("  earth3d.js getDayTexturePaths() candidates dict does NOT contain d5z_a or d5z_b.")
    print("  STATUS: D5z variant keys missing — on-globe preview BLOCKED until separately authorized.")

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n[D5z] ─── METRICS SUMMARY ───")
    for label, m in [("d5z_a", m_a), ("d5z_b", m_b)]:
        print(f"\n  [{label}]")
        for key in ["antarctica_ice", "greenland_ice", "antarctica", "greenland", "sahara", "indian_ocean_deep_sat"]:
            v = m.get(key)
            if v:
                print(f"    {key}: change_pct={v.get('change_pct')}%")
        for pole, pv in m.get("polar_gray_check", {}).items():
            print(f"    polar_gray {pole}: spread_delta={pv['spread_delta']}, pass={pv['gray_check_pass']}")
        print(f"    protected regions:")
        all_protected_pass = True
        for pname, pv in m.get("protected", {}).items():
            passed = pv.get("all_pass", False)
            if not passed:
                all_protected_pass = False
            print(f"      {pname}: PSNR={pv.get('PSNR_dB')}dB  rgb_diff={pv.get('mean_rgb_diff')}  br_diff={pv.get('mean_br_diff')}  → {'PASS' if passed else 'FAIL'}")
        print(f"    protected regions overall: {'ALL PASS' if all_protected_pass else 'FAIL — see above'}")

    print(f"\n[D5z] Output: {OUT_DIR}")
    print("[D5z] Complete.")
    return m_a, m_b, guard_log


if __name__ == "__main__":
    main()
