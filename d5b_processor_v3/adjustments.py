# adjustments.py
import numpy as np

def apply_rgb_offset(img, mask, r_off, g_off, b_off):
    result = img.astype(np.int16)
    m = mask[:,:,np.newaxis]
    delta = np.array([r_off, g_off, b_off], dtype=np.int16)
    return np.clip(result + (delta * m).astype(np.int16), 0, 255).astype(np.uint8)

def apply_saturation(img, mask, factor):
    if abs(factor - 1.0) < 0.001:
        return img
    f = img.astype(np.float32)
    gray = f.mean(axis=2, keepdims=True)
    adj = np.clip(gray + (f - gray) * factor, 0, 255)
    m = mask[:,:,np.newaxis]
    return np.clip(f * (1 - m) + adj * m, 0, 255).astype(np.uint8)

def apply_brightness(img, mask, factor):
    if abs(factor - 1.0) < 0.001:
        return img
    f = img.astype(np.float32)
    adj = np.clip(f * factor, 0, 255)
    m = mask[:,:,np.newaxis]
    return np.clip(f * (1 - m) + adj * m, 0, 255).astype(np.uint8)

def apply_region(img, region_mask, cfg):
    img = apply_rgb_offset(img, region_mask, cfg["r_offset"], cfg["g_offset"], cfg["b_offset"])
    img = apply_saturation(img, region_mask, cfg.get("saturation_factor", 1.0))
    img = apply_brightness(img, region_mask, cfg.get("brightness_factor", 1.0))
    return img

def apply_island_halo(img, halo_mask, cfg):
    eff = halo_mask * cfg.get("strength", 0.15)
    return apply_rgb_offset(img, eff, cfg["r_offset"], cfg["g_offset"], cfg["b_offset"])
