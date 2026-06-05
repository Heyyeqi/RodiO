# enhancement.py
import numpy as np
from PIL import Image, ImageFilter
from masks import make_land_mask_v2, make_ocean_mask_v2
from config import ENHANCEMENT

def enhance_land(img):
    if not ENHANCEMENT.get("enable_land_enhancement", False):
        return img
    from adjustments import apply_saturation, apply_brightness
    land = make_land_mask_v2(img).astype(np.float32)
    img = apply_saturation(img, land, ENHANCEMENT["land_saturation_factor"])
    return apply_brightness(img, land, ENHANCEMENT["land_contrast_factor"])

def compress_polar_highlights(img):
    """只压缩南纬75°以南（南极大陆）"""
    if not ENHANCEMENT.get("enable_polar_compress", True):
        return img
    height, width = img.shape[:2]
    lat_thresh = ENHANCEMENT.get("polar_lat_threshold", -75.0)

    y_start = int((90.0 - lat_thresh) / 180.0 * height)
    y_start = max(0, min(height, y_start))

    print(f"  [polar] y_start={y_start} / height={height}, "
          f"对应纬度: {90 - y_start/height*180:.1f}° 到 -90°")
    assert y_start > height * 0.7, \
        f"极地 y_start={y_start} 异常（应 > {height*0.7:.0f}），请检查 lat_threshold 配置"

    threshold = ENHANCEMENT["polar_highlight_threshold"]
    compress  = ENHANCEMENT["polar_highlight_compress"]

    result = img.astype(np.float32)
    row_slice = result[y_start:, :, :]
    # Bug fix: only compress channels that actually exceed threshold;
    # original code set ALL channels of bright pixels to threshold, lifting low channels.
    over = np.maximum(row_slice - threshold, 0)   # how much each channel exceeds threshold
    compressed = row_slice - over * (1.0 - compress)  # reduce overshoot; channels at/below threshold unchanged
    bright3 = (row_slice.max(axis=2) > threshold)[:, :, np.newaxis]
    row_slice[:] = np.where(bright3, compressed, row_slice)
    result[y_start:] = row_slice
    return np.clip(result, 0, 255).astype(np.uint8)

def sharpen_land_only(img, img_pil):
    if not ENHANCEMENT.get("enable_sharpen", True):
        return img, img_pil
    amount = ENHANCEMENT["sharpen_amount"]
    radius = ENHANCEMENT["sharpen_radius"]
    land_mask = make_land_mask_v2(img).astype(np.float32)
    blurred = img_pil.filter(ImageFilter.GaussianBlur(radius=radius))
    orig = img.astype(np.float32)
    blur = np.array(blurred).astype(np.float32)
    sharp = np.clip(orig + amount * (orig - blur), 0, 255)
    m = land_mask[:,:,np.newaxis]
    result = np.clip(orig * (1 - m) + sharp * m, 0, 255).astype(np.uint8)
    return result, Image.fromarray(result)

def full_enhance(img, img_pil):
    print("  [enhance] 陆地增强...")
    img = enhance_land(img)
    print("  [enhance] 南极高光压缩...")
    img = compress_polar_highlights(img)
    print("  [enhance] 陆地锐化...")
    img_pil = Image.fromarray(img)
    img, img_pil = sharpen_land_only(img, img_pil)
    return img, img_pil
