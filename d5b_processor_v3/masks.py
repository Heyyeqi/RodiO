# masks.py
import numpy as np
from scipy.ndimage import gaussian_filter

def make_region_mask(bounds, width, height, cross_antimeridian=False, feather_px=20):
    lon_min, lon_max, lat_min, lat_max = bounds
    mask = np.zeros((height, width), dtype=np.float32)
    y_top = max(0, int((90.0 - lat_max) / 180.0 * height))
    y_bot = min(height, int((90.0 - lat_min) / 180.0 * height))

    if cross_antimeridian or lon_min > lon_max:
        x_r = int((lon_min + 180.0) / 360.0 * width)
        x_l = int((lon_max + 180.0) / 360.0 * width)
        mask[y_top:y_bot, x_r:] = 1.0
        mask[y_top:y_bot, :x_l] = 1.0
    else:
        x_l = max(0, int((lon_min + 180.0) / 360.0 * width))
        x_r = min(width, int((lon_max + 180.0) / 360.0 * width))
        mask[y_top:y_bot, x_l:x_r] = 1.0

    if feather_px > 0:
        mask = gaussian_filter(mask, sigma=feather_px)
        if mask.max() > 0:
            mask /= mask.max()
    return mask

def make_ocean_mask_v2(img):
    """改良 ocean mask：4条件复合，减少沙漠/冰雪/陆地误判"""
    r = img[:,:,0].astype(np.int16)
    g = img[:,:,1].astype(np.int16)
    b = img[:,:,2].astype(np.int16)
    return (b > r + 15) & (b > 60) & (g > r - 5) & (r < 160)

def make_conservative_water_mask(img):
    """保守水体：用于封闭海，防沙漠误伤"""
    r = img[:,:,0].astype(np.int16)
    g = img[:,:,1].astype(np.int16)
    b = img[:,:,2].astype(np.int16)
    return (b > r + 20) & (b > g - 5) & (r < 130)

def make_deep_ocean_mask(img):
    """深海像素：暗蓝灰"""
    r = img[:,:,0].astype(np.int16)
    g = img[:,:,1].astype(np.int16)
    b = img[:,:,2].astype(np.int16)
    return (r < 80) & (g < 110) & (b < 150) & (b > r + 15)

def make_land_mask_v2(img):
    return ~make_ocean_mask_v2(img)

def make_island_halo_mask(center_lon, center_lat, radius_km, width, height, blur_px=40):
    radius_deg_lat = radius_km / 111.0
    cos_lat = max(0.05, abs(np.cos(np.radians(center_lat))))
    radius_deg_lon = radius_km / (111.0 * cos_lat)

    cx = int((center_lon + 180.0) / 360.0 * width) % width
    cy = max(0, min(height - 1, int((90.0 - center_lat) / 180.0 * height)))
    rx = max(1, int(radius_deg_lon / 360.0 * width))
    ry = max(1, int(radius_deg_lat / 180.0 * height))

    yy, xx = np.ogrid[:height, :width]
    dx = np.minimum(np.abs(xx - cx), width - np.abs(xx - cx)).astype(np.float32)
    dy = (yy - cy).astype(np.float32)
    dist = np.sqrt((dx / rx)**2 + (dy / ry)**2)
    mask = np.clip(1.0 - dist, 0.0, 1.0)

    if blur_px > 0:
        mask = gaussian_filter(mask, sigma=blur_px / 2.5)
        if mask.max() > 0:
            mask /= mask.max()
    return mask

def make_deep_gate_for_halo(img, halo_mask):
    """
    v3 强化版深海门控：
    very_deep（最暗蓝）→ 0
    deep（深蓝） → 3%
    shallow_like（浅色/浅海）→ 100%
    """
    r = img[:,:,0].astype(np.int16)
    g = img[:,:,1].astype(np.int16)
    b = img[:,:,2].astype(np.int16)

    very_deep    = (r < 55) & (g < 85)  & (b < 125) & (b > r + 18)
    deep         = (r < 75) & (g < 105) & (b < 150) & (b > r + 18)
    shallow_like = (r > 70) | (g > 105) | ((g > 90) & ((b - r) < 45))

    gate = np.ones_like(halo_mask, dtype=np.float32)
    gate[deep]         = 0.03
    gate[very_deep]    = 0.0
    gate[shallow_like] = 1.0
    return halo_mask * gate
