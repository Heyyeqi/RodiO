"""
core/m1 — Semantic Mask Derivation (M1)

Public surface:
    M1Pipeline          — full pipeline entry point
    MaskGenerator       — per-tile mask generation
    TileSegmenter       — grid decomposition and stitching
    SemanticFieldBuilder— SAL + D6 → scalar field conversion
    M1BridgeProvider    — M0 SpatialRuntime → SAL signal kwargs bridge
    SemanticMaskTile    — per-tile mask arrays
    TileBBox            — geographic tile bounds
    GlobalMaskSummary   — run_global() aggregate stats

Signal provider classes are defined in core/signal/providers/ — M1 does not
own or define any provider classes directly.
"""

from .m1_pipeline import M1Pipeline
from .mask_generator import MaskGenerator
from .tile_segmenter import TileSegmenter
from .semantic_field_builder import SemanticFieldBuilder
from core.signal.providers.m1_bridge import M1BridgeProvider
from .mask_types import (
    SemanticMaskTile, TileBBox, GlobalMaskSummary,
    BIOME_OCEAN, BIOME_LAND, BIOME_DESERT, BIOME_FOREST,
    BIOME_ICE, BIOME_UNKNOWN, BIOME_NAMES,
)

# Backward-compatible alias — do not add new usages.
RealSignalProvider = M1BridgeProvider

__all__ = [
    "M1Pipeline", "MaskGenerator", "TileSegmenter", "SemanticFieldBuilder",
    "M1BridgeProvider",
    "RealSignalProvider",   # deprecated alias, kept for existing tests
    "SemanticMaskTile", "TileBBox", "GlobalMaskSummary",
    "BIOME_OCEAN", "BIOME_LAND", "BIOME_DESERT", "BIOME_FOREST",
    "BIOME_ICE", "BIOME_UNKNOWN", "BIOME_NAMES",
]
