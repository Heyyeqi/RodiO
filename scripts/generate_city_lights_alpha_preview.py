from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

try:
    import numpy as np
except ImportError:
    print("missing dependency: numpy", flush=True)
    print("install with: python -m pip install numpy Pillow", flush=True)
    sys.exit(1)

try:
    from PIL import Image, ImageFilter
except ImportError:
    print("missing dependency: Pillow", flush=True)
    print("install with: python -m pip install numpy Pillow", flush=True)
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "pwa" / "assets" / "earth_night_8k.jpg"
OUTPUT_PATH = ROOT / "pwa" / "assets" / "earth_city_lights_alpha_preview_v3.png"

EXPECTED_SIZE = (8192, 4096)

LOW_THRESHOLD = 0.24
HIGH_THRESHOLD = 0.76
ALPHA_GAMMA = 0.70
BLUR_RADIUS = 0.55
WARMTH_MASK_ENABLED = True
POLAR_SUPPRESSION_ENABLED = True
WARM_TINT = np.array([255.0, 231.0, 176.0], dtype=np.float32) / 255.0


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / max(1e-6, edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024.0
    return f"{num_bytes}B"


def main() -> None:
    print(f"input path: {INPUT_PATH}", flush=True)
    print(f"output path: {OUTPUT_PATH}", flush=True)
    print("starting image read...", flush=True)

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"input not found: {INPUT_PATH}")

    source = Image.open(INPUT_PATH).convert("RGB")
    print(f"input size: {source.size}", flush=True)
    print(f"mode: {source.mode}", flush=True)

    if source.size != EXPECTED_SIZE:
        raise ValueError(
            f"unexpected input size {source.size}, expected {EXPECTED_SIZE}"
        )

    print("starting processing...", flush=True)

    rgb = np.asarray(source, dtype=np.float32) / 255.0
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]

    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

    alpha = smoothstep(LOW_THRESHOLD, HIGH_THRESHOLD, luminance)
    alpha = np.power(alpha, ALPHA_GAMMA, dtype=np.float32)
    mid_lights = smoothstep(LOW_THRESHOLD * 0.85, HIGH_THRESHOLD * 0.90, luminance)
    alpha = np.clip(alpha + 0.12 * mid_lights * (1.0 - alpha), 0.0, 1.0)

    if WARMTH_MASK_ENABLED:
        warm_score = np.clip(r + 0.6 * g - 1.2 * b, -1.0, 1.0)
        warm_mask = smoothstep(-0.12, 0.08, warm_score)
        blue_penalty = np.clip((b - (0.85 * r + 0.95 * g)) / 0.35, 0.0, 1.0)
        alpha *= (0.45 + 0.55 * warm_mask)
        alpha *= (1.0 - 0.72 * blue_penalty)

    if POLAR_SUPPRESSION_ENABLED:
        height = rgb.shape[0]
        y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
        top_fade = 1.0 - 0.82 * (1.0 - smoothstep(0.00, 0.08, y))
        bottom_fade = 1.0 - 0.90 * smoothstep(0.88, 1.00, y)
        polar_mask = np.minimum(top_fade, bottom_fade)
        alpha *= polar_mask

    alpha_img = Image.fromarray(
        np.clip(alpha * 255.0, 0, 255).astype(np.uint8), mode="L"
    )
    if BLUR_RADIUS > 0:
        alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))

    alpha = np.asarray(alpha_img, dtype=np.float32) / 255.0

    light_strength = np.clip(
        smoothstep(LOW_THRESHOLD * 0.95, HIGH_THRESHOLD, luminance), 0.0, 1.0
    )
    neutral_strength = (0.18 + 0.22 * light_strength)[..., None]
    base_rgb = rgb * neutral_strength + WARM_TINT * (1.0 - neutral_strength)
    warm_mix = (0.70 + 0.22 * light_strength)[..., None]
    tinted_rgb = base_rgb * (1.0 - warm_mix) + WARM_TINT * warm_mix
    out_rgb = np.clip(tinted_rgb * 255.0, 0, 255).astype(np.uint8)
    out_alpha = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    out_rgba = np.dstack([out_rgb, out_alpha])

    result = Image.fromarray(out_rgba, mode="RGBA")

    before_size = OUTPUT_PATH.stat().st_size if OUTPUT_PATH.exists() else 0
    result.save(OUTPUT_PATH)
    after_size = OUTPUT_PATH.stat().st_size

    coverage = float((alpha > 0.01).mean() * 100.0)
    coverage_gt10 = float((out_alpha > 10).mean() * 100.0)
    coverage_gt50 = float((out_alpha > 50).mean() * 100.0)
    print(f"output size: {result.size}", flush=True)
    print(f"output file size: {format_size(after_size)}", flush=True)
    print(
        f"output file size before/after: {format_size(before_size)} -> {format_size(after_size)}",
        flush=True,
    )
    print(
        f"thresholds: low={LOW_THRESHOLD:.2f}, high={HIGH_THRESHOLD:.2f}, gamma={ALPHA_GAMMA:.2f}",
        flush=True,
    )
    print(f"blur radius: {BLUR_RADIUS:.2f}", flush=True)
    print(f"alpha coverage percentage: {coverage:.2f}%", flush=True)
    print(f"alpha > 10 coverage: {coverage_gt10:.2f}%", flush=True)
    print(f"alpha > 50 coverage: {coverage_gt50:.2f}%", flush=True)
    print(f"warmth mask enabled: {WARMTH_MASK_ENABLED}", flush=True)
    print(f"polar suppression enabled: {POLAR_SUPPRESSION_ENABLED}", flush=True)
    print(f"saved timestamp: {datetime.now().isoformat(timespec='seconds')}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
