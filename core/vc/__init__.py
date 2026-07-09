"""
core/vc — Visual Consistency Layer (VC)

Public surface:
    VisualConsistencyEngine — top-level pipeline entry point
    VCRenderContext         — stabilised rendering context output
    BiomeTransition         — biome boundary → smooth colour gradients
    CoastlineSmoother       — binary coastline → probability gradient band
    TemporalStabilizer      — EMA-based frame-to-frame continuity
"""

from .visual_consistency_engine import VisualConsistencyEngine
from .vc_types import VCRenderContext, BIOME_BASE_COLORS
from .biome_transition import BiomeTransition
from .coastline_smoother import CoastlineSmoother
from .temporal_stabilizer import TemporalStabilizer

__all__ = [
    "VisualConsistencyEngine",
    "VCRenderContext",
    "BIOME_BASE_COLORS",
    "BiomeTransition",
    "CoastlineSmoother",
    "TemporalStabilizer",
]
