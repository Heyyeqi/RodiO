# formal_8k.py — thin wrapper for 8192×4096 formal generation
# No visual parameters changed; only output dir/filenames are overridden.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(SCRIPT_DIR, "d5b_output", "formal_8k")

# Override output filenames only (no visual params touched)
config.OUTPUT["main_filename"]         = "bmng_processed_8192x4096_natural_d5b_design_v3_1.jpg"
config.OUTPUT["main_png"]              = "bmng_processed_8192x4096_natural_d5b_design_v3_1.png"
config.OUTPUT["preview_filename"]      = "d5b_design_v3_1_8k_preview_global.jpg"
config.OUTPUT["diff_heatmap"]          = "d5b_design_v3_1_8k_diff_heatmap.jpg"
config.OUTPUT["metrics_file"]          = "d5b_design_v3_1_8k_metrics.json"
config.OUTPUT["processing_stats_file"] = "d5b_design_v3_1_8k_processing_stats.json"

# Prefix compare image names for version traceability
for r in config.OUTPUT["region_preview_regions"]:
    if not r["name"].startswith("v3_1_8k_"):
        r["name"] = "v3_1_8k_" + r["name"]

from main import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python formal_8k.py <8K 输入图路径>")
        sys.exit(1)
    main(sys.argv[1], out_dir=OUT_DIR)
