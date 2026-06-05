# config.py
# 坐标：(lon_min, lon_max, lat_min, lat_max)，经度 -180~180，纬度 -90~90
# priority 越低越先执行

OCEAN_REGIONS = [

    # === A. 深海基础（最先执行）===
    {
        "name": "global_deep_ocean_base",
        "bounds": (-180, 180, -90, 90),
        "ocean_only": True,
        "deep_ocean_only": True,
        "r_offset": 0, "g_offset": 0, "b_offset": 2,
        "saturation_factor": 0.97,
        "brightness_factor": 0.99,
        "blur_px": 0,
        "priority": 0,
    },

    # === B. 东亚海域 ===
    {
        "name": "bohai_sea",
        "bounds": (117.5, 122.0, 37.0, 41.0),
        "ocean_only": True,
        "r_offset": 8, "g_offset": 6, "b_offset": -8,
        "saturation_factor": 0.82, "brightness_factor": 1.02,
        "blur_px": 8, "priority": 10,
    },
    {
        "name": "yellow_sea",
        "bounds": (119.0, 126.5, 31.5, 38.5),
        "ocean_only": True,
        "r_offset": 6, "g_offset": 5, "b_offset": -6,
        "saturation_factor": 0.85, "brightness_factor": 1.03,
        "blur_px": 12, "priority": 10,
    },
    {
        "name": "east_china_sea",
        "bounds": (120.0, 130.0, 24.0, 33.0),
        "ocean_only": True,
        "r_offset": 3, "g_offset": 3, "b_offset": -3,
        "saturation_factor": 0.90, "brightness_factor": 1.01,
        "blur_px": 16, "feather_px": 32, "priority": 10,
    },
    {
        "name": "japan_sea",
        "bounds": (128.0, 142.0, 34.0, 52.0),
        "ocean_only": True,
        "r_offset": -3, "g_offset": -2, "b_offset": 4,
        "saturation_factor": 0.88, "brightness_factor": 0.94,
        "blur_px": 20, "feather_px": 32, "priority": 10,
    },
    {
        "name": "okhotsk_sea",
        "bounds": (135.0, 163.0, 45.0, 62.0),
        "ocean_only": True,
        "r_offset": -4, "g_offset": -2, "b_offset": 2,
        "saturation_factor": 0.82, "brightness_factor": 0.93,
        "blur_px": 20, "priority": 10,
    },
    {
        "name": "bering_sea",
        "bounds": (160.0, -157.0, 52.0, 66.0),
        "cross_antimeridian": True,
        "ocean_only": True,
        "r_offset": -3, "g_offset": -2, "b_offset": 2,
        "saturation_factor": 0.83, "brightness_factor": 0.94,
        "blur_px": 20, "priority": 10,
    },

    # === C. 南海与东南亚 ===
    {
        "name": "south_china_sea_north",
        "bounds": (108.0, 121.0, 15.0, 25.0),
        "ocean_only": True,
        "r_offset": 2, "g_offset": 3, "b_offset": -2,
        "saturation_factor": 0.92, "brightness_factor": 1.02,
        "blur_px": 20, "priority": 10,
    },
    {
        "name": "south_china_sea_deep",
        "bounds": (109.0, 120.0, 5.0, 18.0),
        "ocean_only": True, "deep_ocean_only": True,
        "r_offset": -2, "g_offset": -1, "b_offset": 3,
        "saturation_factor": 0.90, "brightness_factor": 0.96,
        "blur_px": 24, "priority": 10,
    },
    {
        "name": "philippine_sea_deep",
        "bounds": (126.0, 145.0, 5.0, 28.0),
        "ocean_only": True, "deep_ocean_only": True,
        "r_offset": -3, "g_offset": -2, "b_offset": 3,
        "saturation_factor": 0.88, "brightness_factor": 0.94,
        "blur_px": 0, "priority": 10,
    },
    {
        "name": "java_sea",
        "bounds": (105.0, 120.0, -8.0, 5.0),
        "ocean_only": True,
        "r_offset": 5, "g_offset": 6, "b_offset": -4,
        "saturation_factor": 0.88, "brightness_factor": 1.04,
        "blur_px": 16, "feather_px": 32, "priority": 10,
    },
    {
        "name": "banda_sea",
        "bounds": (120.0, 135.0, -8.0, -2.0),
        "ocean_only": True,
        "r_offset": -2, "g_offset": -1, "b_offset": 2,
        "saturation_factor": 0.90, "brightness_factor": 0.96,
        "blur_px": 16, "priority": 10,
    },
    {
        "name": "malacca_thailand_gulf",
        "bounds": (98.0, 107.0, 1.0, 14.0),
        "ocean_only": True,
        "r_offset": 6, "g_offset": 5, "b_offset": -5,
        "saturation_factor": 0.84, "brightness_factor": 1.03,
        "blur_px": 12, "feather_px": 28, "priority": 10,
    },

    # === D. 印度洋 ===
    {
        "name": "bay_of_bengal",
        "bounds": (79.0, 100.0, 5.0, 23.0),
        "ocean_only": True,
        "r_offset": 5, "g_offset": 4, "b_offset": -5,
        "saturation_factor": 0.86, "brightness_factor": 1.01,
        "blur_px": 20, "priority": 10,
    },
    {
        "name": "arabian_sea",
        "bounds": (50.0, 78.0, 5.0, 26.0),
        "ocean_only": True,
        "r_offset": 2, "g_offset": 1, "b_offset": -1,
        "saturation_factor": 0.91, "brightness_factor": 0.98,
        "blur_px": 20, "priority": 10,
    },

    # === E. 中东封闭海（保守水体判断）===
    {
        "name": "persian_gulf",
        "bounds": (47.5, 57.0, 23.5, 30.5),
        "ocean_only": True, "conservative_water": True,
        "r_offset": 10, "g_offset": 8, "b_offset": -10,
        "saturation_factor": 0.80, "brightness_factor": 1.04,
        "blur_px": 8, "priority": 20,
    },
    {
        "name": "red_sea",
        "bounds": (32.0, 44.0, 12.0, 30.0),
        "ocean_only": True,
        "r_offset": 4, "g_offset": 3, "b_offset": -3,
        "saturation_factor": 0.86, "brightness_factor": 1.01,
        "blur_px": 8, "priority": 20,
    },

    # === F. 欧洲内海与封闭海 ===
    {
        "name": "black_sea",
        "bounds": (27.5, 41.5, 40.9, 46.5),
        "ocean_only": True, "conservative_water": True,
        "r_offset": -4, "g_offset": -3, "b_offset": 5,
        "saturation_factor": 0.83, "brightness_factor": 0.93,
        "blur_px": 8, "priority": 20,
    },
    {
        "name": "caspian_sea",
        "bounds": (49.0, 55.0, 36.5, 47.0),
        "ocean_only": True, "conservative_water": True,
        "r_offset": 3, "g_offset": 2, "b_offset": -2,
        "saturation_factor": 0.80, "brightness_factor": 0.97,
        "blur_px": 8, "priority": 20,
    },
    {
        "name": "caspian_north_shallow",
        "bounds": (49.0, 55.0, 43.5, 47.0),
        "ocean_only": True, "conservative_water": True,
        "r_offset": 8, "g_offset": 6, "b_offset": -8,
        "saturation_factor": 0.78, "brightness_factor": 1.04,
        "blur_px": 8, "priority": 25,
    },
    {
        "name": "mediterranean_west",
        "bounds": (-5.5, 12.0, 36.0, 44.5),
        "ocean_only": True,
        "r_offset": -2, "g_offset": -1, "b_offset": 4,
        "saturation_factor": 0.90, "brightness_factor": 0.97,
        "blur_px": 12, "priority": 20,
    },
    {
        "name": "mediterranean_east",
        "bounds": (12.0, 37.0, 30.0, 42.0),
        "ocean_only": True,
        "r_offset": -1, "g_offset": 0, "b_offset": 3,
        "saturation_factor": 0.91, "brightness_factor": 0.98,
        "blur_px": 12, "priority": 20,
    },
    {
        "name": "aegean_sea",
        "bounds": (22.0, 28.5, 35.5, 41.0),
        "ocean_only": True,
        "r_offset": 2, "g_offset": 2, "b_offset": -1,
        "saturation_factor": 0.90, "brightness_factor": 1.01,
        "blur_px": 8, "priority": 25,
    },
    {
        "name": "adriatic_sea",
        "bounds": (12.5, 20.0, 38.0, 45.8),
        "ocean_only": True,
        "r_offset": 4, "g_offset": 4, "b_offset": -3,
        "saturation_factor": 0.87, "brightness_factor": 1.01,
        "blur_px": 8, "priority": 25,
    },
    {
        "name": "baltic_sea",
        "bounds": (9.5, 30.5, 53.5, 66.0),
        "ocean_only": True, "conservative_water": True,
        "r_offset": 5, "g_offset": 4, "b_offset": -5,
        "saturation_factor": 0.80, "brightness_factor": 1.01,
        "blur_px": 12, "priority": 20,
    },
    {
        "name": "north_sea",
        "bounds": (-2.0, 9.5, 51.0, 58.5),
        "ocean_only": True,
        "r_offset": 4, "g_offset": 3, "b_offset": -4,
        "saturation_factor": 0.82, "brightness_factor": 0.99,
        "blur_px": 12, "feather_px": 28, "priority": 20,
    },
    {
        "name": "norwegian_barents",
        "bounds": (-5.0, 60.0, 65.0, 80.0),
        "ocean_only": True,
        "r_offset": -3, "g_offset": -2, "b_offset": 2,
        "saturation_factor": 0.82, "brightness_factor": 0.93,
        "blur_px": 20, "priority": 10,
    },

    # === G. 非洲周边 ===
    {
        "name": "west_africa_nearshore",
        "bounds": (-20.0, 10.0, -5.0, 15.0),
        "ocean_only": True,
        "r_offset": 5, "g_offset": 4, "b_offset": -5,
        "saturation_factor": 0.86, "brightness_factor": 1.00,
        "blur_px": 20, "priority": 10,
    },
    {
        "name": "benguela_current",
        "bounds": (10.0, 20.0, -35.0, -15.0),
        "ocean_only": True,
        "r_offset": -2, "g_offset": 0, "b_offset": 2,
        "saturation_factor": 0.84, "brightness_factor": 0.97,
        "blur_px": 20, "priority": 10,
    },
    {
        "name": "mozambique_channel",
        "bounds": (32.0, 52.0, -30.0, -10.0),
        "ocean_only": True,
        "r_offset": 4, "g_offset": 5, "b_offset": -3,
        "saturation_factor": 0.90, "brightness_factor": 1.02,
        "blur_px": 16, "priority": 10,
    },

    # === H. 美洲 ===
    {
        "name": "caribbean",
        "bounds": (-87.0, -60.0, 9.0, 23.0),
        "ocean_only": True,
        "r_offset": 2, "g_offset": 4, "b_offset": -2,
        "saturation_factor": 0.90, "brightness_factor": 1.03,
        "blur_px": 20, "feather_px": 32, "priority": 10,
    },
    {
        "name": "bahamas_shelf",
        "bounds": (-80.0, -72.0, 22.0, 27.5),
        "ocean_only": True,
        "r_offset": 3, "g_offset": 6, "b_offset": -3,
        "saturation_factor": 0.88, "brightness_factor": 1.04,
        "blur_px": 32, "feather_px": 30, "priority": 15,
    },
    {
        "name": "gulf_of_mexico",
        "bounds": (-97.0, -80.0, 18.0, 30.5),
        "ocean_only": True,
        "r_offset": 4, "g_offset": 3, "b_offset": -4,
        "saturation_factor": 0.85, "brightness_factor": 1.01,
        "blur_px": 20, "feather_px": 32, "priority": 10,
    },
    {
        "name": "amazon_mouth",
        "bounds": (-52.0, -44.0, -3.0, 6.0),
        "ocean_only": True,
        "r_offset": 8, "g_offset": 6, "b_offset": -10,
        "saturation_factor": 0.78, "brightness_factor": 1.01,
        "blur_px": 16, "priority": 20,
    },
    {
        "name": "humboldt_current",
        "bounds": (-82.0, -68.0, -45.0, -3.0),
        "ocean_only": True,
        "r_offset": -2, "g_offset": 0, "b_offset": 2,
        "saturation_factor": 0.85, "brightness_factor": 0.97,
        "blur_px": 20, "priority": 10,
    },
    {
        "name": "argentina_shelf",
        "bounds": (-65.0, -52.0, -55.0, -35.0),
        "ocean_only": True,
        "r_offset": -1, "g_offset": 0, "b_offset": 2,
        "saturation_factor": 0.84, "brightness_factor": 0.98,
        "blur_px": 16, "priority": 10,
    },

    # === I. 太平洋深海 ===
    {
        "name": "pacific_deep_north",
        "bounds": (140.0, -100.0, 10.0, 60.0),
        "cross_antimeridian": True,
        "ocean_only": True, "deep_ocean_only": True,
        "r_offset": 0, "g_offset": 0, "b_offset": 2,
        "saturation_factor": 0.96, "brightness_factor": 0.985,
        "blur_px": 0, "priority": 5,
    },
    {
        "name": "pacific_deep_south",
        "bounds": (140.0, -70.0, -60.0, 10.0),
        "cross_antimeridian": True,
        "ocean_only": True, "deep_ocean_only": True,
        "r_offset": 0, "g_offset": 0, "b_offset": 2,
        "saturation_factor": 0.96, "brightness_factor": 0.985,
        "blur_px": 0, "priority": 5,
    },

    # === J. 南大洋与极地 ===
    {
        "name": "southern_ocean",
        "bounds": (-180, 180, -70.0, -55.0),
        "ocean_only": True,
        "r_offset": -1, "g_offset": 0, "b_offset": 1,
        "saturation_factor": 0.83, "brightness_factor": 0.94,
        "blur_px": 20, "feather_px": 24, "priority": 10,
    },
    {
        "name": "ross_weddell_sea",
        "bounds": (-180, 180, -80.0, -70.0),
        "ocean_only": True,
        "r_offset": -1, "g_offset": 0, "b_offset": 1,
        "saturation_factor": 0.80, "brightness_factor": 0.92,
        "blur_px": 24, "feather_px": 30, "priority": 10,
    },
    {
        "name": "labrador_sea",
        "bounds": (-65.0, -40.0, 50.0, 65.0),
        "ocean_only": True,
        "r_offset": -3, "g_offset": -2, "b_offset": 3,
        "saturation_factor": 0.83, "brightness_factor": 0.94,
        "blur_px": 16, "priority": 10,
    },
]

