# v3_2_dryrun.py — thin wrapper for v3.2 2048×1024 dry-run
# No visual parameters changed; only output routing and metrics/compare regions extended.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(SCRIPT_DIR, "d5b_output", "v3_2_dryrun")

# Override output filenames only
config.OUTPUT["main_filename"]         = "bmng_processed_2048x1024_natural_d5b_design_v3_2_dryrun.jpg"
config.OUTPUT["main_png"]              = "bmng_processed_2048x1024_natural_d5b_design_v3_2_dryrun.png"
config.OUTPUT["preview_filename"]      = "d5b_design_v3_2_preview_global.jpg"
config.OUTPUT["diff_heatmap"]          = "d5b_design_v3_2_diff_heatmap.jpg"
config.OUTPUT["metrics_file"]          = "d5b_design_v3_2_metrics.json"
config.OUTPUT["processing_stats_file"] = "d5b_design_v3_2_processing_stats.json"

# Extended compare regions: P1 + P2 observation coverage
config.OUTPUT["region_preview_regions"] = [
    # P1A: Antarctica / Southern Ocean
    {"name": "v3_2_antarctica_ross_sea",    "bounds": (150,  180, -82, -68)},
    {"name": "v3_2_antarctica_weddell_sea", "bounds": (-70,  -10, -82, -68)},
    {"name": "v3_2_southern_ocean",         "bounds": (-180, 180, -68, -52)},
    # P1B: Coastline edge
    {"name": "v3_2_bahamas",                "bounds": (-84,  -68,  20,  30)},
    {"name": "v3_2_caribbean",              "bounds": (-90,  -60,   9,  24)},
    {"name": "v3_2_indonesia_java_sea",     "bounds": (100,  128, -11,   7)},
    {"name": "v3_2_singapore_malacca",      "bounds": ( 95,  110,  -1,  12)},
    {"name": "v3_2_east_china_sea",         "bounds": (116,  134,  22,  36)},
    {"name": "v3_2_tokyo_japan",            "bounds": (130,  146,  29,  43)},
    {"name": "v3_2_new_york_coast",         "bounds": (-80,  -66,  34,  45)},
    # P2-1: Deep ocean texture
    {"name": "v3_2_central_pacific_deep",   "bounds": (-175, -140, -12,  22)},
    {"name": "v3_2_north_atlantic_deep",    "bounds": ( -55,  -20,  22,  52)},
    {"name": "v3_2_azores_ridge",           "bounds": ( -33,  -18,  33,  46)},
    # P2-2: Pacific island visibility
    {"name": "v3_2_tahiti",                 "bounds": (-158, -142, -24, -12)},
    {"name": "v3_2_fiji",                   "bounds": ( 174,  188, -23, -12)},
    {"name": "v3_2_new_caledonia",          "bounds": ( 160,  174, -26, -18)},
    # P2-4: Inland water
    {"name": "v3_2_black_sea",              "bounds": (  26,   42,  40,  48)},
    {"name": "v3_2_caspian_sea",            "bounds": (  47,   57,  36,  48)},
    {"name": "v3_2_great_lakes",            "bounds": ( -93,  -75,  40,  49)},
    # P2-5: Land observation
    {"name": "v3_2_amazon_rainforest",      "bounds": ( -70,  -48, -12,   6)},
    {"name": "v3_2_sahara",                 "bounds": ( -12,   32,  14,  31)},
    {"name": "v3_2_australia_interior",     "bounds": ( 118,  142, -31, -18)},
]

# Extended metrics regions
config.METRICS_REGIONS = [
    # Polar / highlight
    {"name": "antarctica",            "bounds": (-180, 180, -90, -75)},
    {"name": "southern_ocean",        "bounds": (-180, 180, -65, -55)},
    {"name": "greenland",             "bounds": ( -60,  -15,  60,  85)},
    {"name": "arctic",                "bounds": (-180, 180,  78,  90)},
    {"name": "sahara",                "bounds": ( -10,   35,  15,  30)},
    {"name": "arabian_peninsula",     "bounds": (  35,   60,  12,  30)},
    {"name": "australia_interior",    "bounds": ( 115,  145, -35, -20)},
    {"name": "tibetan_plateau",       "bounds": (  75,  105,  28,  40)},
    # Coastline / shallow edge
    {"name": "bahamas",               "bounds": ( -80,  -72,  22, 27.5)},
    {"name": "caribbean",             "bounds": ( -87,  -60,   9,  23)},
    {"name": "indonesia_java_sea",    "bounds": ( 105,  120,  -8,   5)},
    {"name": "singapore_malacca",     "bounds": (  98,  107,   1,  14)},
    {"name": "east_china_sea",        "bounds": ( 120,  130,  24,  33)},
    {"name": "japan_nearshore",       "bounds": ( 128,  142,  34,  42)},
    {"name": "new_york_coast",        "bounds": ( -80,  -68,  35,  42)},
    {"name": "persian_gulf",          "bounds": (47.5,   57,23.5,30.5)},
    # Deep ocean
    {"name": "central_pacific_deep",  "bounds": (-180, -100, -30,  30)},
    {"name": "north_atlantic_deep",   "bounds": ( -55,  -25,  20,  45)},
    {"name": "azores_ridge",          "bounds": ( -32,  -20,  34,  45)},
    {"name": "mariana_guam",          "bounds": ( 140,  150,  10,  25)},
    {"name": "chile_offshore",        "bounds": ( -82,  -68, -45,  -3)},
    # Pacific islands
    {"name": "tahiti",                "bounds": (-155, -140, -20, -10)},
    {"name": "tuamotu",               "bounds": (-148, -134, -22, -14)},
    {"name": "fiji",                  "bounds": ( 172,  180, -22, -15)},
    {"name": "tonga",                 "bounds": (-180, -173, -23, -15)},
    {"name": "marshall_islands",      "bounds": ( 162,  174,   4,  12)},
    {"name": "tuvalu",                "bounds": ( 176,  182,  -9,  -7)},
    {"name": "new_caledonia",         "bounds": ( 162,  170, -23, -18)},
    {"name": "solomon_islands",       "bounds": ( 155,  164, -12,  -5)},
    {"name": "hawaii",                "bounds": (-162, -154,  18,  23)},
    # Inland water
    {"name": "caspian_sea",           "bounds": (  49,   55,36.5,  47)},
    {"name": "black_sea",             "bounds": (27.5, 41.5,40.9,46.5)},
    {"name": "great_lakes",           "bounds": ( -93,  -76,  41,  48)},
    {"name": "baikal",                "bounds": ( 104,  110,  51,  56)},
    {"name": "lake_victoria",         "bounds": (  30,   35,  -3,   0)},
    # Land
    {"name": "amazon_rainforest",     "bounds": ( -65,  -45, -10,   5)},
    {"name": "congo_basin",           "bounds": (  15,   30, -10,   5)},
    {"name": "indochina",             "bounds": (  98,  112,   8,  24)},
    {"name": "central_india",         "bounds": (  72,   88,  14,  28)},
]

from main import main

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python v3_2_dryrun.py <2048×1024 输入图路径>")
        sys.exit(1)
    main(sys.argv[1], out_dir=OUT_DIR)
