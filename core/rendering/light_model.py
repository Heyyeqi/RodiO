"""Simplified physical light model for D6 CPU renderer.

No ray tracing. Models: cosine sun intensity, atmospheric scattering
(Rayleigh-approximate), and slope-based terrain attenuation.
"""

from __future__ import annotations

import math

from .renderer_types import LightState


class LightModel:

    def compute_intensity(self, sun_elevation: float) -> float:
        """Lambert cosine sun intensity.

        Returns 0 when sun is at or below horizon; peaks at 1.0 for 90°.
        Civil twilight (elevation > -6°) contributes a small ambient floor.
        """
        if sun_elevation <= -6.0:
            return 0.0
        if sun_elevation <= 0.0:
            # Civil twilight: linear ramp 0→0.05
            return 0.05 * (1.0 + sun_elevation / 6.0)
        # Sine of elevation = cosine of zenith angle
        raw = math.sin(math.radians(sun_elevation))
        # Atmospheric correction: low-angle sunlight travels further through atmosphere
        # Simple approximation: reduce near-horizon intensity slightly
        correction = 1.0 - 0.12 * math.exp(-sun_elevation / 15.0)
        return min(1.0, raw * correction)

    def atmospheric_scatter(self, sun_elevation: float, ocean_flag: bool) -> LightState:
        """Rayleigh-approximate atmospheric scatter contribution.

        Returns the complete LightState including scatter additive RGB.
        Ocean surfaces get a stronger blue shift from reflected sky.

        Scatter is a small additive term; values are intentionally low (≤ 0.08).
        """
        intensity = self.compute_intensity(sun_elevation)

        if sun_elevation <= -6.0:
            # Full night: faint blue ambient (starlight / moonlight proxy)
            return LightState(
                intensity=0.0,
                scatter_r=0.0,
                scatter_g=0.002,
                scatter_b=0.015,
                shadow_attenuation=1.0,
            )

        # Rayleigh scatter peaks at blue wavelengths; scales with air mass
        # Air mass approximation: 1/sin(elevation) for elevation > 3°
        if sun_elevation < 3.0:
            air_mass = 10.0
        else:
            air_mass = min(10.0, 1.0 / math.sin(math.radians(sun_elevation)))

        # Blue scatter contribution grows with air mass (low sun → more scattering)
        blue_scatter = min(0.06, 0.003 * air_mass)
        # Red/orange glow near horizon (longer path length → blue absorbed → warm remainder)
        red_scatter = min(0.04, 0.002 * max(0, air_mass - 3.0))
        green_scatter = red_scatter * 0.4

        # Ocean adds sky reflection (blue bias)
        ocean_blue_boost = 0.025 if ocean_flag else 0.0

        # Twilight: bleed warm colours into scatter
        if sun_elevation < 5.0 and sun_elevation > -6.0:
            warmth = (5.0 - sun_elevation) / 11.0  # 0 at elev=5, 1 at elev=-6
            red_scatter += warmth * 0.04
            green_scatter += warmth * 0.015

        scatter_b = blue_scatter * intensity + ocean_blue_boost
        scatter_g = green_scatter * intensity
        scatter_r = red_scatter * intensity

        return LightState(
            intensity=intensity,
            scatter_r=scatter_r,
            scatter_g=scatter_g,
            scatter_b=scatter_b,
            shadow_attenuation=1.0,  # filled in by shadow_factor
        )

    def shadow_factor(self, slope_proxy: float) -> float:
        """Terrain-based ambient light attenuation from slope proxy.

        slope_proxy is the raw DEM elevation difference (meters) between
        adjacent pixels (~4.9 km apart at 8K). Very large values indicate
        cliff-like relief; small values indicate flat terrain.

        At 8K resolution this is coarse — treat as a soft ambient modifier only.
        """
        # Normalise against a realistic max cliff-face at 8K (≈ 3000m over one pixel)
        norm = min(1.0, slope_proxy / 3000.0)
        # Gentle attenuation: high slope → up to 20% darker ambient
        return 1.0 - 0.20 * (norm ** 0.7)

    def build(self, sun_elevation: float, slope_proxy: float, ocean_flag: bool) -> LightState:
        """Convenience: build a complete LightState in one call."""
        base = self.atmospheric_scatter(sun_elevation, ocean_flag)
        shadow = self.shadow_factor(slope_proxy)
        return LightState(
            intensity=base.intensity,
            scatter_r=base.scatter_r,
            scatter_g=base.scatter_g,
            scatter_b=base.scatter_b,
            shadow_attenuation=shadow,
        )
