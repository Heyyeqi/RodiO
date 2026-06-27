"""
M1 Mask Types — shared data structures for the semantic mask generation system.
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Callable, Dict
import numpy as np


# ---------------------------------------------------------------------------
# Biome integer codes stored in biome_mask
# ---------------------------------------------------------------------------
BIOME_OCEAN        = 0
BIOME_SHALLOW      = 1
BIOME_LAND         = 2
BIOME_DESERT       = 3
BIOME_FOREST       = 4
BIOME_WETLAND      = 5
BIOME_ICE          = 6
BIOME_URBAN        = 7
BIOME_UNKNOWN      = 255

SEMANTIC_TO_BIOME: Dict[str, int] = {
    "ocean":         BIOME_OCEAN,
    "shallow_water": BIOME_SHALLOW,
    "land":          BIOME_LAND,
    "desert":        BIOME_DESERT,
    "forest":        BIOME_FOREST,
    "wetland":       BIOME_WETLAND,
    "ice":           BIOME_ICE,
    "urban":         BIOME_URBAN,
    "unknown":       BIOME_UNKNOWN,
}

BIOME_NAMES: Dict[int, str] = {v: k for k, v in SEMANTIC_TO_BIOME.items()}

# Ocean mask threshold: SAL probability_map["ocean"] must exceed this to
# mark a point as ocean in the probabilistic ocean mask.
# Set just below the expected pure-ocean probability (~0.17) but above the
# expected land-dominant ocean probability (~0.13).
OCEAN_PROB_THRESHOLD = 0.145


@dataclass
class TileBBox:
    """Geographic bounding box for one mask tile."""
    lon_min: float    # degrees, −180 to 180
    lon_max: float
    lat_min: float    # degrees, −90 to 90
    lat_max: float
    col_idx: int = 0  # grid column index (0-based)
    row_idx: int = 0  # grid row index (0-based)

    @property
    def width_deg(self) -> float:
        return self.lon_max - self.lon_min

    @property
    def height_deg(self) -> float:
        return self.lat_max - self.lat_min

    def __repr__(self) -> str:
        return (
            f"TileBBox(lon=[{self.lon_min:.1f},{self.lon_max:.1f}] "
            f"lat=[{self.lat_min:.1f},{self.lat_max:.1f}] "
            f"tile=({self.col_idx},{self.row_idx}))"
        )


@dataclass
class SemanticMaskTile:
    """
    Per-tile semantic mask arrays.

    All arrays share the same shape (rows, cols).
    dtype conventions:
        ocean_mask:       bool     — True where SAL class = ocean
        land_mask:        bool     — True where SAL class = land-family
        biome_mask:       uint8    — BIOME_* integer code per point
        uncertainty_mask: float32  — [0, 1], 0=certain, 1=max uncertain
        confidence_mask:  float32  — SAL confidence_score per point
        ocean_prob_mask:  float32  — raw SAL probability_map["ocean"]
    """
    bbox: TileBBox
    ocean_mask:       np.ndarray   # bool
    land_mask:        np.ndarray   # bool
    biome_mask:       np.ndarray   # uint8
    uncertainty_mask: np.ndarray   # float32
    confidence_mask:  np.ndarray   # float32
    ocean_prob_mask:  np.ndarray   # float32
    shape: Tuple[int, int] = field(init=False)

    def __post_init__(self):
        self.shape = self.ocean_mask.shape

    def ocean_fraction(self) -> float:
        return float(self.ocean_mask.mean())

    def land_fraction(self) -> float:
        return float(self.land_mask.mean())

    def mean_uncertainty(self) -> float:
        return float(self.uncertainty_mask.mean())

    def mean_confidence(self) -> float:
        return float(self.confidence_mask.mean())


# Signal provider type: callable(lon, lat) → dict of SAL signal kwargs
SignalProvider = Callable[[float, float], Dict]


@dataclass
class GlobalMaskSummary:
    """Aggregate stats after a run_global() pass."""
    total_tiles: int
    completed_tiles: int
    global_ocean_fraction: float
    global_land_fraction: float
    mean_uncertainty: float
    tile_summaries: List[dict] = field(default_factory=list)