# ============================================================
# 岛屿 Halo 配置（v3：deep gate 强化，大范围岛链 strength 降低）
# ============================================================
ISLAND_HALOS = [
    {"name": "hawaii",            "center": (-155.5, 20.0),  "halo_radius_km": 150, "r_offset": 3,  "g_offset": 6,  "b_offset": -3, "strength": 0.18, "blur_px": 40, "deep_gate": True},
    {"name": "guam_mariana",      "center": (145.5, 15.0),   "halo_radius_km": 200, "r_offset": 2,  "g_offset": 5,  "b_offset": -2, "strength": 0.15, "blur_px": 40, "deep_gate": True},
    {"name": "palau",             "center": (134.5, 7.3),    "halo_radius_km": 120, "r_offset": 3,  "g_offset": 6,  "b_offset": -3, "strength": 0.18, "blur_px": 36, "deep_gate": True},
    {"name": "micronesia",        "center": (158.0, 7.0),    "halo_radius_km": 300, "r_offset": 2,  "g_offset": 4,  "b_offset": -2, "strength": 0.06, "blur_px": 48, "deep_gate": True},
    {"name": "marshall_islands",  "center": (168.0, 8.0),    "halo_radius_km": 300, "r_offset": 2,  "g_offset": 4,  "b_offset": -2, "strength": 0.05, "blur_px": 48, "deep_gate": True},
    {"name": "kiribati",          "center": (-157.0, 1.5),   "halo_radius_km": 400, "r_offset": 2,  "g_offset": 4,  "b_offset": -2, "strength": 0.04, "blur_px": 52, "deep_gate": True},
    {"name": "tuvalu",            "center": (179.0, -8.5),   "halo_radius_km": 150, "r_offset": 2,  "g_offset": 5,  "b_offset": -2, "strength": 0.12, "blur_px": 40, "deep_gate": True},
    {"name": "fiji",              "center": (178.0, -18.0),  "halo_radius_km": 160, "r_offset": 3,  "g_offset": 6,  "b_offset": -3, "strength": 0.15, "blur_px": 40, "deep_gate": True},
    {"name": "tonga",             "center": (-174.5, -21.0), "halo_radius_km": 120, "r_offset": 2,  "g_offset": 5,  "b_offset": -2, "strength": 0.12, "blur_px": 40, "deep_gate": True},
    {"name": "samoa",             "center": (-172.0, -14.0), "halo_radius_km": 120, "r_offset": 2,  "g_offset": 5,  "b_offset": -2, "strength": 0.15, "blur_px": 36, "deep_gate": True},
    {"name": "cook_islands",      "center": (-159.8, -21.2), "halo_radius_km": 200, "r_offset": 2,  "g_offset": 4,  "b_offset": -2, "strength": 0.09, "blur_px": 44, "deep_gate": True},
    {"name": "french_polynesia",  "center": (-149.5, -17.5), "halo_radius_km": 400, "r_offset": 3,  "g_offset": 6,  "b_offset": -2, "strength": 0.06, "blur_px": 52, "deep_gate": True},
    {"name": "new_caledonia",     "center": (165.5, -21.5),  "halo_radius_km": 140, "r_offset": 4,  "g_offset": 7,  "b_offset": -3, "strength": 0.18, "blur_px": 36, "deep_gate": True},
    {"name": "solomon_islands",   "center": (160.0, -8.5),   "halo_radius_km": 160, "r_offset": 3,  "g_offset": 6,  "b_offset": -3, "strength": 0.15, "blur_px": 40, "deep_gate": True},
    {"name": "vanuatu",           "center": (167.5, -16.0),  "halo_radius_km": 120, "r_offset": 3,  "g_offset": 6,  "b_offset": -3, "strength": 0.15, "blur_px": 36, "deep_gate": True},
    {"name": "maldives",          "center": (73.5, 3.5),     "halo_radius_km": 160, "r_offset": 4,  "g_offset": 8,  "b_offset": -2, "strength": 0.22, "blur_px": 40, "deep_gate": True},
    {"name": "seychelles",        "center": (55.5, -4.7),    "halo_radius_km": 150, "r_offset": 3,  "g_offset": 6,  "b_offset": -2, "strength": 0.16, "blur_px": 36, "deep_gate": True},
    {"name": "mauritius_reunion", "center": (57.5, -20.5),   "halo_radius_km": 120, "r_offset": 2,  "g_offset": 5,  "b_offset": -2, "strength": 0.15, "blur_px": 36, "deep_gate": True},
    {"name": "comoros",           "center": (43.5, -11.5),   "halo_radius_km": 80,  "r_offset": 3,  "g_offset": 5,  "b_offset": -2, "strength": 0.14, "blur_px": 32, "deep_gate": True},
    {"name": "lesser_antilles",   "center": (-62.0, 14.0),   "halo_radius_km": 300, "r_offset": 3,  "g_offset": 6,  "b_offset": -3, "strength": 0.18, "blur_px": 44, "deep_gate": True},
    {"name": "bermuda",           "center": (-64.7, 32.3),   "halo_radius_km": 80,  "r_offset": 2,  "g_offset": 5,  "b_offset": -2, "strength": 0.18, "blur_px": 32, "deep_gate": True},
    {"name": "azores",            "center": (-27.0, 38.5),   "halo_radius_km": 120, "r_offset": 2,  "g_offset": 4,  "b_offset": -1, "strength": 0.12, "blur_px": 36, "deep_gate": True},
    {"name": "canary_islands",    "center": (-15.5, 28.0),   "halo_radius_km": 150, "r_offset": 2,  "g_offset": 4,  "b_offset": -2, "strength": 0.15, "blur_px": 36, "deep_gate": True},
    {"name": "falkland_islands",  "center": (-59.0, -51.7),  "halo_radius_km": 70,  "r_offset": -1, "g_offset": 1,  "b_offset": 2,  "strength": 0.09, "blur_px": 32, "deep_gate": True},
    {"name": "aleutian_islands",  "center": (-170.0, 52.5),  "halo_radius_km": 280, "r_offset": -1, "g_offset": 1,  "b_offset": 2,  "strength": 0.03, "blur_px": 48, "deep_gate": True},
]

