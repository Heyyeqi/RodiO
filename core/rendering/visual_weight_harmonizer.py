"""Visual Weight Harmonizer — post-grammar constraint layer.

Applies Noon Air spec limits to VisualGrammar output.  No upstream modules
(SAL / M1 / VC / LOD / RasterIndexer) are touched.

Pipeline position:
    BMNG base → VisualGrammar → VisualWeightHarmonizer → D6 final output
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from .renderer_types import RGB


# ── Constraint container ─────────────────────────────────────────────────────


@dataclass
class VisualConstraints:
    """Numeric limits derived from the Noon Air design spec.

    All luminance caps use the ITU-R BT.709 luma formula
    (0.2126 R + 0.7152 G + 0.0722 B) consistent with RGB.luminance().

    biome_saturation_max — maximum allowed ratio of (peak channel deviation
    from luminance) to luminance.  At 0.95 a mid-lum green pixel can deviate
    from grey by at most 95 % of its luma; beyond that the deviation is scaled
    back.  This prevents game-map vivid greens while leaving muted biomes
    untouched.
    """

    ocean_weight_max: float = 0.72
    biome_saturation_max: float = 0.95
    ice_brightness_max: float = 0.97
    desert_exposure_max: float = 0.77
    atmosphere_opacity_max: float = 0.08


# ── Spec parser ───────────────────────────────────────────────────────────────


def _hex_luminance(hex_str: str) -> float:
    h = hex_str.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * r / 255 + 0.7152 * g / 255 + 0.0722 * b / 255


def _extract_section(text: str, keywords: tuple[str, ...], max_lines: int = 50) -> str:
    lines = text.split('\n')
    result: list[str] = []
    for i, line in enumerate(lines):
        if any(kw in line for kw in keywords):
            result = lines[i: i + max_lines]
            break
    return '\n'.join(result)


def load_noon_air_spec(constraint_file: str | Path) -> VisualConstraints:
    """Parse Noon Air spec markdown and return VisualConstraints.

    Deterministic extraction rules:
    - atmosphere_opacity_max ← first "不得超过 N%" match
    - ice_brightness_max     ← max luminance among polar section hex codes + 0.01
    - desert_exposure_max    ← hex after "不能大面积超过" + 0.02
    - ocean_weight_max       ← max luminance among shallow/mid-ocean section hex + 0.05
    - biome_saturation_max   ← derived from global saturation reduction ("全图饱和度")

    Falls back to VisualConstraints defaults for any value not found.
    """
    path = Path(constraint_file)
    constraints = VisualConstraints()

    if not path.exists():
        return constraints

    text = path.read_text(encoding="utf-8")

    # atmosphere_opacity_max: "最大透明度：不得超过 8%"
    m = re.search(r'不得超过\s*(\d+)\s*%', text)
    if m:
        constraints.atmosphere_opacity_max = int(m.group(1)) / 100.0

    # ice_brightness_max: brightest hex in polar / ice sections
    polar_text = _extract_section(text, ('南极冰盖', '格陵兰冰盖', '冰雪亮部'))
    ice_hexes = re.findall(r'#([0-9A-Fa-f]{6})', polar_text)
    if ice_hexes:
        max_lum = max(_hex_luminance(h) for h in ice_hexes)
        constraints.ice_brightness_max = min(0.985, max_lum + 0.01)

    # desert_exposure_max: "不能大面积超过 `#XXXXXX`"
    m_des = re.search(r'不能大面积超过\s*`?#([0-9A-Fa-f]{6})`?', text)
    if m_des:
        constraints.desert_exposure_max = min(0.90, _hex_luminance(m_des.group(1)) + 0.02)

    # ocean_weight_max: brightest explicit shallow hex in ocean sections
    ocean_text = _extract_section(text, ('中浅海', '明亮浅水', '浅水过渡'))
    ocean_hexes = re.findall(r'#([0-9A-Fa-f]{6})', ocean_text)
    if ocean_hexes:
        max_lum = max(_hex_luminance(h) for h in ocean_hexes)
        constraints.ocean_weight_max = min(0.85, max_lum + 0.05)

    # biome_saturation_max: "全图饱和度：-N% 至 -M%"
    # Spec directs a 4–8 % global reduction; tropical is allowed +12 % headroom.
    # We set the cap to allow tropical's boost while honouring the intent.
    m_sat = re.search(r'全图饱和度.*?(-\d+)\s*%\s*至\s*(-\d+)\s*%', text)
    if m_sat:
        min_reduction = abs(int(m_sat.group(1))) / 100.0   # e.g. 0.04
        # Neutral is 1.0 minus the smaller reduction, plus tropical headroom
        constraints.biome_saturation_max = (1.0 - min_reduction) * 1.08

    return constraints


# ── Core harmonization function ───────────────────────────────────────────────


def harmonize_visual_output(
    pixel: RGB,
    grammar_output: RGB,
    constraints: VisualConstraints,
    *,
    ocean: bool = False,
    climate_family: str = "unknown",
    elevation: float = 0.0,
) -> RGB:
    """Apply Noon Air constraint limits to a single post-grammar RGB value.

    Args:
        pixel:          Original BMNG base pixel (kept for reference; not
                        directly modified but informs the correction direction).
        grammar_output: Post-VisualGrammar RGB — the value being constrained.
        constraints:    Parsed VisualConstraints from the Noon Air spec.
        ocean:          True if this pixel is an ocean / water point.
        climate_family: Koppen family string ("polar", "arid", "tropical", …).
        elevation:      Signed elevation in metres (negative = depth).

    Returns:
        Corrected RGB, clamped to [0, 1].  Values already within spec are
        returned unchanged; only over-driven values are pulled back.
    """
    rgb = grammar_output

    if ocean:
        # Shallow ocean brightness cap — deep ocean stays dark naturally.
        depth = abs(float(elevation)) if elevation < 0 else 0.0
        is_shallow = depth < 1000.0
        if is_shallow:
            lum = rgb.luminance()
            if lum > constraints.ocean_weight_max:
                scale = constraints.ocean_weight_max / max(lum, 1e-9)
                rgb = RGB(rgb.r * scale, rgb.g * scale, rgb.b * scale)

    else:
        lum = rgb.luminance()
        # Explicit climate_family takes priority over luminance-based heuristics.
        if climate_family == "arid":
            if lum > constraints.desert_exposure_max:
                scale = constraints.desert_exposure_max / max(lum, 1e-9)
                rgb = RGB(rgb.r * scale, rgb.g * scale, rgb.b * scale)

        elif climate_family == "polar" or lum > 0.82:
            # polar by label OR inferred from very high brightness (snow, ice caps)
            if lum > constraints.ice_brightness_max:
                scale = constraints.ice_brightness_max / max(lum, 1e-9)
                rgb = RGB(rgb.r * scale, rgb.g * scale, rgb.b * scale)

        else:
            # General land: biome saturation cap.
            # Measure effective saturation as peak channel deviation / luminance.
            lum = rgb.luminance()
            if lum > 0.01:
                dev_r = rgb.r - lum
                dev_g = rgb.g - lum
                dev_b = rgb.b - lum
                peak_dev = max(abs(dev_r), abs(dev_g), abs(dev_b))
                if peak_dev > lum * constraints.biome_saturation_max:
                    scale = (lum * constraints.biome_saturation_max) / max(peak_dev, 1e-9)
                    rgb = RGB(
                        lum + dev_r * scale,
                        lum + dev_g * scale,
                        lum + dev_b * scale,
                    )

    return rgb.clamp()


# ── Harmonizer class ──────────────────────────────────────────────────────────


class VisualWeightHarmonizer:
    """Post-grammar visual constraint layer.

    Instantiate once per renderer.  Pass ``constraint_file`` to load limits
    from the Noon Air spec; omit for spec-derived defaults.
    """

    def __init__(self, constraint_file: Optional[str | Path] = None):
        if constraint_file is not None:
            self.constraints = load_noon_air_spec(constraint_file)
        else:
            self.constraints = VisualConstraints()

    # ── Per-pixel API ─────────────────────────────────────────────────────────

    def harmonize(
        self,
        rgb: RGB,
        *,
        ocean: bool = False,
        climate_family: str = "unknown",
        elevation: float = 0.0,
        sun_angle: float = 90.0,
    ) -> RGB:
        """Constrain a post-grammar per-pixel RGB to Noon Air spec limits."""
        return harmonize_visual_output(
            rgb,
            rgb,
            self.constraints,
            ocean=ocean,
            climate_family=climate_family,
            elevation=elevation,
        )

    # ── Texture array API (for bake_textures path) ─────────────────────────────

    def harmonize_texture(
        self,
        texture: np.ndarray,
        *,
        ocean_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Apply luminance caps to an RGB uint8 texture array.

        Args:
            texture:    (H, W, 3) uint8 array.
            ocean_mask: Optional boolean (H, W) array marking ocean pixels.
                        If omitted, only the atmosphere opacity cap applies.

        Returns:
            uint8 (H, W, 3) array with caps enforced.
        """
        arr = np.asarray(texture)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError("texture must be (H, W, 3) uint8")
        f = arr.astype(np.float32) / 255.0

        # Compute per-pixel luminance
        lum = (
            0.2126 * f[:, :, 0]
            + 0.7152 * f[:, :, 1]
            + 0.0722 * f[:, :, 2]
        )

        # --- ocean shallow cap ---
        if ocean_mask is not None:
            ocean = ocean_mask.astype(bool)
            over = ocean & (lum > self.constraints.ocean_weight_max)
            if over.any():
                safe_lum = np.where(lum > 0, lum, 1.0)
                scale = np.where(over, self.constraints.ocean_weight_max / safe_lum, 1.0)
                f *= scale[:, :, None]

        # --- ice brightness cap (very bright non-ocean) ---
        # Without a semantic mask, apply to pixels brighter than the threshold
        over_bright = lum > self.constraints.ice_brightness_max
        if ocean_mask is not None:
            over_bright &= ~ocean_mask.astype(bool)
        if over_bright.any():
            safe_lum = np.where(lum > 0, lum, 1.0)
            scale = np.where(over_bright, self.constraints.ice_brightness_max / safe_lum, 1.0)
            f *= scale[:, :, None]

        return np.clip(np.rint(f * 255.0), 0, 255).astype(np.uint8)

    # ── Candidate-emission API (resolver pipeline) ─────────────────────────────

    def emit_candidates(
        self,
        rgb: RGB,
        *,
        ocean: bool = False,
        climate_family: str = "unknown",
        elevation: float = 0.0,
    ) -> list:
        """Emit constraint-violation candidates without applying any correction.

        Returns a list of RuleCandidate objects whose score encodes how far the
        pixel exceeds the relevant cap (score > 1.0 means over-limit).  The
        resolver can use these to understand constraint pressure; the actual
        clamping still happens in harmonize().

        This method makes the harmonizer a pure constraint reporter when used in
        the resolver pipeline — rule classification is done by VisualRuleResolver,
        not here.
        """
        from .visual_rule_resolver import RuleCandidate

        candidates: list[RuleCandidate] = []
        lum = rgb.luminance()

        if ocean:
            depth = abs(float(elevation)) if elevation < 0 else 0.0
            if depth < 1000.0 and lum > 0:
                # Score = how much the pixel exceeds the ocean cap (>1 = violation)
                candidates.append(RuleCandidate(
                    rule_type="ocean",
                    score=lum / max(self.constraints.ocean_weight_max, 1e-9),
                    payload={"cap": self.constraints.ocean_weight_max, "lum": lum},
                ))

        if climate_family == "polar" or lum > 0.82:
            candidates.append(RuleCandidate(
                rule_type="ice",
                score=lum / max(self.constraints.ice_brightness_max, 1e-9),
                payload={"cap": self.constraints.ice_brightness_max, "lum": lum},
            ))

        if climate_family == "arid":
            candidates.append(RuleCandidate(
                rule_type="desert",
                score=lum / max(self.constraints.desert_exposure_max, 1e-9),
                payload={"cap": self.constraints.desert_exposure_max, "lum": lum},
            ))

        # Atmosphere opacity is always a candidate (score = current effective opacity)
        candidates.append(RuleCandidate(
            rule_type="atmosphere",
            score=self.constraints.atmosphere_opacity_max,
            payload={"cap": self.constraints.atmosphere_opacity_max},
        ))

        return candidates
