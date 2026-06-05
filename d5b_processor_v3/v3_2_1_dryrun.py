# v3_2_1_dryrun.py — thin wrapper for v3.2.1 narrow correction 2048×1024 dry-run
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(SCRIPT_DIR, "d5b_output", "v3_2_1_dryrun")

config.OUTPUT["main_filename"]         = "bmng_processed_2048x1024_natural_d5b_design_v3_2_1_dryrun.jpg"
config.OUTPUT["main_png"]              = "bmng_processed_2048x1024_natural_d5b_design_v3_2_1_dryrun.png"
config.OUTPUT["preview_filename"]      = "d5b_design_v3_2_1_preview_global.jpg"
config.OUTPUT["diff_heatmap"]          = "d5b_design_v3_2_1_diff_heatmap.jpg"
config.OUTPUT["metrics_file"]          = "d5b_design_v3_2_1_metrics.json"
config.OUTPUT["processing_stats_file"] = "d5b_design_v3_2_1_processing_stats.json"

config.OUTPUT["region_preview_regions"] = [
    {"name": "v3_2_1_antarctica_ross_sea",    "bounds": (150,  180, -82, -68)},
    {"name": "v3_2_1_antarctica_weddell_sea", "bounds": (-70,  -10, -82, -68)},
    {"name": "v3_2_1_southern_ocean",         "bounds": (-180, 180, -68, -52)},
    {"name": "v3_2_1_bahamas",                "bounds": (-84,  -68,  20,  30)},
    {"name": "v3_2_1_caribbean",              "bounds": (-90,  -60,   9,  24)},
    {"name": "v3_2_1_east_china_sea",         "bounds": (116,  134,  22,  36)},
    {"name": "v3_2_1_indonesia_java_sea",     "bounds": (100,  128, -11,   7)},
    {"name": "v3_2_1_central_pacific_deep",   "bounds": (-175, -140, -12,  22)},
    {"name": "v3_2_1_tahiti",                 "bounds": (-158, -142, -24, -12)},
    {"name": "v3_2_1_fiji",                   "bounds": (174,   188, -23, -12)},
]

config.METRICS_REGIONS = [
    {"name": "antarctica",         "bounds": (-180, 180, -90, -75)},
    {"name": "southern_ocean",     "bounds": (-180, 180, -65, -55)},
    {"name": "greenland",          "bounds": ( -60,  -15,  60,  85)},
    {"name": "sahara",             "bounds": ( -10,   35,  15,  30)},
    {"name": "bahamas",            "bounds": ( -80,  -72,  22, 27.5)},
    {"name": "caribbean",          "bounds": ( -87,  -60,   9,  23)},
    {"name": "east_china_sea",     "bounds": ( 120,  130,  24,  33)},
    {"name": "indonesia_java_sea", "bounds": ( 105,  120,  -8,   5)},
    {"name": "central_pacific_deep","bounds": (-180, -100, -30,  30)},
    {"name": "north_atlantic_deep","bounds": ( -55,  -25,  20,  45)},
    {"name": "tahiti",             "bounds": (-155, -140, -20, -10)},
    {"name": "fiji",               "bounds": ( 172,  180, -22, -15)},
    {"name": "new_caledonia",      "bounds": ( 162,  170, -23, -18)},
    {"name": "caspian_sea",        "bounds": (  49,   55,36.5,  47)},
    {"name": "black_sea",          "bounds": (27.5, 41.5,40.9,46.5)},
    {"name": "great_lakes",        "bounds": ( -93,  -76,  41,  48)},
]

from main import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python v3_2_1_dryrun.py <2048×1024 输入图路径>")
        sys.exit(1)
    main(sys.argv[1], out_dir=OUT_DIR)