# ============================================================
# 全局增强参数
# ============================================================
ENHANCEMENT = {
    "enable_land_enhancement":     False,
    "land_contrast_factor":        1.02,
    "land_saturation_factor":      1.02,

    "enable_polar_compress":       True,
    "polar_lat_threshold":         -75.0,
    "polar_highlight_threshold":   238,
    "polar_highlight_compress":    0.95,

    "enable_sharpen":              True,
    "sharpen_land_only":           True,
    "sharpen_amount":              0.15,
    "sharpen_radius":              0.8,

    "global_ocean_final_b_add":    0,
}

# ============================================================
# 输出配置
# ============================================================
OUTPUT = {
    "output_dir": "./d5b_output/",
    "main_filename":    "bmng_processed_2048x1024_natural_d5b_design_v3_1_dryrun.jpg",
    "main_png":         "bmng_processed_2048x1024_natural_d5b_design_v3_1_dryrun.png",
    "main_quality":     95,
    "preview_filename": "d5b_design_v3_1_preview_global.jpg",
    "preview_width":    1024,
    "preview_height":   512,
    "preview_quality":  88,
    "diff_heatmap":     "d5b_design_v3_1_diff_heatmap.jpg",
    "metrics_file":     "d5b_design_v3_1_metrics.json",
    "processing_stats_file": "d5b_design_v3_1_processing_stats.json",
    "generate_region_previews": True,
    "region_preview_regions": [
        {"name": "east_asia",              "bounds": (100,  150,  20,  55)},
        {"name": "japan_sea_region",       "bounds": (125,  145,  30,  55)},
        {"name": "med_black_caspian",      "bounds": (0,    65,   28,  50)},
        {"name": "persian_gulf_red_sea",   "bounds": (30,   60,   10,  35)},
        {"name": "maldives",               "bounds": (60,   90,  -10,  15)},
        {"name": "caribbean_gulf",         "bounds": (-100, -55,  10,  32)},
        {"name": "pacific_south_islands",  "bounds": (140, -120, -35,  15)},
        {"name": "south_america",          "bounds": (-90,  -30, -60,  15)},
        {"name": "pacific_deep",           "bounds": (-180, -100,-30,  30)},
        {"name": "antarctica",             "bounds": (-180,  180, -90, -55)},
        {"name": "hawaii",                 "bounds": (-165, -148,  15,  25)},
        {"name": "french_polynesia",       "bounds": (-158, -136, -24,  -8)},
    ],
}

