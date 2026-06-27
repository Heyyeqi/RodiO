"""Spectral Earth Engine — physics-inspired nonlinear surface response models.

Pipeline position:
    GeoFieldEngine → SpectralEarthEngine → NoonAirColorizer → VisualUnificationEngine

Replaces linear blends in NoonAirColorizer with nonlinear spectral models:
- Ocean: Beer-Lambert absorption (red attenuates fastest, blue deepest)
- Ice: Lambertian + specular BRDF with spatial fracture variation
- Desert: ferric oxide spectral signature (warm soil model)
- Atmosphere: Rayleigh (λ^-4) + Mie (wavelength-neutral) scattering

All methods: numpy array in → numpy array out. No GPU, no random state, deterministic.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .geo_field_engine import AtmosphereField, IceField


class SpectralEarthEngine:
    """Nonlinear spectral response models for Earth surface types.

    Calibration anchors for ocean Beer-Lambert:
        depth_proxy=0 (deepest) → #052C4A  [  5,  44,  74]
        depth_proxy=1 (shallowest) → #2EC4C6 [ 46, 196, 198]
    mu derived: mu_r=-ln(5/46)=2.219, mu_g=-ln(44/196)=1.494, mu_b=-ln(74/198)=0.985
    """

    # Beer-Lambert per-channel absorption coefficients (normalized depth units)
    _MU = np.array([2.219, 1.494, 0.985], dtype=np.float32)
    # Reference at shallowest depth (depth_proxy=1) — calibration anchor
    _SHALLOW_REF = np.array([46.0, 196.0, 198.0], dtype=np.float32)

    # Ice BRDF base reflectance (pure ice at normal-ish incidence)
    _ICE_WHITE = np.array([230.0, 242.0, 252.0], dtype=np.float32)

    # Desert ferric soil reference
    _SAND_REF = np.array([194.0, 160.0, 119.0], dtype=np.float32)

    # Rayleigh sky tint (blue-dominant, calibrated from λ^-4 ratios)
    _RAYLEIGH_RGB = np.array([148.0, 196.0, 248.0], dtype=np.float32)
    # Mie haze (wavelength-neutral, forward-scattered)
    _MIE_RGB = np.array([210.0, 220.0, 230.0], dtype=np.float32)
    # Ocean-sky azure reflection
    _AZURE_RGB = np.array([185.0, 215.0, 248.0], dtype=np.float32)

    # ── Ocean ──────────────────────────────────────────────────────────────────

    def ocean_spectral_response(
        self, depth_field: np.ndarray, ocean_factor: np.ndarray
    ) -> np.ndarray:
        """Beer-Lambert ocean color: nonlinear per-channel absorption.

        Red attenuates fastest (mu=2.219), blue penetrates deepest (mu=0.985).
        Returns (H, W, 3) float32 in [0, 255] — the spectral color of ocean
        water at the given depth. NoonAirColorizer blends this with the original.

        depth_field:  (H, W) float32, 0=deepest, 1=shallowest
        ocean_factor: (H, W) float32, continuous ocean coverage [0, 1] (unused
                      here — caller controls blending weight externally)
        """
        # attenuation_depth: 0 = at surface (no attenuation), 1 = full depth
        attenuation_depth = (1.0 - depth_field)[..., None]  # (H, W, 1)

        # I = I_surface * exp(-mu * d)  [Beer-Lambert]
        attenuation = np.exp(-self._MU[None, None, :] * attenuation_depth)
        ocean_spectral = self._SHALLOW_REF[None, None, :] * attenuation

        return ocean_spectral.astype(np.float32)

    # ── Ice ───────────────────────────────────────────────────────────────────

    def ice_reflectance(
        self, ice_f: "IceField", sun_angle: float = 45.0
    ) -> np.ndarray:
        """Lambertian + minor specular BRDF for ice/snow.

        Returns (H, W, 3) float32 in [0, 252] — the color of a fully
        ice-covered surface. NoonAirColorizer blends via ice_factor.

        incidence_scale ≥ 0.75 keeps ice bright even at low sun angles.
        Spatial BRDF variation comes from the deterministic fracture pattern
        in ice_f.brightness_gradient (never random).
        """
        cos_inc = math.cos(math.radians(sun_angle))
        incidence_scale = 0.75 + 0.25 * cos_inc  # [0.75, 1.00]

        # Spatial variation: [0.88, 1.00] range via fracture gradient
        variation = (0.88 + 0.12 * ice_f.brightness_gradient)[..., None]

        reflectance = self._ICE_WHITE[None, None, :] * incidence_scale * variation

        # Spectral tilt: ice absorbs slightly in red, transmits blue preferentially
        b_shift = ice_f.blue_shift[..., None]
        r = np.maximum(reflectance[..., 0:1] - b_shift * 80.0, 0.0)
        g = reflectance[..., 1:2]
        b = np.minimum(reflectance[..., 2:3] + b_shift * 30.0, 252.0)

        return np.clip(np.concatenate([r, g, b], axis=2), 0.0, 252.0).astype(np.float32)

    # ── Desert ────────────────────────────────────────────────────────────────

    def desert_albedo(
        self, img: np.ndarray, desert_factor: np.ndarray
    ) -> np.ndarray:
        """Ferric oxide spectral signature for arid soil.

        Warms tones toward sand reference, preserves luma structure.
        desert_factor=0 → img unchanged; desert_factor=1 → full desert response.
        Returns (H, W, 3) float32.
        """
        f = img.astype(np.float32)
        luma = (0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]) / 255.0
        gray = luma[..., None] * 255.0

        # Mild de-saturation (ferric soils have moderate chroma)
        centered = f * 0.86 + gray * 0.14

        # Sand target scaled by brightness to preserve local luminance variation
        sand_scale = np.clip(0.72 + luma[..., None] * 0.46, 0.0, 1.0)
        target = np.clip(self._SAND_REF[None, None, :] * sand_scale, 0.0, 226.0)

        desert_result = centered * 0.70 + target * 0.30

        w = desert_factor[..., None]
        return (f * (1.0 - w) + desert_result * w).astype(np.float32)

    # ── Atmosphere ────────────────────────────────────────────────────────────

    def atmospheric_scattering(
        self, img: np.ndarray, atmo_f: "AtmosphereField"
    ) -> np.ndarray:
        """Rayleigh (λ^-4) + Mie (wavelength-neutral) scattering approximation.

        Rayleigh: blue-preferential scattering at limb/edges (from AtmosphereField).
        Mie: wavelength-neutral forward scatter → neutral horizon brightening.
        Ocean-sky: additive azure reflection on ocean-like surfaces (≤1.5%).
        Returns (H, W, 3) float32.
        """
        f = img.astype(np.float32)

        # Rayleigh: sky tint toward blue, driven by limb_glow field
        rayleigh = atmo_f.limb_glow[..., None]
        result = f * (1.0 - rayleigh) + self._RAYLEIGH_RGB[None, None, :] * rayleigh

        # Mie: neutral haze near horizon, driven by horizon_blend field
        mie = atmo_f.horizon_blend[..., None]
        result = result * (1.0 - mie) + self._MIE_RGB[None, None, :] * mie

        # Ocean-sky: additive azure on ocean surfaces (tiny, ≤1.5% from field)
        result = result + self._AZURE_RGB[None, None, :] * atmo_f.ocean_sky_continuity[..., None]

        return result.astype(np.float32)
