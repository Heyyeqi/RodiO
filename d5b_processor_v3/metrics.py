# metrics.py
import json
import numpy as np
from config import METRICS_REGIONS, OUTPUT

def crop_region_array(arr, bounds, width, height):
    lon_min, lon_max, lat_min, lat_max = bounds
    y0 = max(0, int((90.0 - lat_max) / 180.0 * height))
    y1 = min(height, int((90.0 - lat_min) / 180.0 * height))
    if lon_min <= lon_max:
        x0 = max(0, int((lon_min + 180.0) / 360.0 * width))
        x1 = min(width, int((lon_max + 180.0) / 360.0 * width))
        return arr[y0:y1, x0:x1]
    else:
        x0 = int((lon_min + 180.0) / 360.0 * width)
        x1 = int((lon_max + 180.0) / 360.0 * width)
        return np.concatenate([arr[y0:y1, x0:], arr[y0:y1, :x1]], axis=1)

def region_stats(arr):
    f = arr.astype(np.float32)
    mean_rgb = f.mean(axis=(0, 1)).tolist()
    brightness = f.mean(axis=2)
    white_ratio = float((brightness > 220).mean())
    high_sat = (f.max(axis=2) - f.min(axis=2))
    high_sat_ratio = float((high_sat > 60).mean())
    return {
        "mean_rgb": [round(x, 2) for x in mean_rgb],
        "mean_brightness": round(float(brightness.mean()), 2),
        "white_pixel_ratio": round(white_ratio, 4),
        "high_saturation_ratio": round(high_sat_ratio, 4),
    }

def compute_diff_stats(in_arr, out_arr):
    diff = np.abs(out_arr.astype(np.int16) - in_arr.astype(np.int16))
    return {
        "delta_rgb": [round(float(diff[:,:,c].mean()), 3) for c in range(3)],
        "max_abs_diff": int(diff.max()),
    }

def compute_top_changed_pixels(in_arr, out_arr, n=20):
    """找出变化最大的 n 个像素"""
    height, width = in_arr.shape[:2]
    diff = np.abs(out_arr.astype(np.int16) - in_arr.astype(np.int16)).mean(axis=2)
    flat_idx = np.argsort(diff.ravel())[-n:][::-1]
    results = []
    for idx in flat_idx:
        y, x = divmod(int(idx), width)
        lon = round(x / width * 360.0 - 180.0, 2)
        lat = round(90.0 - y / height * 180.0, 2)
        results.append({
            "x": x, "y": y, "lon": lon, "lat": lat,
            "input_rgb": in_arr[y, x].tolist(),
            "output_rgb": out_arr[y, x].tolist(),
            "mean_diff": round(float(diff[y, x]), 2),
        })
    return results

def compute_diff_heatmap(in_arr, out_arr):
    diff = np.abs(out_arr.astype(np.int16) - in_arr.astype(np.int16)).mean(axis=2)
    # Patch 4: 防除零
    max_diff = float(diff.max())
    if max_diff <= 0:
        normalized = np.zeros(diff.shape, dtype=np.uint8)
    else:
        normalized = (diff / max_diff * 255).astype(np.uint8)
    # 热力图：黑→蓝→红
    hmap = np.zeros((*normalized.shape, 3), dtype=np.uint8)
    hmap[:,:,0] = normalized
    hmap[:,:,2] = 255 - normalized
    return hmap

def run_metrics(in_arr, out_arr, out_dir):
    height, width = in_arr.shape[:2]
    results = {"regions": {}, "top_changed_pixels": []}

    for region in METRICS_REGIONS:
        name = region["name"]
        in_crop  = crop_region_array(in_arr,  region["bounds"], width, height)
        out_crop = crop_region_array(out_arr, region["bounds"], width, height)
        if in_crop.size == 0:
            continue
        in_stats   = region_stats(in_crop)
        out_stats  = region_stats(out_crop)
        diff_stats = compute_diff_stats(in_crop, out_crop)
        results["regions"][name] = {
            "input":  in_stats,
            "output": out_stats,
            "diff":   diff_stats,
        }
        warnings = []
        if diff_stats["max_abs_diff"] > 40 and name in (
            "sahara","arabian_peninsula","australia_interior","greenland","arctic"
        ):
            warnings.append(f"⚠️  陆地/极地区域最大变化 {diff_stats['max_abs_diff']}，超过 40，请检查误伤")
        if warnings:
            results["regions"][name]["warnings"] = warnings

    results["top_changed_pixels"] = compute_top_changed_pixels(in_arr, out_arr)

    import os
    json_path = os.path.join(out_dir, OUTPUT["metrics_file"])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  [metrics] 保存: {json_path}")

    from PIL import Image
    hmap = compute_diff_heatmap(in_arr, out_arr)
    hmap_path = os.path.join(out_dir, OUTPUT["diff_heatmap"])
    Image.fromarray(hmap).save(hmap_path, "JPEG", quality=88)
    print(f"  [metrics] diff heatmap: {hmap_path}")

    return results
