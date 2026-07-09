#!/usr/bin/env python3.11
"""
rdl_mapbox_poc.py — Mapbox Satellite + GEBCO depth compositor for RDL regions.

Compositor layers:
  M0  Mapbox Satellite-v9 tiles (RGB base, zoom 10)
  M1  GEBCO 2026 sub-ice depth tint (depth-weighted, zero influence at ≥-30m)

Token: reads MAPBOX_TOKEN from environment or .env at repo root.
Token is never written to output files or logs.

Usage:
  python3.11 scripts/geo/rdl_mapbox_poc.py --region hawaii
  python3.11 scripts/geo/rdl_mapbox_poc.py --all
  python3.11 scripts/geo/rdl_mapbox_poc.py --list
  python3.11 scripts/geo/rdl_mapbox_poc.py --region maldives --no-gebco
  python3.11 scripts/geo/rdl_mapbox_poc.py --all --resource-stack
  python3.11 scripts/geo/rdl_mapbox_poc.py --all --resource-stack-level 16k
  MAPBOX_TOKEN=pk... python3.11 scripts/geo/rdl_mapbox_poc.py --all
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import sqlite3
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

try:
    import tifffile
    _HAS_TIFFFILE = True
except ImportError:
    _HAS_TIFFFILE = False

Image.MAX_IMAGE_PIXELS = None

ROOT       = Path(__file__).parent.parent.parent
RDL_OUT    = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions"
TILE_CACHE = ROOT / "d5b_processor_v3/source_cache/mapbox_static_tiles"
GEBCO_DIR  = ROOT / "d5b_processor_v3/source_cache/gee_global/external_raw/gebco/gebco_2026_sub_ice_topo_geotiff"
CORAL_ROOT = ROOT / "d5b_processor_v3/source_cache/gee_global/external_raw/allen_coral_atlas"
HINTS_PATH = ROOT / "docs/preview_archives/rdl_m3_m4_region_sampler_20260626/m3_m4_visual_hints.json"
JRC_OCC_PATH = ROOT / "d5b_processor_v3/source_cache/gee_global/exported_8k/jrc_gsw_occurrence_8192x4096.tif"
COPERNICUS_SLOPE_PATH = ROOT / "d5b_processor_v3/source_cache/gee_global/exported_8k/copernicus_dem_glo30_slope_8192x4096.tif"
COPERNICUS_ELEV_PATH = ROOT / "d5b_processor_v3/source_cache/gee_global/exported_8k/copernicus_dem_glo30_elevation_8192x4096.tif"
SRTM_LANDFORMS_PATH = ROOT / "d5b_processor_v3/source_cache/gee_global/supplemental_8k/srtm_landforms_global_8192x4096.tif"
_JRC_W, _JRC_H = 8192, 4096

# ── M3/M4 visual hints (loaded once on first use) ─────────────────────────────

def _load_m3m4_hints() -> dict[str, dict]:
    if not HINTS_PATH.exists():
        return {}
    payload = json.loads(HINTS_PATH.read_text())
    return {r["region"]: r for r in payload.get("regions", [])}

M3M4_HINTS: dict[str, dict] = {}

def _get_m3m4_hints(region_id: str) -> dict | None:
    global M3M4_HINTS
    if not M3M4_HINTS:
        M3M4_HINTS = _load_m3m4_hints()
    return M3M4_HINTS.get(region_id)

# ── Region definitions ────────────────────────────────────────────────────────
# bounds: (lon_w, lon_e, lat_s, lat_n)

REGIONS: dict[str, dict] = {
    # ── Original 8 regions ────────────────────────────────────────────────────
    "hawaii": {
        "label": "夏威夷",
        "bounds": (-161.5, -154.0, 18.0, 23.0),
        "description": "Hawaiian island chain",
    },
    "maldives": {
        "label": "马尔代夫",
        "bounds": (71.5, 74.5, -1.5, 8.5),
        "description": "Maldives atoll chain + approach waters",
    },
    "ryukyu": {
        "label": "琉球 / 冲绳",
        "bounds": (122.5, 132.5, 23.5, 30.0),
        "description": "Ryukyu Islands chain including Okinawa",
    },
    "philippines_central": {
        "label": "菲律宾中部",
        "bounds": (117.0, 127.0, 6.0, 18.0),
        "description": "Philippine archipelago central region",
    },
    "south_china_sea": {
        "label": "南海",
        "bounds": (108.0, 120.0, 8.0, 22.0),
        "description": "South China Sea including Paracel & Spratly Islands",
    },
    "great_barrier_reef": {
        "label": "大堡礁",
        "bounds": (142.5, 153.5, -25.0, -10.0),
        "description": "Great Barrier Reef and Coral Sea",
    },
    "caribbean_bahamas": {
        "label": "加勒比 / 巴哈马",
        "bounds": (-85.0, -70.0, 17.0, 27.5),
        "description": "Bahamas archipelago and Caribbean island chain",
    },
    "indonesia_east": {
        "label": "印度尼西亚东部",
        "bounds": (120.0, 135.0, -10.0, 1.0),
        "description": "Eastern Indonesian archipelago including Sulawesi",
    },
    # ── East Asia ─────────────────────────────────────────────────────────────
    "japan": {
        "label": "日本列岛",
        "bounds": (129.5, 145.5, 30.5, 45.5),
        "description": "Japanese archipelago — Honshu, Kyushu, Shikoku, Hokkaido",
        "zoom": 9,
    },
    "korea_yellow_sea": {
        "label": "朝鲜半岛 / 黄海",
        "bounds": (122.0, 132.0, 31.0, 38.5),
        "description": "Korean Peninsula and Yellow Sea",
    },
    "taiwan": {
        "label": "台湾 / 东海",
        "bounds": (118.5, 124.0, 21.5, 26.0),
        "description": "Taiwan island and East China Sea shelf",
    },
    # ── Europe / Atlantic ─────────────────────────────────────────────────────
    "mediterranean_east": {
        "label": "东地中海",
        "bounds": (22.0, 37.0, 34.0, 41.5),
        "description": "Aegean Sea, Greek islands, Turkish coast",
    },
    "mediterranean_west": {
        "label": "西地中海",
        "bounds": (7.0, 22.0, 35.5, 47.0),
        "description": "Tyrrhenian Sea, Adriatic, Sardinia, Sicily",
        "zoom": 9,
    },
    "british_isles": {
        "label": "不列颠群岛",
        "bounds": (-11.0, 3.0, 49.5, 61.5),
        "description": "Great Britain, Ireland and surrounding seas",
        "zoom": 9,
    },
    "norway_fjords": {
        "label": "挪威峡湾",
        "bounds": (4.0, 18.0, 57.5, 71.0),
        "description": "Norwegian fjord coast and North Sea",
        "zoom": 9,
    },
    "iceland": {
        "label": "冰岛",
        "bounds": (-27.0, -10.0, 62.5, 67.0),
        "description": "Iceland and surrounding North Atlantic",
        "zoom": 9,
    },
    "azores": {
        "label": "亚速尔群岛",
        "bounds": (-31.5, -24.5, 36.5, 40.0),
        "description": "Azores archipelago, mid-Atlantic",
    },
    "canary_madeira": {
        "label": "加那利 / 马德拉",
        "bounds": (-18.5, -13.0, 27.0, 33.5),
        "description": "Canary Islands and Madeira archipelago",
    },
    # ── Middle East / Indian Ocean ────────────────────────────────────────────
    "black_sea": {
        "label": "黑海",
        "bounds": (27.5, 42.0, 40.5, 47.0),
        "description": "Black Sea and Bosphorus region",
        "zoom": 9,
    },
    "caspian_sea": {
        "label": "里海",
        "bounds": (49.0, 55.0, 36.5, 47.5),
        "description": "Caspian Sea — world's largest landlocked water body",
    },
    "red_sea": {
        "label": "红海",
        "bounds": (32.0, 44.0, 12.0, 30.0),
        "description": "Red Sea, Gulf of Aden, Sinai Peninsula",
        "zoom": 9,
    },
    "persian_gulf": {
        "label": "波斯湾",
        "bounds": (50.0, 60.0, 22.0, 27.5),
        "description": "Persian Gulf and Gulf of Oman",
    },
    "sri_lanka": {
        "label": "斯里兰卡",
        "bounds": (78.5, 82.5, 5.5, 11.0),
        "description": "Sri Lanka island and southern India tip",
    },
    "andaman_sea": {
        "label": "安达曼海",
        "bounds": (91.5, 100.5, 5.0, 14.5),
        "description": "Andaman Sea, Andaman & Nicobar Islands",
    },
    "seychelles": {
        "label": "塞舌尔",
        "bounds": (54.5, 57.5, -7.5, -3.5),
        "description": "Seychelles archipelago, western Indian Ocean",
    },
    "madagascar": {
        "label": "马达加斯加",
        "bounds": (43.0, 51.0, -27.0, -11.0),
        "description": "Madagascar island and Mozambique Channel",
        "zoom": 9,
    },
    # ── Africa / Southern ─────────────────────────────────────────────────────
    "south_africa": {
        "label": "南非开普",
        "bounds": (16.0, 33.0, -35.0, -21.0),
        "description": "Cape of Good Hope, South African coast",
        "zoom": 9,
    },
    "cape_verde": {
        "label": "佛得角",
        "bounds": (-26.0, -21.5, 14.5, 17.5),
        "description": "Cape Verde archipelago, eastern Atlantic",
    },
    # ── Pacific / Americas ────────────────────────────────────────────────────
    "new_zealand": {
        "label": "新西兰",
        "bounds": (165.5, 178.5, -48.0, -33.5),
        "description": "New Zealand North and South Islands",
        "zoom": 9,
    },
    "alaska": {
        "label": "阿拉斯加",
        "bounds": (-168.0, -141.0, 54.0, 62.0),
        "description": "Alaska Peninsula and Gulf of Alaska",
        "zoom": 8,
    },
    "galapagos": {
        "label": "加拉帕戈斯",
        "bounds": (-92.5, -88.5, -2.5, 2.0),
        "description": "Galápagos Islands, eastern Pacific",
    },
    "gulf_mexico_yucatan": {
        "label": "墨西哥湾 / 尤卡坦",
        "bounds": (-98.0, -83.0, 17.0, 31.0),
        "description": "Gulf of Mexico, Yucatan Peninsula, Florida Keys",
        "zoom": 9,
    },
    # ── 东亚补充 ──────────────────────────────────────────────────────────
    "bohai_sea": {
        "label": "渤海",
        "bounds": (117.0, 122.5, 37.0, 41.0),
        "description": "Bohai Sea, Yellow Sea western coast, Liaodong/Shandong",
        "zoom": 11,
    },
    "east_china_sea": {
        "label": "东海",
        "bounds": (119.0, 131.0, 23.0, 34.0),
        "description": "East China Sea, continental shelf between China and Japan",
        "zoom": 9,
    },
    "sea_of_japan": {
        "label": "日本海",
        "bounds": (128.0, 142.0, 33.0, 52.0),
        "description": "Sea of Japan between Japan and Korean peninsula",
        "zoom": 8,
    },
    "taiwan_strait": {
        "label": "台湾海峡",
        "bounds": (117.0, 121.5, 22.5, 26.5),
        "description": "Taiwan Strait, Fujian coast",
        "zoom": 10,
    },
    "bashi_channel": {
        "label": "巴士海峡",
        "bounds": (118.0, 123.0, 18.0, 22.5),
        "description": "Bashi Channel / Luzon Strait between Taiwan and Philippines",
        "zoom": 10,
    },
    # ── 东南亚补充 ────────────────────────────────────────────────────────
    "singapore_malacca": {
        "label": "新加坡 / 马六甲",
        "bounds": (98.0, 106.0, 0.5, 7.0),
        "description": "Singapore, Strait of Malacca, southern Malay Peninsula",
        "zoom": 10,
    },
    "borneo": {
        "label": "婆罗洲 / 马来西亚",
        "bounds": (108.0, 119.5, -2.0, 8.0),
        "description": "Borneo, Sabah, Sarawak, Kalimantan",
        "zoom": 9,
    },
    "indonesia_west": {
        "label": "印尼西部 / 爪哇 / 苏门答腊",
        "bounds": (99.0, 118.0, -9.0, 6.0),
        "description": "Sumatra, Java, Bali, Lombok, Flores",
        "zoom": 8,
    },
    "gulf_of_thailand": {
        "label": "泰国湾 / 越南南海岸",
        "bounds": (99.0, 108.0, 5.0, 17.0),
        "description": "Gulf of Thailand, Vietnam coast, Mekong Delta",
        "zoom": 9,
    },
    # ── 南亚补充 ──────────────────────────────────────────────────────────
    "bay_of_bengal": {
        "label": "孟加拉湾",
        "bounds": (80.0, 100.0, 5.0, 23.0),
        "description": "Bay of Bengal, eastern India coast, Bangladesh",
        "zoom": 8,
    },
    "arabian_sea": {
        "label": "阿拉伯海 / 印度西岸",
        "bounds": (60.0, 78.0, 8.0, 25.0),
        "description": "Arabian Sea, western India coast, Lakshadweep",
        "zoom": 8,
    },
    # ── 欧洲补充 ──────────────────────────────────────────────────────────
    "baltic_sea": {
        "label": "波罗的海",
        "bounds": (9.0, 30.0, 54.0, 66.0),
        "description": "Baltic Sea, Gulf of Finland, Gulf of Bothnia",
        "zoom": 8,
    },
    "adriatic_sea": {
        "label": "亚得里亚海",
        "bounds": (12.0, 20.5, 38.0, 46.0),
        "description": "Adriatic Sea, Italian peninsula, Dalmatian coast",
        "zoom": 10,
    },
    "bay_of_biscay": {
        "label": "比斯开湾 / 伊比利亚",
        "bounds": (-10.0, 2.0, 42.0, 48.5),
        "description": "Bay of Biscay, Iberian Peninsula north coast, Pyrenees",
        "zoom": 9,
    },
    # ── 非洲补充 ──────────────────────────────────────────────────────────
    "east_africa_coast": {
        "label": "东非海岸 / 桑给巴尔",
        "bounds": (38.0, 46.0, -12.0, 4.0),
        "description": "East Africa coast, Zanzibar, Kenya, Tanzania",
        "zoom": 9,
    },
    "mozambique_channel": {
        "label": "莫桑比克海峡",
        "bounds": (33.0, 42.0, -25.0, -10.0),
        "description": "Mozambique Channel between Madagascar and mainland Africa",
        "zoom": 9,
    },
    # ── 太平洋岛屿补充 ────────────────────────────────────────────────────
    "guam_marianas": {
        "label": "关岛 / 马里亚纳群岛",
        "bounds": (143.5, 146.5, 12.0, 16.0),
        "description": "Guam, Northern Mariana Islands",
        "zoom": 10,
    },
    "palau": {
        "label": "帕劳",
        "bounds": (132.5, 135.5, 5.0, 9.0),
        "description": "Palau archipelago, Rock Islands",
        "zoom": 10,
    },
    "papua_new_guinea": {
        "label": "巴布亚新几内亚",
        "bounds": (140.0, 152.0, -8.0, 0.5),
        "description": "Papua New Guinea, Coral Sea coast",
        "zoom": 9,
    },
    "fiji_vanuatu": {
        "label": "斐济 / 瓦努阿图",
        "bounds": (165.0, 180.0, -22.0, -12.0),
        "description": "Fiji Islands, Vanuatu archipelago",
        "zoom": 9,
    },
    "samoa": {
        "label": "萨摩亚",
        "bounds": (-174.0, -168.0, -15.0, -11.0),
        "description": "Samoa, American Samoa",
        "zoom": 10,
    },
    "french_polynesia": {
        "label": "法属波利尼西亚 / 大溪地",
        "bounds": (-151.0, -148.0, -18.5, -15.5),
        "description": "Tahiti, Bora Bora, Moorea, Society Islands",
        "zoom": 10,
    },
    "christmas_island": {
        "label": "圣诞节岛",
        "bounds": (105.0, 106.5, -11.0, -9.5),
        "description": "Christmas Island, Australian territory in Indian Ocean",
        "zoom": 10,
    },
    # ── 美洲补充 ──────────────────────────────────────────────────────────
    "california_coast": {
        "label": "加州海岸 / 下加利福尼亚",
        "bounds": (-121.0, -109.0, 22.0, 38.0),
        "description": "California coast, Baja California, Channel Islands",
        "zoom": 9,
    },
    "eastern_caribbean": {
        "label": "东加勒比 / 小安的列斯",
        "bounds": (-63.0, -59.0, 11.0, 19.0),
        "description": "Lesser Antilles, Martinique, Barbados, Saint Lucia",
        "zoom": 10,
    },
    "brazil_coast": {
        "label": "巴西 / 亚马孙河口",
        "bounds": (-50.0, -34.0, -5.0, 6.0),
        "description": "Brazil NE coast, Amazon delta, Fernando de Noronha",
        "zoom": 9,
    },
    "french_guiana": {
        "label": "法属圭亚那",
        "bounds": (-54.0, -50.0, 2.0, 6.0),
        "description": "French Guiana coast, Kourou launch site",
        "zoom": 10,
    },
    "patagonia": {
        "label": "巴塔哥尼亚 / 麦哲伦",
        "bounds": (-76.0, -64.0, -56.0, -40.0),
        "description": "Patagonia, Strait of Magellan, Tierra del Fuego",
        "zoom": 9,
    },
    "falkland_islands": {
        "label": "福克兰群岛 / 马尔维纳斯",
        "bounds": (-62.0, -57.0, -53.0, -50.0),
        "description": "Falkland Islands (Malvinas), South Atlantic",
        "zoom": 10,
    },
    # ── 亚太 / 中国近海岛屿（第三批）────────────────────────────────────────
    "xisha_paracel": {
        "label": "西沙群岛 / 帕拉塞尔群岛",
        "bounds": (109.5, 114.5, 14.5, 18.0),
        "description": "Paracel Islands (Xisha), South China Sea",
        "zoom": 10,
    },
    "nansha_spratly": {
        "label": "南沙群岛 / 斯普拉特利群岛",
        "bounds": (108.0, 118.0, 3.5, 12.0),
        "description": "Spratly Islands (Nansha), South China Sea reefs and atolls",
        "zoom": 8,
    },
    "dongsha_pratas": {
        "label": "东沙群岛 / 普拉塔斯岛",
        "bounds": (115.5, 117.5, 19.5, 21.5),
        "description": "Pratas Islands (Dongsha), northeastern South China Sea",
        "zoom": 10,
    },
    "ogasawara": {
        "label": "小笠原群岛",
        "bounds": (140.5, 143.5, 23.5, 28.0),
        "description": "Ogasawara (Bonin) Islands, sub-tropical Pacific Japan",
        "zoom": 10,
    },
    "micronesia": {
        "label": "密克罗尼西亚联邦",
        "bounds": (138.0, 165.0, 3.5, 10.5),
        "description": "Federated States of Micronesia, Caroline Islands",
        "zoom": 8,
    },
    "marshall_islands": {
        "label": "马绍尔群岛",
        "bounds": (160.0, 172.0, 4.0, 12.0),
        "description": "Marshall Islands, Bikini Atoll, Majuro",
        "zoom": 9,
    },
    "solomon_islands": {
        "label": "所罗门群岛",
        "bounds": (155.0, 163.0, -12.0, -4.0),
        "description": "Solomon Islands, Guadalcanal, Coral Sea",
        "zoom": 9,
    },
    "new_caledonia": {
        "label": "新喀里多尼亚",
        "bounds": (162.5, 168.5, -23.0, -18.5),
        "description": "New Caledonia (Grande Terre), Loyalty Islands, French territory",
        "zoom": 10,
    },
    "tonga": {
        "label": "汤加群岛",
        "bounds": (-177.0, -173.0, -24.0, -15.0),
        "description": "Kingdom of Tonga, Polynesian island chain",
        "zoom": 10,
    },
    "kiribati_gilbert": {
        "label": "基里巴斯 / 吉尔伯特群岛",
        "bounds": (171.0, 177.5, -3.5, 4.0),
        "description": "Kiribati Gilbert Islands, Tarawa atoll",
        "zoom": 10,
    },
    # ── 美洲补充（第三批）────────────────────────────────────────────────────
    "puerto_rico_vi": {
        "label": "波多黎各 / 美属维京群岛",
        "bounds": (-68.5, -64.0, 17.0, 19.0),
        "description": "Puerto Rico, US Virgin Islands, gap between Caribbean patches",
        "zoom": 10,
    },
    "abc_venezuela": {
        "label": "ABC群岛 / 委内瑞拉加勒比",
        "bounds": (-73.0, -59.5, 10.0, 14.0),
        "description": "Aruba, Bonaire, Curacao, Venezuela Caribbean coast, Trinidad",
        "zoom": 9,
    },
    "easter_island": {
        "label": "复活节岛 / 拉帕努伊",
        "bounds": (-110.5, -108.5, -28.0, -26.0),
        "description": "Easter Island (Rapa Nui), most remote inhabited island",
        "zoom": 10,
    },
    "rio_southeast_brazil": {
        "label": "里约 / 东南巴西",
        "bounds": (-46.0, -34.0, -25.0, -14.0),
        "description": "Rio de Janeiro, Sao Paulo coast, Brazil SE seaboard",
        "zoom": 9,
    },
    "peru_chile_coast": {
        "label": "秘鲁 / 厄瓜多尔太平洋海岸",
        "bounds": (-82.0, -70.0, -18.0, -4.0),
        "description": "Peru coast, Humboldt Current, Atacama edge, Ecuador",
        "zoom": 9,
    },
    "rio_de_la_plata": {
        "label": "拉普拉塔河 / 布宜诺斯艾利斯",
        "bounds": (-60.0, -52.0, -37.0, -30.0),
        "description": "Rio de la Plata estuary, Buenos Aires, Montevideo",
        "zoom": 9,
    },
    "south_georgia": {
        "label": "南乔治亚岛",
        "bounds": (-40.0, -34.0, -56.0, -52.0),
        "description": "South Georgia and South Sandwich Islands, sub-Antarctic",
        "zoom": 10,
    },
    "bermuda": {
        "label": "百慕大",
        "bounds": (-65.5, -64.5, 32.0, 33.0),
        "description": "Bermuda, isolated mid-Atlantic British territory",
        "zoom": 10,
    },
    "central_america_pacific": {
        "label": "中美洲太平洋海岸",
        "bounds": (-92.0, -77.0, 7.0, 18.0),
        "description": "Panama, Costa Rica, Nicaragua, El Salvador Pacific coast",
        "zoom": 9,
    },
    # ── 欧洲补充（第三批）────────────────────────────────────────────────────
    "faroe_islands": {
        "label": "法罗群岛",
        "bounds": (-8.0, -5.5, 61.5, 62.5),
        "description": "Faroe Islands, Danish autonomous territory, North Atlantic",
        "zoom": 10,
    },
    "svalbard": {
        "label": "斯瓦尔巴群岛",
        "bounds": (10.0, 30.0, 76.0, 82.0),
        "description": "Svalbard archipelago, Norwegian Arctic, polar ice edge",
        "zoom": 9,
    },
    # ── 补漏（第四批）────────────────────────────────────────────────────────────
    "hainan_island": {
        "label": "海南岛",
        "bounds": (108.0, 111.5, 18.0, 20.5),
        "description": "Hainan Island, South China Sea",
        "zoom": 10,
    },
    "kuril_southern": {
        "label": "北方四岛 / 库页岛南端",
        "bounds": (141.5, 150.5, 43.0, 48.0),
        "description": "Southern Kuril Islands (Northern Territories), south Sakhalin",
        "zoom": 9,
    },
}

# ── Mapbox params ─────────────────────────────────────────────────────────────

STYLE_USER   = "mapbox"
STYLE_ID     = "satellite-v9"
TILE_SIZE    = 512
DEFAULT_ZOOM = 10
MAX_DIM      = 4096   # default longer axis of output tile
HIRES_MAX_DIM = 8192  # optional high-detail audit variant
RESOURCE_STACK_LEVELS = {
    "8k": 8192,
    "12k": 12288,
    "16k": 16384,
}
DEFAULT_RESOURCE_STACK_LEVEL = "8k"
JPEG_Q       = 92

# ── M1 GEBCO depth compositing ────────────────────────────────────────────────
# Blend weight is 0 at ≥-30m (preserve Mapbox shallow water / reef colors),
# rising to BLEND_MAX at abyssal depths.

_GEBCO_BLEND_MAX  = 0.60   # max blend at very deep ocean
_GEBCO_ONSET_M    = 30     # depth in metres where blending begins
_GEBCO_FULL_M     = 3000   # depth where max blend is reached

# Ocean depth color palette used for the GEBCO tint layer.
# These are deep-blue tones designed to push Mapbox toward natural depth perception.
_DEPTH_STOPS = [
    (   -30, ( 45, 118, 168)),
    (  -200, ( 26,  82, 140)),
    ( -1000, ( 16,  56, 112)),
    ( -3000, (  8,  34,  82)),
    (-10000, (  2,  16,  50)),
]


# ── M2 Allen Coral Atlas reef extent ──────────────────────────────────────────

_ACA_REEF_PACKAGES = {
    # Original 5
    "hawaii":              "Hawaiian-Islands-20230309235255.zip",
    "maldives":            "Central-Indian-Ocean-20230310001123.zip",
    "great_barrier_reef":  "Great-Barrier-Reef-and-Torres-Strait-20230310013521.zip",
    "philippines_central": "Philippines-20230310023925.zip",
    "caribbean_bahamas":   "Northern-Caribbean--Florida---Bahamas-20230310014129.zip",
    # Red Sea / Arabian
    "red_sea":             "Red-Sea---Gulf-of-Aden-20230310014131.zip",
    "arabian_sea":         "Northwestern-Arabian-Sea-20230310014334.zip",
    "andaman_sea":         "Andaman-Sea-20230309235804.zip",
    # South China Sea cluster
    "south_china_sea":     "South-China-Sea-20230310001832.zip",
    "nansha_spratly":      "South-China-Sea-20230310001832.zip",
    "xisha_paracel":       "South-China-Sea-20230310001832.zip",
    "dongsha_pratas":      "South-China-Sea-20230310001832.zip",
    "hainan_island":       "South-China-Sea-20230310001832.zip",
    "bashi_channel":       "Philippines-20230310023925.zip",
    # SE Asia / Indo-Pacific
    "indonesia_east":      "Southeast-Asian-Archipelago-20230310000615.zip",
    "indonesia_west":      "Southeast-Asian-Archipelago-20230310000615.zip",
    "borneo":              "Southeast-Asian-Archipelago-20230310000615.zip",
    "singapore_malacca":   "Southeast-Asian-Archipelago-20230310000615.zip",
    "palau":               "Western-Micronesia-20230310012947.zip",
    "guam_marianas":       "Western-Micronesia-20230310012947.zip",
    "papua_new_guinea":    "Eastern-Papua-New-Guinea---Solomon-Islands-20230310000210.zip",
    "solomon_islands":     "Eastern-Papua-New-Guinea---Solomon-Islands-20230310000210.zip",
    "christmas_island":    "Southeast-Asian-Archipelago-20230310000615.zip",
    "sri_lanka":           "Southern-Asia-20230310000614.zip",
    "bay_of_bengal":       "Southern-Asia-20230310000614.zip",
    # NE Asia
    "ryukyu":              "Northeastern-Asia-20230310004410.zip",
    "ogasawara":           "Northeastern-Asia-20230310004410.zip",
    # Pacific islands
    "new_caledonia":       "Coral-Sea-20230310000950.zip",
    "fiji_vanuatu":        "Southwestern-Pacific-20230309235258.zip",
    "samoa":               "Southwestern-Pacific-20230309235258.zip",
    "tonga":               "Southwestern-Pacific-20230309235258.zip",
    "micronesia":          "Eastern-Micronesia-20230310003732.zip",
    "marshall_islands":    "Eastern-Micronesia-20230310003732.zip",
    "kiribati_gilbert":    "Eastern-Micronesia-20230310003732.zip",
    "french_polynesia":    "Central-South-Pacific-20230310003051.zip",
    "easter_island":       "Eastern-Tropical-Pacific-20230310004005.zip",
    "galapagos":           "Eastern-Tropical-Pacific-20230310004005.zip",
    # Indian Ocean
    "seychelles":          "Western-Indian-Ocean-20230309235254.zip",
    "east_africa_coast":   "Eastern-Africa---Madagascar-20230309235254.zip",
    "madagascar":          "Eastern-Africa---Madagascar-20230309235254.zip",
    "mozambique_channel":  "Eastern-Africa---Madagascar-20230309235254.zip",
    # Caribbean / Atlantic
    "eastern_caribbean":   "Southeastern-Caribbean-20230310014130.zip",
    "abc_venezuela":       "Southeastern-Caribbean-20230310014130.zip",
    "puerto_rico_vi":      "Northern-Caribbean--Florida---Bahamas-20230310014129.zip",
    "gulf_mexico_yucatan": "Mesoamerica-20230310002848.zip",
    "bermuda":             "Bermuda-20230328225056.zip",
    "brazil_coast":        "Brazil-20230310004005.zip",
}


class _WKBReader:
    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.offset = offset

    def _endian(self) -> str:
        flag = self.data[self.offset]
        self.offset += 1
        if flag == 0:
            return ">"
        if flag == 1:
            return "<"
        raise ValueError(f"unsupported WKB endian flag: {flag}")

    def _u32(self, endian: str) -> int:
        value = struct.unpack_from(endian + "I", self.data, self.offset)[0]
        self.offset += 4
        return value

    def _f64(self, endian: str) -> float:
        value = struct.unpack_from(endian + "d", self.data, self.offset)[0]
        self.offset += 8
        return value

    def read_geometry(self) -> list[list[list[tuple[float, float]]]]:
        endian = self._endian()
        raw_type = self._u32(endian)
        geom_type = raw_type % 1000
        has_z = raw_type in (1001, 1002, 1003, 1004, 1005, 1006, 3001, 3002, 3003, 3004, 3005, 3006)
        has_m = raw_type in (2001, 2002, 2003, 2004, 2005, 2006, 3001, 3002, 3003, 3004, 3005, 3006)
        if geom_type == 3:
            return [self._read_polygon(endian, has_z, has_m)]
        if geom_type == 6:
            polygons: list[list[list[tuple[float, float]]]] = []
            for _ in range(self._u32(endian)):
                polygons.extend(self.read_geometry())
            return polygons
        raise ValueError(f"unsupported WKB geometry type: {raw_type}")

    def _read_polygon(self, endian: str, has_z: bool, has_m: bool) -> list[list[tuple[float, float]]]:
        rings: list[list[tuple[float, float]]] = []
        for _ in range(self._u32(endian)):
            ring: list[tuple[float, float]] = []
            for _ in range(self._u32(endian)):
                x = self._f64(endian)
                y = self._f64(endian)
                if has_z:
                    self._f64(endian)
                if has_m:
                    self._f64(endian)
                ring.append((x, y))
            rings.append(ring)
        return rings


def _aca_gpkg_path(region_id: str, out_dir: Path) -> tuple[Path | None, str | None]:
    package = _ACA_REEF_PACKAGES.get(region_id)
    if not package:
        return None, None
    package_path = CORAL_ROOT / package
    if not package_path.exists():
        print(f"  [M2] WARNING: ACA package missing for {region_id}: {package_path.name}")
        return None, package
    gpkg_dir = out_dir / "_aca_cache"
    gpkg_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = gpkg_dir / "reefextent.gpkg"
    if gpkg_path.exists() and gpkg_path.stat().st_size > 0:
        return gpkg_path, package
    with zipfile.ZipFile(package_path) as zf:
        with zf.open("Reef-Extent/reefextent.gpkg") as src, gpkg_path.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    return gpkg_path, package


def _gpkg_table_info(gpkg_path: Path) -> tuple[str, str]:
    with sqlite3.connect(gpkg_path) as con:
        row = con.execute("select table_name from gpkg_contents where data_type='features' limit 1").fetchone()
        geom = con.execute("select column_name from gpkg_geometry_columns where table_name=? limit 1", (row[0],)).fetchone()
    return row[0], geom[0]


def _gpkg_wkb_offset(blob: bytes) -> int:
    if blob[:2] != b"GP":
        return 0
    envelope_code = (blob[3] >> 1) & 0b111
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    return 8 + envelope_sizes.get(envelope_code, 0)


def _parse_gpkg_geometry(blob: bytes) -> list[list[list[tuple[float, float]]]]:
    return _WKBReader(blob, _gpkg_wkb_offset(blob)).read_geometry()


def _lonlat_to_px(
    lon: float,
    lat: float,
    lon_w: float,
    lon_e: float,
    lat_s: float,
    lat_n: float,
    out_w: int,
    out_h: int,
    scale: int,
) -> tuple[float, float]:
    x = (lon - lon_w) / (lon_e - lon_w) * (out_w * scale - 1)
    y = (lat_n - lat) / (lat_n - lat_s) * (out_h * scale - 1)
    return x, y


def m2_aca_reef_mask(
    region_id: str,
    out_dir: Path,
    lon_w: float,
    lon_e: float,
    lat_s: float,
    lat_n: float,
    out_w: int,
    out_h: int,
    oversample: int = 2,
) -> tuple[Image.Image | None, dict]:
    gpkg_path, package = _aca_gpkg_path(region_id, out_dir)
    if gpkg_path is None:
        return None, {"enabled": False, "reason": "no_package_mapping_or_missing_package", "package": package}
    table, geom_col = _gpkg_table_info(gpkg_path)
    rtree = f"rtree_{table}_{geom_col}"
    sql = (
        f'select t."{geom_col}" from "{table}" t '
        f'join "{rtree}" r on t.fid = r.id '
        "where r.maxx >= ? and r.minx <= ? and r.maxy >= ? and r.miny <= ?"
    )
    scale = max(1, oversample)
    mask = Image.new("L", (out_w * scale, out_h * scale), 0)
    draw = ImageDraw.Draw(mask)
    feature_count = 0
    polygon_count = 0
    hole_count = 0
    parse_errors = 0
    with sqlite3.connect(gpkg_path) as con:
        for (blob,) in con.execute(sql, (lon_w, lon_e, lat_s, lat_n)):
            feature_count += 1
            try:
                polygons = _parse_gpkg_geometry(blob)
            except Exception:
                parse_errors += 1
                continue
            for rings in polygons:
                if not rings:
                    continue
                polygon_count += 1
                exterior = [
                    _lonlat_to_px(lon, lat, lon_w, lon_e, lat_s, lat_n, out_w, out_h, scale)
                    for lon, lat in rings[0]
                ]
                draw.polygon(exterior, fill=255)
                for hole in rings[1:]:
                    hole_count += 1
                    hole_px = [
                        _lonlat_to_px(lon, lat, lon_w, lon_e, lat_s, lat_n, out_w, out_h, scale)
                        for lon, lat in hole
                    ]
                    draw.polygon(hole_px, fill=0)
    if scale > 1:
        mask = mask.resize((out_w, out_h), Image.Resampling.LANCZOS)
    reef_pixels = sum(mask.histogram()[17:])
    stats = {
        "enabled": True,
        "package": package,
        "gpkg": str(gpkg_path.relative_to(ROOT)),
        "features_in_bbox": feature_count,
        "polygons_rasterized": polygon_count,
        "holes_rasterized": hole_count,
        "parse_errors": parse_errors,
        "reef_pixels_gt16": reef_pixels,
        "reef_pixel_ratio_gt16": reef_pixels / float(out_w * out_h),
    }
    print(
        "  [M2] ACA reef mask "
        f"features={feature_count:,} polygons={polygon_count:,} "
        f"reef_px={reef_pixels:,} errors={parse_errors}"
    )
    return mask, stats


def apply_m2_aca_reef(base_arr: np.ndarray, mask_img: Image.Image, elev: np.ndarray | None = None) -> np.ndarray:
    """Natural reef-extent enhancement: shallow, feathered, and subtle."""
    base = base_arr.astype(np.float32)
    mask_core = np.array(mask_img, dtype=np.float32) / 255.0
    mask_feather = np.array(mask_img.filter(ImageFilter.GaussianBlur(radius=2.2)), dtype=np.float32) / 255.0
    if elev is not None:
        depth = np.maximum(-elev.astype(np.float32), 0.0)
        shallow = np.clip(1.0 - (depth - 5.0) / 115.0, 0.0, 1.0)
        gate = np.where(elev < 8.0, 0.35 + 0.65 * shallow, 0.0)
    else:
        gate = np.ones(mask_core.shape, dtype=np.float32) * 0.75
    alpha = np.clip(mask_feather * gate * 0.34, 0.0, 0.34)
    core = np.clip(mask_core * gate, 0.0, 1.0)
    reef_rgb = np.array([88, 190, 184], dtype=np.float32)
    sand_rgb = np.array([205, 214, 184], dtype=np.float32)
    target = base * 0.72 + reef_rgb[None, None, :] * 0.20 + sand_rgb[None, None, :] * 0.08
    result = base * (1.0 - alpha[:, :, None]) + target * alpha[:, :, None]
    lift = (core * 11.0)[:, :, None]
    result = result + lift * np.array([0.45, 0.95, 0.85], dtype=np.float32)[None, None, :]
    return np.clip(result, 0, 255).astype(np.uint8)


# ── M5: JRC Global Surface Water ─────────────────────────────────────────────

_JRC_OCC_CACHE: np.ndarray | None = None
_COPERNICUS_SLOPE_CACHE: np.ndarray | None = None
_COPERNICUS_ELEV_CACHE: np.ndarray | None = None
_SRTM_LANDFORMS_CACHE: np.ndarray | None = None

def _load_jrc_occ() -> np.ndarray | None:
    global _JRC_OCC_CACHE
    if _JRC_OCC_CACHE is not None:
        return _JRC_OCC_CACHE
    if not _HAS_TIFFFILE or not JRC_OCC_PATH.exists():
        return None
    _JRC_OCC_CACHE = tifffile.imread(str(JRC_OCC_PATH))  # (4096, 8192) uint8 0-100
    return _JRC_OCC_CACHE


def m5_jrc_water_mask(
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    out_w: int, out_h: int,
) -> np.ndarray | None:
    """Crop JRC GSW occurrence to region bounds. Returns uint8 (0-100) or None."""
    jrc = _load_jrc_occ()
    if jrc is None:
        return None
    px0 = round((lon_w + 180) / 360 * _JRC_W)
    px1 = round((lon_e + 180) / 360 * _JRC_W)
    py0 = round((90 - lat_n) / 180 * _JRC_H)
    py1 = round((90 - lat_s) / 180 * _JRC_H)
    px0, px1 = max(0, px0), min(_JRC_W, px1)
    py0, py1 = max(0, py0), min(_JRC_H, py1)
    crop = jrc[py0:py1, px0:px1]
    if crop.size == 0:
        return None
    occ = Image.fromarray(crop).resize((out_w, out_h), Image.BILINEAR)
    return np.array(occ, dtype=np.uint8)


_LAKE_RGB = np.array([52, 138, 195], dtype=np.float32)


def apply_m5_jrc_water(arr: np.ndarray, jrc_occ: np.ndarray | None, strength: float = 0.45) -> np.ndarray:
    """Blend lake blue onto JRC permanent-water pixels (occurrence >= 90)."""
    if jrc_occ is None:
        return arr
    water_px = int((jrc_occ >= 90).sum())
    if water_px == 0:
        return arr
    w = (jrc_occ >= 90).astype(np.float32) * strength
    base = arr.astype(np.float32)
    result = base + (_LAKE_RGB[None, None, :] - base) * w[:, :, None]
    print(f"  [M5] JRC water pixels={water_px:,}")
    return np.clip(result, 0, 255).astype(np.uint8)


# ── Batch 2: Copernicus DEM slope terrain enhancement ────────────────────────

def _crop_global_float_raster(
    arr: np.ndarray,
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    out_w: int, out_h: int,
) -> np.ndarray | None:
    h, w = arr.shape[:2]
    x0 = math.floor((lon_w + 180.0) / 360.0 * w)
    x1 = math.ceil((lon_e + 180.0) / 360.0 * w)
    y0 = math.floor((90.0 - lat_n) / 180.0 * h)
    y1 = math.ceil((90.0 - lat_s) / 180.0 * h)
    x0 = max(0, min(w - 1, x0))
    x1 = max(x0 + 1, min(w, x1))
    y0 = max(0, min(h - 1, y0))
    y1 = max(y0 + 1, min(h, y1))
    crop = arr[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    return np.array(Image.fromarray(crop.astype(np.float32), mode="F").resize((out_w, out_h), Image.BILINEAR))


def _crop_global_uint8_raster(
    arr: np.ndarray,
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    out_w: int, out_h: int,
) -> np.ndarray | None:
    h, w = arr.shape[:2]
    x0 = math.floor((lon_w + 180.0) / 360.0 * w)
    x1 = math.ceil((lon_e + 180.0) / 360.0 * w)
    y0 = math.floor((90.0 - lat_n) / 180.0 * h)
    y1 = math.ceil((90.0 - lat_s) / 180.0 * h)
    x0 = max(0, min(w - 1, x0))
    x1 = max(x0 + 1, min(w, x1))
    y0 = max(0, min(h - 1, y0))
    y1 = max(y0 + 1, min(h, y1))
    crop = arr[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    return np.array(Image.fromarray(crop.astype(np.uint8), mode="L").resize((out_w, out_h), Image.NEAREST), dtype=np.uint8)


def _load_copernicus_slope() -> np.ndarray | None:
    global _COPERNICUS_SLOPE_CACHE
    if _COPERNICUS_SLOPE_CACHE is not None:
        return _COPERNICUS_SLOPE_CACHE
    if not _HAS_TIFFFILE or not COPERNICUS_SLOPE_PATH.exists():
        return None
    _COPERNICUS_SLOPE_CACHE = tifffile.imread(str(COPERNICUS_SLOPE_PATH)).astype(np.float32)
    return _COPERNICUS_SLOPE_CACHE


def _load_copernicus_elev() -> np.ndarray | None:
    global _COPERNICUS_ELEV_CACHE
    if _COPERNICUS_ELEV_CACHE is not None:
        return _COPERNICUS_ELEV_CACHE
    if not _HAS_TIFFFILE or not COPERNICUS_ELEV_PATH.exists():
        return None
    _COPERNICUS_ELEV_CACHE = tifffile.imread(str(COPERNICUS_ELEV_PATH)).astype(np.float32)
    return _COPERNICUS_ELEV_CACHE


def _load_srtm_landforms() -> np.ndarray | None:
    global _SRTM_LANDFORMS_CACHE
    if _SRTM_LANDFORMS_CACHE is not None:
        return _SRTM_LANDFORMS_CACHE
    if not _HAS_TIFFFILE or not SRTM_LANDFORMS_PATH.exists():
        return None
    _SRTM_LANDFORMS_CACHE = tifffile.imread(str(SRTM_LANDFORMS_PATH)).astype(np.uint8)
    return _SRTM_LANDFORMS_CACHE


def b2_copernicus_dem_layers(
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    out_w: int, out_h: int,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    slope_global = _load_copernicus_slope()
    elev_global = _load_copernicus_elev()
    if slope_global is None or elev_global is None:
        return None, None
    slope = _crop_global_float_raster(slope_global, lon_w, lon_e, lat_s, lat_n, out_w, out_h)
    elev = _crop_global_float_raster(elev_global, lon_w, lon_e, lat_s, lat_n, out_w, out_h)
    if slope is None or elev is None:
        return None, None
    slope = np.where(slope < -1000.0, 0.0, slope)
    elev = np.where(elev < -1000.0, 0.0, elev)
    return slope.astype(np.float32), elev.astype(np.float32)


def apply_b2_dem_slope(
    arr: np.ndarray,
    dem_slope: np.ndarray | None,
    dem_elev: np.ndarray | None,
    climate_family: str | None = None,
) -> tuple[np.ndarray, dict[str, float] | None]:
    if dem_slope is None or dem_elev is None:
        return arr, None

    slope = np.nan_to_num(dem_slope.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    elev = np.nan_to_num(dem_elev.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    land = elev > 1.0
    if not land.any():
        return arr, {
            "terrain_pixels": 0.0,
            "steep_pixels": 0.0,
            "alpine_pixels": 0.0,
            "slope_p60": 0.0,
            "slope_p95": 0.0,
        }

    land_slope = slope[land]
    slope_p60 = float(np.percentile(land_slope, 60))
    slope_p97 = float(np.percentile(land_slope, 97))
    if slope_p97 <= slope_p60 + 1e-5:
        return arr, {
            "terrain_pixels": float(land.sum()),
            "steep_pixels": 0.0,
            "alpine_pixels": 0.0,
            "slope_p60": slope_p60,
            "slope_p95": float(np.percentile(land_slope, 95)),
        }

    slope_norm = np.clip((slope - slope_p60) / (slope_p97 - slope_p60), 0.0, 1.0)
    relief = np.power(slope_norm, 0.82) * land.astype(np.float32)
    highland = np.clip((elev - 700.0) / 2600.0, 0.0, 1.0) * land.astype(np.float32)
    alpine = relief * highland

    terrain_rgb = {
        "arid": np.array([232, 207, 170], dtype=np.float32),
        "cold": np.array([204, 214, 220], dtype=np.float32),
        "polar": np.array([214, 222, 232], dtype=np.float32),
        "tropical": np.array([188, 206, 184], dtype=np.float32),
        "temperate": np.array([196, 208, 188], dtype=np.float32),
    }.get(climate_family or "", np.array([198, 208, 190], dtype=np.float32))

    base = arr.astype(np.float32)
    terrain_alpha = relief * (0.10 + 0.10 * highland)
    terrain_target = base * 0.88 + terrain_rgb[None, None, :] * 0.12
    result = base * (1.0 - terrain_alpha[:, :, None]) + terrain_target * terrain_alpha[:, :, None]

    local_gain = 1.0 + relief[:, :, None] * 0.14
    result = (result - 128.0) * local_gain + 128.0
    result += alpine[:, :, None] * np.array([12.0, 14.0, 18.0], dtype=np.float32)[None, None, :]

    stats = {
        "terrain_pixels": float(land.sum()),
        "steep_pixels": float((relief > 0.22).sum()),
        "alpine_pixels": float((alpine > 0.16).sum()),
        "slope_p60": slope_p60,
        "slope_p95": float(np.percentile(slope[land], 95)),
    }
    print(
        "  [B2] Copernicus slope "
        f"terrain_px={int(stats['terrain_pixels']):,} "
        f"steep_px={int(stats['steep_pixels']):,} "
        f"alpine_px={int(stats['alpine_pixels']):,} "
        f"slope_p60={stats['slope_p60']:.3f} "
        f"slope_p95={stats['slope_p95']:.3f}"
    )
    return np.clip(result, 0, 255).astype(np.uint8), stats


# ── Batch 3: SRTM landforms terrain semantics ────────────────────────────────

def b3_srtm_landforms(
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    out_w: int, out_h: int,
) -> np.ndarray | None:
    landforms = _load_srtm_landforms()
    if landforms is None:
        return None
    return _crop_global_uint8_raster(landforms, lon_w, lon_e, lat_s, lat_n, out_w, out_h)


def _soft_mask_from_classes(landforms: np.ndarray, classes: set[int], blur_radius: float) -> np.ndarray:
    mask = np.isin(landforms, list(classes)).astype(np.uint8) * 255
    mask_img = Image.fromarray(mask, mode="L")
    if blur_radius > 0:
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return np.array(mask_img, dtype=np.float32) / 255.0


def apply_b3_landforms(
    arr: np.ndarray,
    landforms: np.ndarray | None,
    climate_family: str | None = None,
) -> tuple[np.ndarray, dict[str, float] | None]:
    if landforms is None:
        return arr, None

    valid = landforms != 0
    if not valid.any():
        return arr, {
            "valid_pixels": 0.0,
            "ridge_pixels": 0.0,
            "upper_pixels": 0.0,
            "lower_pixels": 0.0,
            "valley_plain_pixels": 0.0,
        }

    ridge = _soft_mask_from_classes(landforms, {11, 12, 13, 14, 15}, 1.4)
    upper = _soft_mask_from_classes(landforms, {21, 22, 23, 24}, 1.1)
    lower = _soft_mask_from_classes(landforms, {31, 32, 33}, 1.0)
    valley = _soft_mask_from_classes(landforms, {34}, 1.0)
    plain = _soft_mask_from_classes(landforms, {41, 42}, 1.2)

    ridge_rgb = {
        "arid": np.array([226, 206, 176], dtype=np.float32),
        "cold": np.array([214, 220, 228], dtype=np.float32),
        "polar": np.array([222, 228, 234], dtype=np.float32),
        "tropical": np.array([194, 208, 192], dtype=np.float32),
        "temperate": np.array([202, 212, 196], dtype=np.float32),
    }.get(climate_family or "", np.array([204, 212, 198], dtype=np.float32))
    valley_rgb = {
        "arid": np.array([188, 166, 138], dtype=np.float32),
        "cold": np.array([178, 188, 196], dtype=np.float32),
        "polar": np.array([182, 190, 200], dtype=np.float32),
        "tropical": np.array([152, 182, 148], dtype=np.float32),
        "temperate": np.array([168, 184, 158], dtype=np.float32),
    }.get(climate_family or "", np.array([170, 184, 160], dtype=np.float32))
    plain_rgb = {
        "arid": np.array([226, 202, 164], dtype=np.float32),
        "cold": np.array([198, 206, 212], dtype=np.float32),
        "polar": np.array([204, 212, 220], dtype=np.float32),
        "tropical": np.array([176, 198, 170], dtype=np.float32),
        "temperate": np.array([186, 198, 178], dtype=np.float32),
    }.get(climate_family or "", np.array([188, 200, 180], dtype=np.float32))

    base = arr.astype(np.float32)
    ridge_alpha = np.clip(ridge * 0.16 + upper * 0.06, 0.0, 0.20)
    valley_alpha = np.clip(valley * 0.10 + lower * 0.04, 0.0, 0.14)
    plain_alpha = np.clip(plain * 0.08, 0.0, 0.08)

    result = base.copy()
    ridge_target = result * 0.86 + ridge_rgb[None, None, :] * 0.14
    result = result * (1.0 - ridge_alpha[:, :, None]) + ridge_target * ridge_alpha[:, :, None]
    result = (result - 128.0) * (1.0 + ridge[:, :, None] * 0.12 + upper[:, :, None] * 0.05) + 128.0

    valley_target = result * 0.90 + valley_rgb[None, None, :] * 0.10
    result = result * (1.0 - valley_alpha[:, :, None]) + valley_target * valley_alpha[:, :, None]
    result -= valley[:, :, None] * np.array([8.0, 7.0, 6.0], dtype=np.float32)[None, None, :]
    result -= lower[:, :, None] * np.array([3.0, 2.0, 2.0], dtype=np.float32)[None, None, :]

    plain_target = result * 0.92 + plain_rgb[None, None, :] * 0.08
    result = result * (1.0 - plain_alpha[:, :, None]) + plain_target * plain_alpha[:, :, None]
    result += plain[:, :, None] * np.array([3.0, 2.0, 1.0], dtype=np.float32)[None, None, :]

    stats = {
        "valid_pixels": float(valid.sum()),
        "ridge_pixels": float(np.isin(landforms, [11, 12, 13, 14, 15]).sum()),
        "upper_pixels": float(np.isin(landforms, [21, 22, 23, 24]).sum()),
        "lower_pixels": float(np.isin(landforms, [31, 32, 33]).sum()),
        "valley_plain_pixels": float(np.isin(landforms, [34, 41, 42]).sum()),
    }
    print(
        "  [B3] SRTM landforms "
        f"valid_px={int(stats['valid_pixels']):,} "
        f"ridge_px={int(stats['ridge_pixels']):,} "
        f"upper_px={int(stats['upper_pixels']):,} "
        f"lower_px={int(stats['lower_pixels']):,} "
        f"valley_plain_px={int(stats['valley_plain_pixels']):,}"
    )
    return np.clip(result, 0, 255).astype(np.uint8), stats


# ── M3/M4 layer functions ──────────────────────────────────────────────────────

_TEMP_BIAS_RGB: dict[str, np.ndarray] = {
    "slightly_warm": np.array([1.012, 1.000, 0.990], dtype=np.float32),
    "warm_dry":      np.array([1.018, 1.003, 0.982], dtype=np.float32),
    "neutral":       np.array([1.000, 1.000, 1.000], dtype=np.float32),
    "cool":          np.array([0.988, 0.996, 1.012], dtype=np.float32),
    "cold_ice":      np.array([0.980, 0.992, 1.018], dtype=np.float32),
    "ocean_default": np.array([1.000, 1.000, 1.000], dtype=np.float32),
}

_LAND_TINT_RGB: dict[str, np.ndarray] = {
    "green_ecology_detail": np.array([0.96, 1.05, 0.94], dtype=np.float32),
    "sand_rock_warmth":     np.array([1.04, 1.01, 0.93], dtype=np.float32),
    "ice_cool_white":       np.array([0.97, 0.98, 1.03], dtype=np.float32),
    "urban_neutral":        np.array([1.01, 1.01, 1.00], dtype=np.float32),
}


def apply_m4_temperature(arr: np.ndarray, temp_bias: str) -> np.ndarray:
    rgb_mult = _TEMP_BIAS_RGB.get(temp_bias, _TEMP_BIAS_RGB["neutral"])
    if np.allclose(rgb_mult, 1.0):
        return arr
    result = arr.astype(np.float32) * rgb_mult[None, None, :]
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_m3_land_tint(arr: np.ndarray, elev: np.ndarray | None, land_tint: str, land_strength: float) -> np.ndarray:
    if land_tint == "none" or land_strength <= 0 or elev is None:
        return arr
    tint = _LAND_TINT_RGB.get(land_tint)
    if tint is None:
        return arr
    land_mask = (elev > 0).astype(np.float32) * land_strength
    base = arr.astype(np.float32)
    tinted = base * tint[None, None, :]
    result = base * (1.0 - land_mask[:, :, None]) + tinted * land_mask[:, :, None]
    return np.clip(result, 0, 255).astype(np.uint8)


# ── Token ─────────────────────────────────────────────────────────────────────

def _load_token() -> str | None:
    token = os.environ.get("MAPBOX_TOKEN")
    if token:
        return token.strip()
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for raw in env_path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == "MAPBOX_TOKEN":
            return v.strip().strip('"').strip("'")
    return None


# ── Web Mercator helpers ──────────────────────────────────────────────────────

def _lon_to_tx(lon: float, z: int) -> float:
    return (lon + 180.0) / 360.0 * (2 ** z)


def _lat_to_ty(lat: float, z: int) -> float:
    lat_rad = math.radians(lat)
    return (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * (2 ** z)


# ── M0: Mapbox tile download + stitch ─────────────────────────────────────────

def _download_tile(token: str, z: int, x: int, y: int, cache_dir: Path) -> Image.Image:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{z}_{x}_{y}.jpg"
    if cache_path.exists() and cache_path.stat().st_size > 1024:
        return Image.open(cache_path).convert("RGB")

    encoded = urllib.parse.quote(token, safe="")
    url = (
        f"https://api.mapbox.com/styles/v1/{STYLE_USER}/{STYLE_ID}"
        f"/tiles/{TILE_SIZE}/{z}/{x}/{y}?access_token={encoded}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "RodiO-RDL/2.0"})

    last_err: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            time.sleep(2 * attempt)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                if res.status != 200:
                    raise RuntimeError(f"HTTP {res.status}")
                data = res.read()
            cache_path.write_bytes(data)
            return Image.open(io.BytesIO(data)).convert("RGB")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:240]
            raise RuntimeError(f"Mapbox tile HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, OSError) as e:
            last_err = e
            continue

    raise RuntimeError(f"Mapbox tile failed after 3 attempts: {last_err}") from last_err


def m0_mapbox_base(
    token: str,
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    zoom: int,
    out_w: int, out_h: int,
    region_id: str,
) -> Image.Image:
    """Download and stitch Mapbox tiles, crop to bounds, resize to (out_w, out_h)."""
    x_w = _lon_to_tx(lon_w, zoom)
    x_e = _lon_to_tx(lon_e, zoom)
    y_n = _lat_to_ty(lat_n, zoom)
    y_s = _lat_to_ty(lat_s, zoom)

    tx0, tx1 = math.floor(x_w), math.floor(x_e)
    ty0, ty1 = math.floor(y_n), math.floor(y_s)
    cols = tx1 - tx0 + 1
    rows = ty1 - ty0 + 1
    n_tiles = cols * rows
    print(f"  [M0] tiles: x[{tx0},{tx1}] y[{ty0},{ty1}] = {n_tiles} requests  zoom={zoom}")

    cache_dir = TILE_CACHE / STYLE_ID / region_id / f"z{zoom}"
    mosaic = Image.new("RGB", (cols * TILE_SIZE, rows * TILE_SIZE))
    done = 0
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            tile = _download_tile(token, zoom, tx, ty, cache_dir)
            mosaic.paste(tile, ((tx - tx0) * TILE_SIZE, (ty - ty0) * TILE_SIZE))
            done += 1
            if done == 1 or done == n_tiles or done % 50 == 0:
                print(f"  [M0] {done}/{n_tiles}")

    left   = round((x_w - tx0) * TILE_SIZE)
    right  = round((x_e - tx0) * TILE_SIZE)
    top    = round((y_n - ty0) * TILE_SIZE)
    bottom = round((y_s - ty0) * TILE_SIZE)
    crop = mosaic.crop((left, top, right, bottom))
    return crop.resize((out_w, out_h), Image.LANCZOS)


# ── M1: GEBCO depth layer ─────────────────────────────────────────────────────

def _gebco_path(lon_w: float, lon_e: float, lat_s: float, lat_n: float) -> Path:
    def _fmt(v: float) -> str:
        return str(int(v)) + ".0"
    return GEBCO_DIR / (
        f"gebco_2026_sub_ice_n{_fmt(lat_n)}_s{_fmt(lat_s)}"
        f"_w{_fmt(lon_w)}_e{_fmt(lon_e)}_geotiff.tif"
    )


def m1_gebco_elevation(
    lon_w: float, lon_e: float, lat_s: float, lat_n: float,
    out_w: int, out_h: int,
) -> np.ndarray | None:
    """Load and stitch GEBCO quadrant TIFFs for the region, return float32 elevation array."""
    if not _HAS_TIFFFILE:
        print("  [M1] WARNING: tifffile not installed, skipping GEBCO layer")
        return None

    lat_bands = []
    if lat_n > 0:
        lat_bands.append((0.0, 90.0))
    if lat_s < 0:
        lat_bands.append((-90.0, 0.0))

    lon_bands = []
    for ls in [-180.0, -90.0, 0.0, 90.0]:
        le = ls + 90.0
        if ls < lon_e and le > lon_w:
            lon_bands.append((ls, le))

    total_lon = lon_e - lon_w
    total_lat = lat_n - lat_s
    canvas = np.zeros((out_h, out_w), dtype=np.float32)
    loaded = 0

    for (qlat_s, qlat_n) in lat_bands:
        for (qlon_w, qlon_e) in lon_bands:
            path = _gebco_path(qlon_w, qlon_e, qlat_s, qlat_n)
            if not path.exists():
                print(f"  [M1] WARNING: {path.name} not found, skipping quadrant")
                continue
            print(f"  [M1] loading {path.name}")
            elev_raw = tifffile.imread(str(path)).astype(np.float32)

            isec_lon_w = max(lon_w, qlon_w)
            isec_lon_e = min(lon_e, qlon_e)
            isec_lat_s = max(lat_s, qlat_s)
            isec_lat_n = min(lat_n, qlat_n)
            qh, qw = elev_raw.shape

            sx0 = round((isec_lon_w - qlon_w) / 90 * qw)
            sx1 = round((isec_lon_e - qlon_w) / 90 * qw)
            sy0 = round((qlat_n - isec_lat_n) / 90 * qh)
            sy1 = round((qlat_n - isec_lat_s) / 90 * qh)
            sx0, sx1 = max(0, sx0), min(qw, sx1)
            sy0, sy1 = max(0, sy0), min(qh, sy1)
            elev_crop = elev_raw[sy0:sy1, sx0:sx1]

            dx0 = round((isec_lon_w - lon_w) / total_lon * out_w)
            dx1 = round((isec_lon_e - lon_w) / total_lon * out_w)
            dy0 = round((lat_n - isec_lat_n) / total_lat * out_h)
            dy1 = round((lat_n - isec_lat_s) / total_lat * out_h)
            dx0, dx1 = max(0, dx0), min(out_w, dx1)
            dy0, dy1 = max(0, dy0), min(out_h, dy1)
            dw, dh = dx1 - dx0, dy1 - dy0

            if dw <= 0 or dh <= 0 or elev_crop.size == 0:
                continue
            e_img = Image.fromarray(elev_crop, mode="F").resize((dw, dh), Image.BILINEAR)
            canvas[dy0:dy1, dx0:dx1] = np.array(e_img)
            loaded += 1

    if loaded == 0:
        print("  [M1] no GEBCO quadrants found, skipping depth layer")
        return None

    print(f"  [M1] elevation range: {canvas.min():.0f}m … {canvas.max():.0f}m")
    return canvas


def _depth_to_rgb(elev: np.ndarray) -> np.ndarray:
    """Map elevation to depth color (ocean only). Land values ignored (masked out later)."""
    h, w = elev.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)
    stops = _DEPTH_STOPS
    for i in range(len(stops) - 1):
        depth_hi, color_hi = stops[i]
        depth_lo, color_lo = stops[i + 1]
        if i == 0:
            mask = elev >= depth_hi
        else:
            mask = (elev < stops[i - 1][0]) & (elev >= depth_hi)
        if not mask.any():
            continue
        band = float(depth_hi - depth_lo)
        t = np.clip((elev[mask] - depth_lo) / band, 0, 1) if band != 0 else np.ones(mask.sum())
        c_hi = np.array(color_hi, dtype=np.float32)
        c_lo = np.array(color_lo, dtype=np.float32)
        rgb[mask] = c_hi[None, :] * t[:, None] + c_lo[None, :] * (1 - t[:, None])
    # depths below last stop
    mask_deep = elev < stops[-1][0]
    if mask_deep.any():
        rgb[mask_deep] = np.array(stops[-1][1], dtype=np.float32)
    return rgb


def _depth_blend_weights(elev: np.ndarray) -> np.ndarray:
    """
    Per-pixel GEBCO blend weight based on depth.
    0 at ≥ -_GEBCO_ONSET_M (preserve Mapbox shallow/reef colors),
    rising to _GEBCO_BLEND_MAX at ≥ _GEBCO_FULL_M depth.
    """
    w = np.zeros(elev.shape, dtype=np.float32)
    ocean = elev < 0
    if not ocean.any():
        return w
    depth = -elev[ocean]  # positive metres below surface
    t = np.clip((depth - _GEBCO_ONSET_M) / (_GEBCO_FULL_M - _GEBCO_ONSET_M), 0, 1)
    w[ocean] = t * _GEBCO_BLEND_MAX
    return w


def apply_m1(base_arr: np.ndarray, elev: np.ndarray) -> np.ndarray:
    """Blend GEBCO depth tint onto Mapbox base. Land pixels unaffected."""
    depth_rgb = _depth_to_rgb(elev)
    weights   = _depth_blend_weights(elev)
    w3 = weights[:, :, None]
    result = base_arr.astype(np.float32) * (1 - w3) + depth_rgb * w3
    ocean_px = (elev < 0).sum()
    print(f"  [M1] depth layer applied  ocean_px={ocean_px:,}  max_blend={weights.max():.2f}")
    return np.clip(result, 0, 255).astype(np.uint8)


# ── Noon Air pass ─────────────────────────────────────────────────────────────

def noon_air_pass(img: Image.Image, sat_bias: float = 1.0, contrast_bias: float = 1.0) -> Image.Image:
    """
    Subtle aesthetic finish: keep satellite realism, push toward
    RodiO's restrained noon palette (warmer, slightly lifted).
    sat_bias / contrast_bias come from M4 Köppen climate hints.
    """
    out = ImageEnhance.Color(img).enhance(1.04 * sat_bias)
    out = ImageEnhance.Contrast(out).enhance(1.06 * contrast_bias)
    out = ImageEnhance.Brightness(out).enhance(1.22)
    out = ImageEnhance.Sharpness(out).enhance(1.10)
    out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    return out


# ── Output sizing ─────────────────────────────────────────────────────────────

def _output_dims(
    lon_w: float,
    lon_e: float,
    lat_s: float,
    lat_n: float,
    max_dim: int = MAX_DIM,
) -> tuple[int, int]:
    """
    Scale so the longer geographic axis = max_dim pixels.
    Aspect ratio is preserved in geographic (not Mercator) space.
    """
    lon_span = lon_e - lon_w
    lat_span = lat_n - lat_s
    if lon_span >= lat_span:
        out_w = max_dim
        out_h = max(256, round(max_dim * lat_span / lon_span))
    else:
        out_h = max_dim
        out_w = max(256, round(max_dim * lon_span / lat_span))
    return out_w, out_h


# ── Main compositor ───────────────────────────────────────────────────────────

def generate_region(
    region_id: str,
    zoom: int | None = None,
    zoom_bias: int = 0,
    max_dim: int = MAX_DIM,
    use_gebco: bool = True,
    use_aca_reef: bool = False,
    use_m3m4: bool = False,
    use_dem_slope: bool = False,
    use_landforms: bool = False,
    dry_run: bool = False,
) -> Path:
    if region_id not in REGIONS:
        raise SystemExit(f"Unknown region '{region_id}'. Use --list to see options.")

    cfg = REGIONS[region_id]
    # Per-region zoom default; CLI --zoom overrides if explicitly set
    base_zoom = zoom if zoom is not None else cfg.get("zoom", DEFAULT_ZOOM)
    effective_zoom = max(0, base_zoom + zoom_bias)
    lon_w, lon_e, lat_s, lat_n = cfg["bounds"]
    out_w, out_h = _output_dims(lon_w, lon_e, lat_s, lat_n, max_dim=max_dim)
    variant_suffix = ""
    if max_dim != MAX_DIM:
        if max_dim % 1024 == 0:
            variant_suffix = f"_{max_dim // 1024}k"
        else:
            variant_suffix = f"_{max_dim}px"

    out_dir   = RDL_OUT / region_id
    raw_path   = out_dir / f"tile_mapbox{variant_suffix}.jpg"
    noon_path  = out_dir / f"tile_noon_air_mapbox{variant_suffix}.jpg"
    m3m4_path  = out_dir / f"tile_noon_air_mapbox_m3m4{variant_suffix}.jpg"
    raw_aca_path  = out_dir / f"tile_mapbox_aca_reef{variant_suffix}.jpg"
    noon_aca_path = out_dir / f"tile_noon_air_mapbox_aca_reef{variant_suffix}.jpg"
    aca_mask_path = out_dir / f"aca_reef_mask{variant_suffix}.png"
    aca_meta_path = out_dir / f"aca_reef_meta{variant_suffix}.json"
    dem_path = out_dir / f"tile_noon_air_mapbox_dem{variant_suffix}.jpg"
    dem_m3m4_path = out_dir / f"tile_noon_air_mapbox_m3m4_dem{variant_suffix}.jpg"
    landforms_path = out_dir / f"tile_noon_air_mapbox_landforms{variant_suffix}.jpg"
    landforms_m3m4_path = out_dir / f"tile_noon_air_mapbox_m3m4_landforms{variant_suffix}.jpg"
    landforms_dem_path = out_dir / f"tile_noon_air_mapbox_m3m4_dem_landforms{variant_suffix}.jpg"
    meta_path = out_dir / f"mapbox_meta{variant_suffix}.json"

    print(f"\n{'═'*60}")
    print(f"  Region : {region_id}  ({cfg['label']})")
    print(f"  Bounds : lon[{lon_w}, {lon_e}]  lat[{lat_s}, {lat_n}]")
    print(f"  Output : {out_w}×{out_h}  zoom={effective_zoom} (base={base_zoom}, bias={zoom_bias:+d})  variant={variant_suffix or 'default'}")
    print(f"  Layers : M0=Mapbox  M1=GEBCO={'on' if use_gebco else 'off'}  M2_ACA_REEF={'on' if use_aca_reef else 'off'}  M3M4={'on' if use_m3m4 else 'off'}  B2_DEM={'on' if use_dem_slope else 'off'}  B3_LANDFORMS={'on' if use_landforms else 'off'}  M5_JRC=off(removed)")
    print(f"{'═'*60}")

    if dry_run:
        print(f"  → DRY RUN: would write {noon_path}")
        return noon_path

    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    result_arr: np.ndarray | None = None
    elev: np.ndarray | None = None
    reuse_existing_base = (use_aca_reef or use_m3m4) and raw_path.exists() and raw_path.stat().st_size > 1024

    if reuse_existing_base:
        print(f"  [M0/M1] reusing existing {raw_path.name} for ACA reef output")
        result_arr = np.array(Image.open(raw_path).convert("RGB"))
        if use_gebco:
            elev = m1_gebco_elevation(lon_w, lon_e, lat_s, lat_n, out_w, out_h)
    else:
        token = _load_token()
        if not token:
            raise SystemExit("ERROR: MAPBOX_TOKEN not found in environment or .env")

        # ── M0: Mapbox base ───────────────────────────────────────────────────
        mapbox_img = m0_mapbox_base(token, lon_w, lon_e, lat_s, lat_n, effective_zoom, out_w, out_h, region_id)

        # ── M1: GEBCO depth layer ─────────────────────────────────────────────
        elev = m1_gebco_elevation(lon_w, lon_e, lat_s, lat_n, out_w, out_h)
        if elev is not None:
            result_arr = apply_m1(np.array(mapbox_img), elev)

        if result_arr is None:
            result_arr = np.array(mapbox_img)

        # ── Save raw composite ────────────────────────────────────────────────
        raw_img = Image.fromarray(result_arr)
        raw_img.save(str(raw_path), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)

        # ── Noon Air pass ─────────────────────────────────────────────────────
        noon_img = noon_air_pass(raw_img)
        noon_img.save(str(noon_path), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)

    # ── M3/M4 candidate (non-destructive, reuses raw base) ────────────────────
    hints = _get_m3m4_hints(region_id) if (use_m3m4 or use_dem_slope) else None
    m3m4_arr: np.ndarray | None = None
    if use_m3m4:
        if hints:
            m3m4_arr = result_arr.copy()
            m4 = hints["m4_climate_baseline"]
            m3 = hints["m3_land_bias"]
            m3m4_arr = apply_m4_temperature(m3m4_arr, m4["temperature_bias"])
            m3m4_arr = apply_m3_land_tint(m3m4_arr, elev, m3["land_tint"], m3["land_strength"])
            m3m4_img = noon_air_pass(
                Image.fromarray(m3m4_arr),
                sat_bias=m4["saturation_bias"],
                contrast_bias=m4["contrast_bias"],
            )
            m3m4_img.save(str(m3m4_path), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
            print(f"  [M3/M4] climate={hints['climate_family']} land={hints['land_family']} → {m3m4_path.name}")
        else:
            print(f"  [M3/M4] no hints found for {region_id}, skipping")

    if use_dem_slope:
        dem_slope, dem_elev = b2_copernicus_dem_layers(lon_w, lon_e, lat_s, lat_n, out_w, out_h)
        dem_base = m3m4_arr.copy() if m3m4_arr is not None else result_arr.copy()
        dem_climate = hints["climate_family"] if hints else None
        dem_arr, dem_stats = apply_b2_dem_slope(dem_base, dem_slope, dem_elev, dem_climate)
        if dem_stats:
            if hints:
                m4 = hints["m4_climate_baseline"]
                dem_img = noon_air_pass(
                    Image.fromarray(dem_arr),
                    sat_bias=m4["saturation_bias"],
                    contrast_bias=m4["contrast_bias"],
                )
            else:
                dem_img = noon_air_pass(Image.fromarray(dem_arr))
            dem_out = dem_m3m4_path if m3m4_arr is not None else dem_path
            dem_img.save(str(dem_out), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
            print(f"  [B2] DEM terrain candidate → {dem_out.name}")

    if use_landforms:
        landforms = b3_srtm_landforms(lon_w, lon_e, lat_s, lat_n, out_w, out_h)
        land_base = result_arr.copy()
        land_out = landforms_path
        if use_dem_slope and 'dem_arr' in locals() and dem_stats:
            land_base = dem_arr.copy()
            land_out = landforms_dem_path
        elif m3m4_arr is not None:
            land_base = m3m4_arr.copy()
            land_out = landforms_m3m4_path
        land_climate = hints["climate_family"] if hints else None
        land_arr, land_stats = apply_b3_landforms(land_base, landforms, land_climate)
        if land_stats and land_stats["valid_pixels"] > 0:
            if hints:
                m4 = hints["m4_climate_baseline"]
                land_img = noon_air_pass(
                    Image.fromarray(land_arr),
                    sat_bias=m4["saturation_bias"],
                    contrast_bias=m4["contrast_bias"],
                )
            else:
                land_img = noon_air_pass(Image.fromarray(land_arr))
            land_img.save(str(land_out), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
            print(f"  [B3] landform candidate → {land_out.name}")
        else:
            # Keep the candidate file family complete even when the global landform
            # raster has no valid non-zero classes inside this bbox.
            if hints:
                m4 = hints["m4_climate_baseline"]
                fallback_img = noon_air_pass(
                    Image.fromarray(land_base),
                    sat_bias=m4["saturation_bias"],
                    contrast_bias=m4["contrast_bias"],
                )
            else:
                fallback_img = noon_air_pass(Image.fromarray(land_base))
            fallback_img.save(str(land_out), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
            print(f"  [B3] fallback copy (no valid landforms in bbox) → {land_out.name}")

    aca_stats: dict | None = None
    if use_aca_reef:
        reef_mask, aca_stats = m2_aca_reef_mask(region_id, out_dir, lon_w, lon_e, lat_s, lat_n, out_w, out_h)
        if reef_mask is not None:
            aca_arr = apply_m2_aca_reef(result_arr, reef_mask, elev)
            aca_raw_img = Image.fromarray(aca_arr)
            aca_noon_img = noon_air_pass(aca_raw_img)
            reef_mask.save(str(aca_mask_path))
            aca_raw_img.save(str(raw_aca_path), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
            aca_noon_img.save(str(noon_aca_path), "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
            aca_meta_path.write_text(json.dumps({
                "region_id": region_id,
                "layer": "M2_aca_reef_extent",
                "method": "sqlite3 + GeoPackageBinary/WKB parser + Pillow raster mask",
                "mask": aca_mask_path.name,
                "raw_tile": raw_aca_path.name,
                "noon_air_tile": noon_aca_path.name,
                "stats": aca_stats,
                "visual_treatment": {
                    "depth_gate": (
                        "strongest near 0 to -120m; disabled on land"
                        if elev is not None
                        else "not applied; GEBCO elevation unavailable in current runtime"
                    ),
                    "feather": "Gaussian blur radius 2.2px",
                    "max_alpha": 0.34,
                    "intent": "subtle shallow-water reef/atoll detail, not debug cyan overlay",
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False, indent=2))

    elapsed = time.time() - t0

    # ── Metadata ──────────────────────────────────────────────────────────────
    meta = {
        "region_id":   region_id,
        "label":       cfg["label"],
        "description": cfg["description"],
        "layers": {
            "M0": "mapbox_satellite-v9",
            "M1": "gebco_2026_depth_tint" if use_gebco else "disabled",
            "M2_ACA_REEF": "allen_coral_atlas_reef_extent" if use_aca_reef else "disabled",
        },
        "style":  f"{STYLE_USER}/{STYLE_ID}",
        "base_zoom": base_zoom,
        "zoom":   effective_zoom,
        "zoom_bias": zoom_bias,
        "max_dim": max_dim,
        "variant_suffix": variant_suffix or "default",
        "bounds": {"lon_w": lon_w, "lon_e": lon_e, "lat_s": lat_s, "lat_n": lat_n},
        "output_px": out_w,
        "output_h_px": out_h,
        "gebco_blend_max": _GEBCO_BLEND_MAX,
        "gebco_onset_m":   _GEBCO_ONSET_M,
        "gebco_full_m":    _GEBCO_FULL_M,
        "raw_tile":     raw_path.name,
        "noon_air_tile": noon_path.name,
        "aca_reef_tile": noon_aca_path.name if use_aca_reef and aca_stats and aca_stats.get("enabled") else None,
        "aca_reef_stats": aca_stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s":    round(elapsed, 1),
        "token_written": False,
        "attribution": "Mapbox Satellite imagery — keep Mapbox attribution in production UI.",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    print(f"  ✓ {raw_path.name}  ({raw_path.stat().st_size / 1e6:.1f} MB)")
    print(f"  ✓ {noon_path.name}  ({noon_path.stat().st_size / 1e6:.1f} MB)")
    if use_aca_reef and noon_aca_path.exists():
        print(f"  ✓ {noon_aca_path.name}  ({noon_aca_path.stat().st_size / 1e6:.1f} MB)")
        print(f"  ✓ {aca_mask_path.name}  ({aca_mask_path.stat().st_size / 1e6:.1f} MB)")
    print(f"  ✓ {meta_path.name}")
    print(f"  done in {elapsed:.0f}s")
    return noon_aca_path if use_aca_reef and noon_aca_path.exists() else noon_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(
        description="RDL Mapbox + GEBCO compositor — M0+M1 layer pipeline"
    )
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--region", choices=sorted(REGIONS), help="Generate tile for one region")
    grp.add_argument("--all",  action="store_true", help="Generate tiles for all regions")
    grp.add_argument("--list", action="store_true", help="List regions and exit")
    p.add_argument("--zoom", type=int, default=None,
                   help=f"Override zoom for all regions (default: per-region, usually {DEFAULT_ZOOM})")
    p.add_argument("--zoom-bias", type=int, default=None,
                   help="Add a uniform zoom delta on top of the resolved per-region zoom (for example: +1 for a full high-resource fidelity pass)")
    p.add_argument("--max-dim", type=int, default=None,
                   help=f"Override output longer axis in pixels (default: {MAX_DIM}; try {HIRES_MAX_DIM} for near/LOW audit assets)")
    p.add_argument("--resource-stack", action="store_true",
                   help=f"Systematic high-resource preset: defaults to {DEFAULT_RESOURCE_STACK_LEVEL} ({RESOURCE_STACK_LEVELS[DEFAULT_RESOURCE_STACK_LEVEL]} px) and zoom-bias=+1 unless explicitly overridden")
    p.add_argument("--resource-stack-level", choices=sorted(RESOURCE_STACK_LEVELS), default=None,
                   help="Named high-resource tier for systematic batch generation: 8k / 12k / 16k")
    p.add_argument("--no-gebco", action="store_true", help="Skip M1 GEBCO depth layer")
    p.add_argument("--aca-reef", action="store_true",
                   help="Add M2 Allen Coral Atlas reef extent output as tile_noon_air_mapbox_aca_reef.jpg")
    p.add_argument("--m3m4", action="store_true",
                   help="Add M3/M4 climate+land candidate output as tile_noon_air_mapbox_m3m4.jpg")
    p.add_argument("--dem-slope", action="store_true",
                   help="Add Batch 2 Copernicus DEM slope candidate output as tile_noon_air_mapbox_dem.jpg or tile_noon_air_mapbox_m3m4_dem.jpg")
    p.add_argument("--landforms", action="store_true",
                   help="Add Batch 3 SRTM landforms candidate output as tile_noon_air_mapbox_landforms*.jpg")
    p.add_argument("--dry-run",  action="store_true")
    return p.parse_args()


def main():
    args = _parse_args()
    resource_stack_level = args.resource_stack_level
    if resource_stack_level is None and args.resource_stack:
        resource_stack_level = DEFAULT_RESOURCE_STACK_LEVEL

    if args.max_dim is not None:
        max_dim = args.max_dim
    elif resource_stack_level is not None:
        max_dim = RESOURCE_STACK_LEVELS[resource_stack_level]
    else:
        max_dim = MAX_DIM

    zoom_bias = args.zoom_bias if args.zoom_bias is not None else (1 if (args.resource_stack or resource_stack_level is not None) else 0)

    if args.list:
        print(f"\n{'Region':<25} {'Label':<18} {'Bounds'}")
        print("─" * 70)
        for rid, cfg in REGIONS.items():
            b = cfg["bounds"]
            print(f"  {rid:<23} {cfg['label']:<18} lon[{b[0]},{b[1]}] lat[{b[2]},{b[3]}]")
        return

    regions = list(REGIONS) if args.all else [args.region]
    t_total = time.time()

    for rid in regions:
        generate_region(
            rid,
            zoom=args.zoom,
            zoom_bias=zoom_bias,
            max_dim=max_dim,
            use_gebco=not args.no_gebco,
            use_aca_reef=args.aca_reef,
            use_m3m4=args.m3m4,
            use_dem_slope=args.dem_slope,
            use_landforms=args.landforms,
            dry_run=args.dry_run,
        )

    if len(regions) > 1:
        print(f"\n{'═'*60}")
        print(f"  All done: {len(regions)} region(s) in {time.time()-t_total:.0f}s")


if __name__ == "__main__":
    main()
