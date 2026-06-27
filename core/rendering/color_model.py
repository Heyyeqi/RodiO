"""Color model: semantic palette × temporal × light → final RGB.

Biome palette is anchored to the discrete biome_proxy values emitted by
FeatureComposer.biome_proxy():
    0.05 → deep ocean      (< −2000 m)
    0.15 → shallow ocean   (ocean, elevation ≥ −2000 m)
    0.35 → arid / desert   (Köppen BWh/BWk/BSh/BSk)
    0.45 → highland        (elevation > 3000 m, non-ocean)
    0.60 → temperate       (everything else on land)
    0.85 → tropical        (Köppen Af/Am/Aw)

Between-anchor colours are linearly interpolated so novel biome_proxy
values (e.g. from future mask layers) degrade gracefully.
"""

from __future__ import annotations

import math

from .renderer_types import RGB, DayCycleState, LightState, SeasonalState


# ── Palette anchors ──────────────────────────────────────────────────────────

_PALETTE: list[tuple[float, RGB]] = [
    (0.00, RGB(0.01, 0.04, 0.16)),   # abyssal / void (shouldn't normally hit)
    (0.05, RGB(0.02, 0.06, 0.22)),   # deep ocean
    (0.15, RGB(0.06, 0.19, 0.42)),   # shallow ocean / coastal
    (0.35, RGB(0.78, 0.64, 0.32)),   # arid desert
    (0.45, RGB(0.54, 0.50, 0.37)),   # highland / rocky
    (0.60, RGB(0.22, 0.52, 0.17)),   # temperate land
    (0.85, RGB(0.07, 0.50, 0.12)),   # tropical forest
    (1.00, RGB(0.05, 0.48, 0.10)),   # deep tropical (future extension)
]

_SNOW_WHITE = RGB(0.92, 0.94, 0.97)
_NIGHT_AMBIENT = RGB(0.005, 0.008, 0.025)


def _interpolate_palette(proxy: float) -> RGB:
    """Linear interpolation across the palette anchor list."""
    proxy = max(0.0, min(1.0, proxy))
    for i in range(len(_PALETTE) - 1):
        lo_p, lo_c = _PALETTE[i]
        hi_p, hi_c = _PALETTE[i + 1]
        if lo_p <= proxy <= hi_p:
            if hi_p == lo_p:
                return lo_c
            t = (proxy - lo_p) / (hi_p - lo_p)
            return lo_c.lerp(hi_c, t)
    return _PALETTE[-1][1]


class ColorModel:

    def base_color(self, biome_proxy: float, ocean: bool) -> RGB:
        """Base semantic colour from biome proxy and ocean flag.

        Special case: FeatureComposer maps Köppen EF (polar frost) to
        biome_proxy=0.10, which sits between the deep-ocean and shallow-ocean
        palette anchors. On non-ocean pixels (ice sheets, Himalayan EF zones)
        this would produce dark navy. Override to glacial white.
        """
        # Polar / glacial ice: non-ocean land with a very low biome_proxy
        # (EF classification from FeatureComposer → 0.10)
        if not ocean and biome_proxy < 0.20:
            return RGB(0.80, 0.88, 0.95)  # icy blue-white

        base = _interpolate_palette(biome_proxy)
        # Ensure ocean flag always pulls toward blue regardless of proxy edge cases
        if ocean and biome_proxy > 0.20:
            base = base.lerp(RGB(0.06, 0.19, 0.42), 0.7)
        return base

    def apply_temporal_shift(
        self,
        color: RGB,
        season: SeasonalState,
        day_cycle: DayCycleState,
    ) -> RGB:
        """Apply seasonal and diurnal colour modulation.

        Operations (all linear RGB):
        1. Seasonal vegetation boost  → green channel push on land
        2. Snow blending              → lerp toward snow white at high snow_factor
        3. Diurnal warmth shift       → warm/cool RGB rotation
        4. Saturation scale           → compress toward grey for night / twilight
        5. Blue bias                  → additive night ambient
        """
        result = color

        # 1. Vegetation season boost (only meaningful on green-ish biomes)
        if season.vegetation_boost > 0 and color.g > 0.15 and color.r < 0.6:
            green_gain = season.vegetation_boost * 0.12
            result = RGB(result.r - green_gain * 0.3, result.g + green_gain, result.b - green_gain * 0.1)

        # 2. Snow blending
        if season.snow_factor > 0.05:
            result = result.lerp(_SNOW_WHITE, season.snow_factor * 0.8)

        # 3. Diurnal warmth
        if abs(day_cycle.warmth) > 0.01:
            result = result.shift_warmth(day_cycle.warmth)

        # 4. Saturation
        if abs(day_cycle.saturation - 1.0) > 0.01:
            result = result.saturate(day_cycle.saturation)

        # 4b. Contrast: luminance-relative range compression applied after saturation.
        # Dawn (0.15) and night (0.08) compress colours toward their own luminance,
        # giving a flat, low-contrast appearance before the light model darkens them.
        # Noon (1.0) leaves the colour unchanged.
        if abs(day_cycle.contrast - 1.0) > 0.01:
            result = result.saturate(day_cycle.contrast)

        # 5. Night blue bias (additive)
        if day_cycle.blue_bias > 0.01:
            result = RGB(result.r, result.g, result.b + day_cycle.blue_bias * 0.08)

        return result

    def apply_light(self, color: RGB, light: LightState) -> RGB:
        """Physically-inspired light application.

        Formula: lit = color × intensity × shadow + ambient_floor + scatter
        The ambient floor prevents fully-lit colours from going completely black
        at night (moonlight / sky glow proxy).
        """
        ambient_floor = 0.035
        effective_intensity = light.intensity * light.shadow_attenuation

        # Scale base colour by light level
        lit = color * (ambient_floor + (1.0 - ambient_floor) * effective_intensity)

        # Add atmospheric scatter (always small additive)
        lit = lit + light.scatter_rgb

        return lit

    def final_color(
        self,
        biome_proxy: float,
        ocean: bool,
        light: LightState,
        season: SeasonalState,
        day_cycle: DayCycleState,
    ) -> RGB:
        """Full rendering pipeline: palette → temporal → light → clamped RGB."""
        base = self.base_color(biome_proxy, ocean)
        shifted = self.apply_temporal_shift(base, season, day_cycle)
        lit = self.apply_light(shifted, light)
        return lit.clamp()
