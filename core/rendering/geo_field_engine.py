"""Geo Field Engine — continuous geophysical fields for Earth colorization.

Replaces discrete ocean/land/ice/desert masks with continuous field values
derived from pixel data and latitude. All operations are deterministic.

Pipeline position:
    Raw BMNG tile → GeoFieldEngine → NoonAirColorizer → final tile
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np


# ── Field result types ────────────────────────────────────────────────────────


@dataclass
class OceanField:
    """Continuous ocean depth and coverage field for a tile."""
    depth_proxy: np.ndarray     # (H, W) float32 in [0, 1]: 0 = deepest, 1 = shallowest
    ocean_factor: np.ndarray    # (H, W) float32 in [0, 1]: continuous ocean probability


@dataclass
class IceField:
    """Continuous ice coverage and spectral properties for a tile."""
    ice_factor: np.ndarray           # (H, W) float32 in [0, 1]: ice coverage
    brightness_gradient: np.ndarray  # (H, W) float32: spatially varying brightness
    blue_shift: np.ndarray           # (H, W) float32 in [0, 0.06]: spectral shift amount


@dataclass
class AtmosphereField:
    """Atmospheric coupling field: limb, horizon, and ocean-sky effects."""
    limb_glow: np.ndarray            # (H, W) float32: edge brightening factor
    horizon_blend: np.ndarray        # (H, W) float32: sky-horizon blend weight
    ocean_sky_continuity: np.ndarray # (H, W) float32: sky reflection on ocean


# ── Engine ────────────────────────────────────────────────────────────────────


class GeoFieldEngine:
    """Continuous geophysical field engine for tile-based Earth colorization.

    Two APIs:
    - Scalar (lon/lat): for per-point rendering pipelines
    - Array (image): for tile batch processing in NoonAirColorizer
    """

    # ── Scalar API ────────────────────────────────────────────────────────────

    def compute_depth_field(self, lon: float, lat: float) -> float:
        """Continuous depth proxy in metres (negative = below sea level).

        Analytical approximation of GEBCO/ETOPO distribution:
        deepest in mid-ocean away from poles; shallower on polar shelves.
        """
        abs_lat = abs(lat)
        deep_factor = math.cos(math.radians(abs_lat * 0.8)) * 0.90 + 0.10
        noise = math.sin(math.radians(lon * 3.7 + lat * 2.1)) * 0.08
        depth_m = -5500.0 * deep_factor * (0.92 + noise)
        if abs_lat > 72.0:
            shelf_blend = min(1.0, (abs_lat - 72.0) / 18.0)
            depth_m = depth_m * (1.0 - shelf_blend) + (-320.0) * shelf_blend
        return depth_m

    def compute_slope_field(self, lon: float, lat: float) -> float:
        """Terrain slope proxy [0.0, 1.0] from known ridge/continental patterns."""
        ridge = math.sin(math.radians(lon * 1.5 + 90.0)) ** 2 * 0.6
        return abs(ridge * math.cos(math.radians(lat)))

    def compute_humidity_proxy(self, lat: float, lon: float) -> float:
        """Köppen-based continuous humidity/moisture proxy [0.0, 1.0].

        Tropical < 15° = very moist; subtropical 15–30° = arid;
        temperate 30–55° = moderate; polar > 55° = cold-arid.
        """
        abs_lat = abs(lat)
        if abs_lat < 15.0:
            base = 0.90 - abs_lat / 15.0 * 0.15
        elif abs_lat < 30.0:
            base = 0.75 - (abs_lat - 15.0) / 15.0 * 0.55
        elif abs_lat < 55.0:
            base = 0.20 + (abs_lat - 30.0) / 25.0 * 0.45
        else:
            base = 0.65 - (abs_lat - 55.0) / 35.0 * 0.45
        lon_wave = math.sin(math.radians(lon * 0.8 + 20.0)) * 0.08
        return max(0.0, min(1.0, base + lon_wave))

    # ── Array API ─────────────────────────────────────────────────────────────

    def ocean_field_from_pixels(
        self, img: np.ndarray, metadata: Dict[str, Any]
    ) -> OceanField:
        """Derive continuous ocean depth and coverage from pixel RGB.

        ocean_factor uses a sigmoid of blue-channel dominance — no hard threshold.
        depth_proxy maps brightness to depth: bright = shallow, dark = deep.
        """
        f = img.astype(np.float32) / 255.0
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b

        # Continuous ocean factor: sigmoid of (blue − 0.6*(red+green))
        blue_dominance = b - (r + g) * 0.6
        ocean_factor = 1.0 / (1.0 + np.exp(-12.0 * (blue_dominance - 0.08)))

        # Attenuate bright ice/snow so it isn't misclassified as ocean
        not_ice = np.clip(1.0 - (brightness - 0.82) / 0.16, 0.0, 1.0)
        ocean_factor = (ocean_factor * not_ice).astype(np.float32)

        # Depth proxy: 0 = deepest (dark navy), 1 = shallowest (bright cyan)
        depth_proxy = np.clip(
            (brightness - 0.05) / 0.65, 0.0, 1.0
        ).astype(np.float32)

        return OceanField(depth_proxy=depth_proxy, ocean_factor=ocean_factor)

    def ice_field_from_pixels(
        self, img: np.ndarray, metadata: Dict[str, Any]
    ) -> IceField:
        """Derive continuous ice field with brightness gradient and spectral shift.

        ice_factor combines pixel brightness/saturation with latitude enhancement.
        brightness_gradient applies a deterministic fracture-like spatial pattern.
        blue_shift drives the spectral tilt toward blue-white for icy pixels.
        """
        f = img.astype(np.float32) / 255.0
        brightness = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
        maxc = img.max(axis=2).astype(np.float32)
        minc = img.min(axis=2).astype(np.float32)
        saturation = (maxc - minc) / np.maximum(maxc, 1.0)

        # Ice probability: high brightness × low saturation
        high_bright = np.clip((brightness - 0.60) / 0.30, 0.0, 1.0)
        low_sat = np.clip(1.0 - saturation / 0.25, 0.0, 1.0)
        ice_base = high_bright * low_sat

        # Polar latitude boosts ice factor beyond what pixel data alone shows
        lat_field = self._latitude_field(img.shape[:2], metadata, 60.0, 90.0)
        ice_factor = np.clip(ice_base + lat_field * 0.40, 0.0, 1.0).astype(np.float32)

        # Deterministic fracture-like brightness gradient (two crossing sinusoids)
        H, W = img.shape[:2]
        y = np.arange(H, dtype=np.float32)[:, None] / max(H - 1, 1)
        x = np.arange(W, dtype=np.float32)[None, :] / max(W - 1, 1)
        fracture = (
            0.50 + 0.25 * np.sin(y * 47.3 + x * 31.7)
                 + 0.25 * np.sin(y * 13.1 - x * 19.3)
        )
        brightness_gradient = (brightness * (0.92 + 0.08 * fracture)).astype(np.float32)

        # Spectral shift: max 0.06 toward blue-white, proportional to ice coverage
        blue_shift = (ice_factor * 0.06).astype(np.float32)

        return IceField(
            ice_factor=ice_factor,
            brightness_gradient=brightness_gradient,
            blue_shift=blue_shift,
        )

    def atmosphere_field_from_pixels(
        self, img: np.ndarray, metadata: Dict[str, Any]
    ) -> AtmosphereField:
        """Derive atmospheric coupling field for limb glow, horizon, ocean-sky.

        All effects are intentionally small (≤ 2.5%) to not shift global hue.
        """
        metadata = metadata or {}
        f = img.astype(np.float32) / 255.0
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b

        H, W = img.shape[:2]
        y_edge = np.abs(
            np.linspace(-1.0, 1.0, H, dtype=np.float32)[:, None]
            * np.ones((1, W), dtype=np.float32)
        )

        # Polar factor: amplifies limb glow at high latitudes
        bounds = metadata.get("bounds") or metadata.get("bbox")
        if bounds and len(bounds) == 4:
            lat_center = (float(bounds[1]) + float(bounds[3])) / 2.0
        else:
            lat_center = 0.0
        polar_factor = min(1.0, abs(lat_center) / 80.0)

        # Limb glow: 2.5% equatorial, up to 6.5% polar, fades toward tile center
        limb_glow = (y_edge * (0.025 + 0.040 * polar_factor)).astype(np.float32)

        # Horizon blend: subtle sky-tint for the darkest pixels (2% max)
        horizon_blend = np.clip(
            0.020 * (1.0 - brightness), 0.0, 0.020
        ).astype(np.float32)

        # Ocean-sky continuity: azure reflection on ocean-like surfaces (1.5% max)
        blue_dom = b - (r + g) * 0.6
        ocean_proxy = np.clip(blue_dom / 0.20, 0.0, 1.0)
        ocean_sky = (
            ocean_proxy * np.clip(brightness, 0.0, 1.0) * 0.015
        ).astype(np.float32)

        return AtmosphereField(
            limb_glow=limb_glow,
            horizon_blend=horizon_blend,
            ocean_sky_continuity=ocean_sky,
        )

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _latitude_field(
        shape: Tuple[int, int],
        metadata: Dict[str, Any],
        min_abs_lat: float,
        max_abs_lat: float,
    ) -> np.ndarray:
        H, W = shape
        metadata = metadata or {}
        bounds = metadata.get("bounds") or metadata.get("bbox")
        if bounds and len(bounds) == 4:
            _, lat_min, _, lat_max = [float(v) for v in bounds]
        else:
            lat_min, lat_max = -90.0, 90.0
        lats = np.linspace(lat_max, lat_min, max(H, 1), dtype=np.float32)
        w = np.clip(
            (np.abs(lats) - min_abs_lat) / max(max_abs_lat - min_abs_lat, 1e-6),
            0.0, 1.0,
        )
        return np.repeat(w[:, None], W, axis=1)
