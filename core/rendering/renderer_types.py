"""Shared data types for the D6 rendering pipeline."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class RGB:
    """Linear RGB in [0.0, 1.0]. Arithmetic ops return new RGB; values may exceed range."""

    r: float
    g: float
    b: float

    def clamp(self) -> "RGB":
        return RGB(max(0.0, min(1.0, self.r)), max(0.0, min(1.0, self.g)), max(0.0, min(1.0, self.b)))

    def to_uint8(self) -> Tuple[int, int, int]:
        c = self.clamp()
        return (int(c.r * 255), int(c.g * 255), int(c.b * 255))

    def __add__(self, other: "RGB") -> "RGB":
        return RGB(self.r + other.r, self.g + other.g, self.b + other.b)

    def __mul__(self, scalar: float) -> "RGB":
        return RGB(self.r * scalar, self.g * scalar, self.b * scalar)

    def __rmul__(self, scalar: float) -> "RGB":
        return self.__mul__(scalar)

    def lerp(self, other: "RGB", t: float) -> "RGB":
        t = max(0.0, min(1.0, t))
        return RGB(self.r + (other.r - self.r) * t, self.g + (other.g - self.g) * t, self.b + (other.b - self.b) * t)

    def luminance(self) -> float:
        return 0.2126 * self.r + 0.7152 * self.g + 0.0722 * self.b

    def saturate(self, factor: float) -> "RGB":
        lum = self.luminance()
        return RGB(lum + (self.r - lum) * factor, lum + (self.g - lum) * factor, lum + (self.b - lum) * factor)

    def shift_warmth(self, delta: float) -> "RGB":
        """Positive delta → warmer (r up, b down); negative → cooler."""
        return RGB(self.r + delta * 0.15, self.g + delta * 0.02, self.b - delta * 0.18)


@dataclass(frozen=True)
class TimeState:
    """Absolute time descriptor for a rendering query."""

    hour: float = 12.0
    day_of_year: int = 180
    year: int = 2024


@dataclass(frozen=True)
class SunState:
    elevation: float    # degrees; negative = below horizon
    azimuth: float      # degrees compass from north (0=N, 90=E, 180=S, 270=W)
    above_horizon: bool


@dataclass(frozen=True)
class LightState:
    intensity: float            # 0.0–1.0 (0 = no light, 1 = full noon)
    scatter_r: float            # atmospheric scatter additive RGB
    scatter_g: float
    scatter_b: float
    shadow_attenuation: float   # 0.0–1.0 (1.0 = fully lit)

    @property
    def scatter_rgb(self) -> RGB:
        return RGB(self.scatter_r, self.scatter_g, self.scatter_b)


@dataclass(frozen=True)
class SeasonalState:
    season_factor: float    # 0.0 = full winter, 1.0 = full summer in local hemisphere
    snow_factor: float      # 0.0–1.0 (1.0 = heavy snow likely)
    vegetation_boost: float  # –1.0 to +1.0 (positive = greener)


@dataclass(frozen=True)
class DayCycleState:
    phase: str          # 'dawn' | 'morning' | 'noon' | 'afternoon' | 'sunset' | 'dusk' | 'night'
    warmth: float       # –1.0 (cool) to +1.0 (warm)
    contrast: float     # 0.0–1.0
    saturation: float   # 0.0–2.0 (1.0 = neutral)
    blue_bias: float    # 0.0–1.0 (added at night)
