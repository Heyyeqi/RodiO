# main.py
import os, sys
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

# Patch 1: 脚本相对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from config import OCEAN_REGIONS, ISLAND_HALOS, OUTPUT
from masks import (make_region_mask, make_ocean_mask_v2,
                   make_conservative_water_mask, make_deep_ocean_mask,
                   make_island_halo_mask, make_deep_gate_for_halo)
from adjustments import apply_region, apply_island_halo
from enhancement import full_enhance
from preview import save_all_previews
from metrics import run_metrics

def main(input_path, out_dir=None):
    print("=== D5b_design_v3 ===")
    if not os.path.exists(input_path):
        print(f"错误：找不到 {input_path}")
        sys.exit(1)

    if out_dir is None:
        out_dir = os.path.join(SCRIPT_DIR, "d5b_output")
    os.makedirs(out_dir, exist_ok=True)
    print(f"输出目录: {out_dir}")

    print("读取图像...")
    in_pil = Image.open(input_path).convert("RGB")
    width, height = in_pil.size
    print(f"分辨率: {width}×{height}")
    in_arr = np.array(in_pil)

    # 预计算全局 mask（基于原始输入图，不受处理过程影响）
    print("预计算 mask...")
    ocean_mask = make_ocean_mask_v2(in_arr)
    consv_mask = make_conservative_water_mask(in_arr)
    deep_mask  = make_deep_ocean_mask(in_arr)

    img = in_arr.copy()

    # 按优先级处理区域
    regions = sorted(OCEAN_REGIONS, key=lambda x: x.get("priority", 10))
    print(f"\n处理 {len(regions)} 个海域区域...")

    region_stats_list = []
    for i, cfg in enumerate(regions):
        name = cfg["name"]
        region_mask = make_region_mask(
            cfg["bounds"], width, height,
            cross_antimeridian=cfg.get("cross_antimeridian", False),
            feather_px=cfg.get("feather_px", 20)
        )

        base_water = ocean_mask if cfg.get("ocean_only") else np.ones((height, width), bool)
        if cfg.get("conservative_water"):
            base_water = consv_mask
        if cfg.get("deep_ocean_only"):
            base_water = base_water & deep_mask

        region_mask_eff = region_mask * base_water.astype(np.float32)

        raw_px = int((region_mask > 0.01).sum())
        eff_px = int((region_mask_eff > 0.01).sum())
        eff_ratio = eff_px / max(raw_px, 1)

        before = img.copy()
        img = apply_region(img, region_mask_eff, cfg)
        diff = np.abs(img.astype(np.int16) - before.astype(np.int16))

        # Patch 3: 有效区域统计
        effective_px = region_mask_eff > 0.01
        if effective_px.any():
            mean_delta_rgb = [round(float(diff[:,:,c][effective_px].mean()), 3) for c in range(3)]
            max_delta_rgb  = int(np.maximum.reduce(
                [diff[:,:,c][effective_px] for c in range(3)]
            ).max())
        else:
            mean_delta_rgb = [0.0, 0.0, 0.0]
            max_delta_rgb  = 0

        region_stats_list.append({
            "name": name,
            "raw_pixels": raw_px,
            "effective_pixels": eff_px,
            "effective_ratio": round(eff_ratio, 4),
            "mean_delta_rgb": mean_delta_rgb,
            "max_delta_rgb": max_delta_rgb,
            "warning": "⚠️ effective_ratio < 1%, 配置可能无效" if eff_ratio < 0.01 else "",
        })

        status = f"eff_ratio={eff_ratio:.1%}"
        if eff_ratio < 0.01:
            status += " ⚠️"
        print(f"  [{i+1}/{len(regions)}] {name}: {status}")

    # 岛屿 halo
    halo_stats_list = []
    print(f"\n处理 {len(ISLAND_HALOS)} 个岛屿 halo...")
    for hcfg in ISLAND_HALOS:
        name = hcfg["name"]
        halo_mask = make_island_halo_mask(
            hcfg["center"][0], hcfg["center"][1],
            hcfg["halo_radius_km"], width, height,
            blur_px=hcfg.get("blur_px", 40)
        )

        raw_px = int((halo_mask > 0.01).sum())

        if hcfg.get("deep_gate"):
            halo_mask = make_deep_gate_for_halo(img, halo_mask)

        # Patch 2: 强制限制在 ocean 区域，防止陆地/岛屿本体被染色
        halo_mask = halo_mask * ocean_mask.astype(np.float32)

        eff_px = int((halo_mask > 0.01).sum())
        eff_ratio = eff_px / max(raw_px, 1)

        before = img.copy()
        img = apply_island_halo(img, halo_mask, hcfg)
        diff = np.abs(img.astype(np.int16) - before.astype(np.int16))

        # Patch 3: halo 有效区域统计
        halo_effective = halo_mask > 0.01
        if halo_effective.any():
            h_mean_delta = [round(float(diff[:,:,c][halo_effective].mean()), 3) for c in range(3)]
            h_max_delta  = int(np.maximum.reduce(
                [diff[:,:,c][halo_effective] for c in range(3)]
            ).max())
        else:
            h_mean_delta = [0.0, 0.0, 0.0]
            h_max_delta  = 0

        halo_stats_list.append({
            "name": name,
            "raw_pixels": raw_px,
            "effective_pixels_after_gate": eff_px,
            "effective_ratio_after_gate": round(eff_ratio, 4),
            "mean_delta_rgb": h_mean_delta,
            "max_delta_rgb": h_max_delta,
            "warning": "⚠️ effective_ratio > 30%, 可能形成大面积光晕" if eff_ratio > 0.30 else "",
        })
        print(f"  halo: {name} eff_ratio={eff_ratio:.1%}")

    # 全局增强
    print("\n全局增强...")
    out_pil_tmp = Image.fromarray(img)
    img, out_pil = full_enhance(img, out_pil_tmp)

    # Patch 1: 所有输出路径用 out_dir
    jpg_path = os.path.join(out_dir, OUTPUT["main_filename"])
    png_path = os.path.join(out_dir, OUTPUT["main_png"])
    out_pil.save(jpg_path, "JPEG", quality=OUTPUT["main_quality"], optimize=True)
    out_pil.save(png_path, "PNG")
    print(f"JPG: {jpg_path}  ({os.path.getsize(jpg_path)/1024:.0f} KB)")
    print(f"PNG: {png_path}  ({os.path.getsize(png_path)/1024:.0f} KB)")

    preview_path = os.path.join(out_dir, OUTPUT["preview_filename"])
    out_pil.resize((OUTPUT["preview_width"], OUTPUT["preview_height"]), Image.LANCZOS)\
           .save(preview_path, "JPEG", quality=OUTPUT["preview_quality"])

    print("\n分区对比预览...")
    save_all_previews(in_pil, out_pil, out_dir)

    print("\n计算 metrics...")
    in_arr_for_metrics  = np.array(in_pil)
    out_arr_for_metrics = np.array(out_pil)
    run_metrics(in_arr_for_metrics, out_arr_for_metrics, out_dir)

    import json
    stats_path = os.path.join(out_dir, OUTPUT.get("processing_stats_file", "d5b_design_v3_1_processing_stats.json"))
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump({
            "ocean_regions": region_stats_list,
            "island_halos": halo_stats_list,
        }, f, ensure_ascii=False, indent=2)
    print(f"处理统计: {stats_path}")

    print("\n=== dry-run 完成 ===")
    print(f"输出目录: {out_dir}")
    files = sorted(os.listdir(out_dir))
    for fname in files:
        p = os.path.join(out_dir, fname)
        print(f"  {fname}  ({os.path.getsize(p)/1024:.0f} KB)")

    print("\n⚠️  请人工检查以下内容后再决定是否全尺寸执行：")
    print("  1. compare_*.jpg — D5a vs D5b 对比图")
    print("  2. d5b_design_v3_diff_heatmap.jpg — 变化热力图")
    print("  3. d5b_design_v3_metrics.json — 区域量化指标")
    print("  4. d5b_design_v3_processing_stats.json — 区域命中率")
    print("  5. PNG 版本检查色带/噪点/halo 光斑")
    print("\n⚠️  未自动 commit，未修改原图，未生成全尺寸图。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python main.py <dry-run 小图路径>")
        sys.exit(1)
    main(sys.argv[1])
