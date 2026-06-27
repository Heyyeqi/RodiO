"""Noon Air Earth colorization — thin orchestration layer for BMNG tiles.

Pipeline (this module's role is orchestration only):
    GeoFieldEngine → SpectralEarthEngine → NoonAirColorizer → VisualUnificationEngine

Physics is delegated to SpectralEarthEngine (Beer-Lambert ocean, BRDF ice,
Rayleigh/Mie atmosphere, ferric desert albedo). This module handles:
  - field computation dispatch
  - blend weight calculation
  - aesthetic touches (reef highlight, land de-saturation)
  - final clip/round

All transforms are absolute RGB/lon-lat rules so adjacent tiles remain stable.
No binary masks, no random state, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import numpy as np

from .geo_field_engine import GeoFieldEngine, OceanField
from .spectral_earth_engine import SpectralEarthEngine
from .visual_unification_engine import VisualUnificationEngine


RGBColor = Tuple[int, int, int]


def _rgb(hex_color: str) -> np.ndarray:
    value = hex_color.lstrip("#")
    return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


@dataclass(frozen=True)
class NoonAirConfig:
    deep_ocean: np.ndarray = field(default_factory=lambda: _rgb("#052C4A"))
    mid_ocean: np.ndarray = field(default_factory=lambda: _rgb("#0B5C7A"))
    shallow_ocean: np.ndarray = field(default_factory=lambda: _rgb("#2EC4C6"))
    reef_highlight: np.ndarray = field(default_factory=lambda: _rgb("#5FD3D8"))
    desert_sand: np.ndarray = field(default_factory=lambda: _rgb("#C2A077"))
    ice_blue_white: np.ndarray = field(default_factory=lambda: _rgb("#DCEFFF"))
    vegetation_olive: np.ndarray = field(default_factory=lambda: _rgb("#6E8F63"))


class NoonAirColorizer:
    """Transform raw satellite RGB tiles toward the Noon Air Earth aesthetic.

    Uses continuous geo fields from GeoFieldEngine instead of binary masks.
    process_tile() is the sole public entry point; shape and dtype are preserved.
    """

    def __init__(self) -> None:
        self.config = self._load_config()
        self.geo_engine = GeoFieldEngine()
        self.spectral_engine = SpectralEarthEngine()
        self.unification_engine = VisualUnificationEngine()

    def _load_config(self) -> NoonAirConfig:
        return NoonAirConfig()

    def process_tile(self, img: np.ndarray, metadata: Dict[str, Any] | None = None) -> np.ndarray:
        """Return a colorized RGB uint8 tile with unchanged shape.

        Pipeline:
          1. Compute continuous geo fields from original pixel data.
          2. Ocean — Beer-Lambert spectral response blended by ocean_factor.
          3. Reef highlight — aesthetic Noon Air touch on shallow cyan pixels.
          4. Land — de-saturation and olive-greening weighted by land probability.
          5. Desert — ferric oxide albedo via SpectralEarthEngine.
          6. Ice — Lambertian/BRDF reflectance blended by ice_factor.
          7. Atmosphere — Rayleigh/Mie scattering via SpectralEarthEngine.
          8. Unification — perceptual tone curves + tile edge feathering.
        """
        metadata = metadata or {}
        arr = self._as_rgb_float(img)

        # All fields computed from ORIGINAL pixels (before any colorization).
        ocean_f = self.geo_engine.ocean_field_from_pixels(img, metadata)
        ice_f = self.geo_engine.ice_field_from_pixels(img, metadata)
        atmo_f = self.geo_engine.atmosphere_field_from_pixels(img, metadata)

        # Step 2: Beer-Lambert ocean spectral response
        ocean_spectral = self.spectral_engine.ocean_spectral_response(
            ocean_f.depth_proxy, ocean_f.ocean_factor
        )
        blend = ocean_f.ocean_factor[..., None] * 0.48
        arr = arr * (1.0 - blend) + ocean_spectral * blend

        # Step 3: Reef highlight (aesthetic, uses original pixel colors)
        arr = self._apply_reef_highlight(arr, img, ocean_f)

        # Step 4: Land de-saturation (aesthetic, not physical)
        land_factor = 1.0 - ocean_f.ocean_factor
        arr = self._apply_land_weighted(arr, land_factor)

        # Step 5: Desert ferric albedo
        desert_f = self._desert_factor(img, metadata)
        arr = self.spectral_engine.desert_albedo(arr, desert_f * land_factor)

        # Step 6: Ice BRDF reflectance
        ice_spectral = self.spectral_engine.ice_reflectance(ice_f, sun_angle=45.0)
        factor = ice_f.ice_factor[..., None]
        arr = arr * (1.0 - factor) + ice_spectral * factor

        # Step 7: Rayleigh/Mie atmospheric scattering
        arr = self.spectral_engine.atmospheric_scattering(arr, atmo_f)

        # Step 8: Perceptual tone normalization
        result = np.clip(np.rint(arr), 0, 255).astype(np.uint8)
        return self.unification_engine.unify(result, metadata)

    # ── Reef highlight (Step 3) ───────────────────────────────────────────────

    def _apply_reef_highlight(
        self, arr: np.ndarray, original_img: np.ndarray, ocean_f: OceanField
    ) -> np.ndarray:
        """Aesthetic Noon Air reef highlight on very shallow, cyan-dominant pixels.

        Detects reef conditions from the ORIGINAL pixel colors (not post-spectral),
        then blends a teal reef highlight into the current pipeline state.
        """
        depth = ocean_f.depth_proxy
        orig = original_img.astype(np.float32)
        total = orig[..., 0] + orig[..., 1] + orig[..., 2] + 1.0
        cyan_frac = (orig[..., 1] + orig[..., 2]) / total
        reef_f = (
            np.clip((depth - 0.72) / 0.28, 0.0, 1.0)
            * np.clip((cyan_frac - 0.65) / 0.20, 0.0, 1.0)
            * ocean_f.ocean_factor
        )[..., None]
        return arr * (1.0 - reef_f * 0.20) + self.config.reef_highlight * (reef_f * 0.20)

    # ── Land (Step 3) ────────────────────────────────────────────────────────

    def _apply_land_weighted(self, img: np.ndarray, land_factor: np.ndarray) -> np.ndarray:
        """Desaturation and olive-greening weighted by land probability."""
        luma = self._luma(img)[..., None] * 255.0
        gray = np.repeat(luma, 3, axis=2)
        desat = img * 0.82 + gray * 0.18

        r, g, b = img[..., 0], img[..., 1], img[..., 2]
        green_excess = np.clip((g - np.maximum(r, b)) / 75.0, 0.0, 1.0)
        olive = (
            desat * (1.0 - green_excess[..., None] * 0.18)
            + self.config.vegetation_olive * (green_excess[..., None] * 0.18)
        )

        w = land_factor[..., None] * 0.40
        return img * (1.0 - w) + olive * w

    # ── Desert (Step 4) ──────────────────────────────────────────────────────

    def _desert_factor(self, img: np.ndarray, metadata: Dict[str, Any]) -> np.ndarray:
        """Return per-pixel desert probability [0, 1] from pixel + latitude."""
        f = img.astype(np.float32)
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        brightness = self._luma(f)
        saturation = self._saturation(img)
        vegetation_proxy = (g - r) / 255.0

        warm_soil = (
            (r >= g * 0.94) & (g >= b * 1.08)
            & (brightness > 0.32) & (brightness < 0.86)
        )
        low_vegetation = vegetation_proxy < 0.06
        lat_weight = self._latitude_weight(img.shape[:2], metadata, 10.0, 38.0)
        dry_latitude = lat_weight > 0.05

        desert_mask = warm_soil & low_vegetation & (dry_latitude | (saturation < 0.38))
        return desert_mask.astype(np.float32)

    def _apply_desert_weighted(self, img: np.ndarray, weight: np.ndarray) -> np.ndarray:
        """Sand coloring blended by combined desert × land weight."""
        luma = self._luma(img)
        centered = (img - luma[..., None] * 255.0) * 0.86 + luma[..., None] * 255.0
        target = self.config.desert_sand * (0.72 + luma[..., None] * 0.46)
        target = np.clip(target, 0, 226)
        blend = 0.30
        desert_result = centered * (1.0 - blend) + target * blend

        w = weight[..., None]
        return img * (1.0 - w) + desert_result * w

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _as_rgb_float(img: np.ndarray) -> np.ndarray:
        arr = np.asarray(img)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f"expected RGB image shape (H, W, 3), got {arr.shape}")
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        return arr.astype(np.float32)

    @staticmethod
    def _luma(img: np.ndarray) -> np.ndarray:
        return (0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]) / 255.0

    @staticmethod
    def _saturation(img: np.ndarray) -> np.ndarray:
        maxc = np.max(img, axis=2)
        minc = np.min(img, axis=2)
        return (maxc - minc) / np.maximum(maxc, 1.0)

    @staticmethod
    def _latitude_weight(
        shape: Tuple[int, int],
        metadata: Dict[str, Any],
        min_abs_lat: float,
        max_abs_lat: float,
    ) -> np.ndarray:
        height, width = shape
        bounds = metadata.get("bounds") or metadata.get("bbox")
        if bounds and len(bounds) == 4:
            _, lat_min, _, lat_max = [float(v) for v in bounds]
        else:
            lat_min, lat_max = -90.0, 90.0
        if height <= 1:
            latitudes = np.array([(lat_min + lat_max) / 2.0], dtype=np.float32)
        else:
            latitudes = np.linspace(lat_max, lat_min, height, dtype=np.float32)
        abs_lat = np.abs(latitudes)
        weight = np.clip(
            (abs_lat - min_abs_lat) / max(max_abs_lat - min_abs_lat, 1e-6), 0.0, 1.0
        )
        return np.repeat(weight[:, None], width, axis=1)
