"""Visual expression grammar for D6 Earth rendering.

This module is a pure visual layer. It interprets already-computed Earth data
as colour language, without changing geometry, sampling, SAL, M1, VC, or raster
indexing semantics.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .renderer_types import RGB


class TimeGrammar:
    """Time-of-day colour grammar driven by a simple sun-angle proxy."""

    def __init__(self):
        self.sun_angle = 0.0

    def angle_from_hour(self, hour: float) -> float:
        """Map local hour to a deterministic sun angle proxy in degrees."""
        return math.sin(((float(hour) - 6.0) / 12.0) * math.pi) * 90.0

    def time_shift(self, color, sun_angle: Optional[float] = None) -> RGB:
        """Apply white-balance shift: noon neutral, sunset warm, night cool/desaturated."""
        angle = self.sun_angle if sun_angle is None else float(sun_angle)
        rgb = _as_rgb(color)

        if angle >= 55.0:
            return rgb.clamp()
        if angle >= 0.0:
            sunset = 1.0 - (angle / 55.0)
            shifted = rgb.shift_warmth(0.45 * sunset).saturate(1.0 + 0.08 * sunset)
            return shifted.clamp()

        night = min(1.0, abs(angle) / 45.0)
        cooled = rgb.saturate(1.0 - 0.45 * night)
        cooled = RGB(
            cooled.r * (1.0 - 0.18 * night),
            cooled.g * (1.0 - 0.12 * night),
            cooled.b * (1.0 + 0.16 * night) + 0.035 * night,
        )
        return cooled.clamp()


class VisualGrammar:
    """Earth visual grammar: climate, elevation, bathymetry, and time."""

    def __init__(self):
        self.climate_palette = {
            "tropical": RGB(0.10, 0.55, 0.24),
            "arid": RGB(0.72, 0.58, 0.30),
            "temperate": RGB(0.24, 0.48, 0.38),
            "cold": RGB(0.46, 0.55, 0.52),
            "polar": RGB(0.82, 0.90, 0.96),
            "unknown": RGB(0.45, 0.48, 0.45),
        }
        self.elevation_curve = {
            "sea_level": 0.0,
            "mid_altitude": 1500.0,
            "high_altitude": 4500.0,
        }
        self.ocean_depth_curve = {
            "shallow": RGB(0.32, 0.78, 0.86),
            "mid": RGB(0.05, 0.27, 0.64),
            "deep": RGB(0.01, 0.04, 0.18),
        }
        self.time_curve = {"noon": 90.0, "sunset": 0.0, "night": -45.0}
        self.time_grammar = TimeGrammar()

    def climate_color(self, climate_class, base_color) -> RGB:
        """Map a Koppen class to a visual palette while preserving base detail."""
        rgb = _as_rgb(base_color)
        family = self.climate_family(climate_class)
        target = self.climate_palette[family]
        blend = {
            "tropical": 0.34,
            "arid": 0.38,
            "temperate": 0.26,
            "cold": 0.28,
            "polar": 0.45,
            "unknown": 0.12,
        }[family]
        mapped = rgb.lerp(target, blend)
        if family == "tropical":
            mapped = mapped.saturate(1.12)
        elif family == "arid":
            mapped = mapped.saturate(0.82).shift_warmth(0.10)
        elif family == "polar":
            mapped = mapped.saturate(0.70).shift_warmth(-0.18)
        return mapped.clamp()

    def climate_family(self, climate_class) -> str:
        """Return a broad climate family for numeric or textual Koppen labels."""
        if climate_class is None:
            return "unknown"
        if isinstance(climate_class, str):
            value = climate_class.strip().lower()
            if value in self.climate_palette:
                return value
            if value.startswith("a"):
                return "tropical"
            if value.startswith("b"):
                return "arid"
            if value.startswith("c"):
                return "temperate"
            if value.startswith("d"):
                return "cold"
            if value.startswith("e"):
                return "polar"
            return "unknown"
        try:
            cls = int(climate_class)
        except (TypeError, ValueError):
            return "unknown"
        if 1 <= cls <= 3:
            return "tropical"
        if 4 <= cls <= 7:
            return "arid"
        if 8 <= cls <= 16:
            return "temperate"
        if 17 <= cls <= 28:
            return "cold"
        if 29 <= cls <= 30:
            return "polar"
        return "unknown"

    def elevation_tone(self, elevation: float) -> float:
        """Return monotonic highland factor in [0, 1] for elevation tone mapping."""
        elev = max(0.0, float(elevation))
        high = self.elevation_curve["high_altitude"]
        return max(0.0, min(1.0, elev / high))

    def apply_elevation_tone(self, color, elevation: float) -> RGB:
        """Low land is humid/darker; high land becomes colder and less saturated."""
        rgb = _as_rgb(color)
        elev = float(elevation)
        highland = self.elevation_tone(elev)
        if elev < 500.0:
            low = 1.0 - max(0.0, elev) / 500.0
            rgb = RGB(rgb.r * (1.0 - 0.06 * low), rgb.g * (1.0 - 0.03 * low), rgb.b * (1.0 - 0.04 * low))
        rgb = rgb.saturate(1.0 - 0.30 * highland).shift_warmth(-0.16 * highland)
        return rgb.clamp()

    def ocean_gradient(self, depth: float) -> RGB:
        """Return continuous ocean colour for bathymetry. Negative DEM is accepted."""
        d = abs(float(depth))
        shallow = self.ocean_depth_curve["shallow"]
        mid = self.ocean_depth_curve["mid"]
        deep = self.ocean_depth_curve["deep"]
        if d <= 1000.0:
            return shallow.lerp(mid, d / 1000.0).clamp()
        return mid.lerp(deep, min(1.0, (d - 1000.0) / 5000.0)).clamp()

    def time_shift(self, color, sun_angle: float) -> RGB:
        return self.time_grammar.time_shift(color, sun_angle)

    def apply_to_rgb(
        self,
        color,
        *,
        climate_class=None,
        elevation: float = 0.0,
        ocean: bool = False,
        sun_angle: float = 90.0,
    ) -> RGB:
        """Apply visual grammar to one RGB colour."""
        if ocean:
            rgb = _as_rgb(color).lerp(self.ocean_gradient(elevation), 0.42)
        else:
            rgb = self.climate_color(climate_class, color)
            rgb = self.apply_elevation_tone(rgb, elevation)
        return self.time_shift(rgb, sun_angle)

    def generate_rule_candidates(
        self,
        *,
        climate_class=None,
        elevation: float = 0.0,
        ocean: bool = False,
        sun_angle: float = 90.0,
    ) -> list:
        """Emit visual rule candidates without producing RGB.

        Returns a list of RuleCandidate objects for consumption by
        VisualRuleResolver.resolve_conflicts().  Existing apply_to_rgb() and
        apply_to_texture() are unchanged and remain the direct-output path.
        """
        # Import here to avoid circular dependency at module load time.
        from .visual_rule_resolver import RuleCandidate

        candidates: list[RuleCandidate] = []
        family = self.climate_family(climate_class)

        if ocean:
            depth = abs(float(elevation)) if elevation < 0 else 0.0
            candidates.append(RuleCandidate(
                rule_type="ocean",
                score=0.95 if depth >= 1000.0 else 0.88,
                payload={"depth": depth, "sun_angle": sun_angle},
            ))
        else:
            if family == "polar":
                candidates.append(RuleCandidate(
                    rule_type="polar", score=0.90,
                    payload={"elevation": elevation},
                ))
            elif family == "arid":
                candidates.append(RuleCandidate(
                    rule_type="desert", score=0.85,
                    payload={"elevation": elevation},
                ))
            else:
                candidates.append(RuleCandidate(
                    rule_type="biome",
                    score=0.60 if family == "tropical" else 0.50,
                    payload={"family": family},
                ))
            if elevation >= 3500.0:
                candidates.append(RuleCandidate(
                    rule_type="ice",
                    score=min(0.90, 0.70 + (elevation - 3500.0) / 15000.0),
                    payload={"elevation": elevation},
                ))

        atmo_t = max(0.0, min(1.0, float(sun_angle) / 90.0))
        candidates.append(RuleCandidate(
            rule_type="atmosphere",
            score=0.10 + 0.40 * atmo_t,
            payload={"sun_angle": sun_angle},
        ))

        return candidates

    def apply_to_texture(self, texture: np.ndarray, *, sun_angle: float = 90.0) -> np.ndarray:
        """Apply global time grammar to an RGB uint8 texture without semantic changes."""
        arr = np.asarray(texture)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError("texture must be an RGB array with shape (height, width, 3)")
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)

        if sun_angle >= 55.0:
            return arr.copy()

        f = arr.astype(np.float32) / 255.0
        lum = 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]
        if sun_angle >= 0.0:
            sunset = 1.0 - (float(sun_angle) / 55.0)
            f[:, :, 0] += 0.15 * 0.45 * sunset
            f[:, :, 1] += 0.02 * 0.45 * sunset
            f[:, :, 2] -= 0.18 * 0.45 * sunset
            sat = 1.0 + 0.08 * sunset
        else:
            night = min(1.0, abs(float(sun_angle)) / 45.0)
            sat = 1.0 - 0.45 * night
            f[:, :, 0] *= 1.0 - 0.18 * night
            f[:, :, 1] *= 1.0 - 0.12 * night
            f[:, :, 2] = f[:, :, 2] * (1.0 + 0.16 * night) + 0.035 * night
        f = lum[:, :, None] + (f - lum[:, :, None]) * sat
        return np.clip(np.rint(f * 255.0), 0, 255).astype(np.uint8)


def _as_rgb(color) -> RGB:
    if isinstance(color, RGB):
        return color
    if isinstance(color, np.ndarray):
        vals = color.astype(float).reshape(-1)
    else:
        vals = list(color)
    if len(vals) != 3:
        raise ValueError("RGB colour must have exactly 3 channels")
    scale = 255.0 if max(vals) > 1.0 else 1.0
    return RGB(float(vals[0]) / scale, float(vals[1]) / scale, float(vals[2]) / scale)