# metrics 统计区域
METRICS_REGIONS = [
    {"name": "antarctica",        "bounds": (-180, 180, -90, -75)},
    {"name": "greenland",         "bounds": (-60,  -15,  60,  85)},
    {"name": "arctic",            "bounds": (-180, 180,  78,  90)},
    {"name": "sahara",            "bounds": (-10,   35,  15,  30)},
    {"name": "arabian_peninsula", "bounds": (35,    60,  12,  30)},
    {"name": "australia_interior","bounds": (115,  145, -35, -20)},
    {"name": "yellow_sea",        "bounds": (119, 126.5,31.5, 38.5)},
    {"name": "japan_sea",         "bounds": (128,  142,  34,  52)},
    {"name": "black_sea",         "bounds": (27.5,41.5,40.9, 46.5)},
    {"name": "caspian_sea",       "bounds": (49,    55,36.5,  47)},
    {"name": "mediterranean",     "bounds": (-5.5,  37,  30,44.5)},
    {"name": "bahamas",           "bounds": (-80,  -72,  22,27.5)},
    {"name": "maldives",          "bounds": (71,    77,   0,   7)},
    {"name": "great_barrier_reef","bounds": (142,  154, -25, -10)},
    {"name": "hawaii",            "bounds": (-162, -154, 18,  23)},
    {"name": "french_polynesia",  "bounds": (-155, -140, -20, -10)},
    {"name": "pacific_deep",      "bounds": (-180, -100, -30,  30)},
    {"name": "southern_ocean",    "bounds": (-180,  180, -65, -55)},
]
