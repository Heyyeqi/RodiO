"""
M1BridgeProvider — bridges M0 SpatialRuntime output into SAL signal kwargs.

Canonical location for the provider that was previously named RealSignalProvider
in core/m1/real_signal_provider.py. Renamed to M1BridgeProvider to clarify
that it is a bridge between the M0 runtime layer and the SAL signal format,
not a general-purpose signal provider.

This is the M1 domain enrichment layer: it translates SpatialState (elevation,
ocean flag, climate class, slope) into the four-signal dict that SAL expects.
It does NOT implement BaseSignalProvider; it is a callable-protocol provider
operating at the SAL signal level, not the raw data level.

Callable protocol: (lon: float, lat: float) → dict of SAL signal kwargs
    dem_signal, climate_signal, ocean_signal, landcover_signal
    plus corresponding *_confidence values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.runtime import SpatialRuntime, SpatialState


class M1BridgeProvider:
    """
    Callable SignalProvider backed by M0 SpatialRuntime.

    Translates SpatialRuntime.query_point() output into the SAL signal kwargs
    dict expected by SemanticArbitrator.resolve() and SALD6Bridge.convert().

    Not a BaseSignalProvider subclass: it operates at the SAL signal level
    (semantic class labels + confidence scores), not the raw data level.
    """

    def __init__(self, runtime: SpatialRuntime):
        self.runtime = runtime

    @classmethod
    def from_source_cache(cls, source_cache_root: str | Path) -> "M1BridgeProvider":
        """Build a provider from the existing RodiO source cache."""
        return cls(SpatialRuntime.from_source_cache(source_cache_root))

    def __call__(self, lon: float, lat: float) -> dict:
        state = self.runtime.query_point(lon, lat)
        dem_signal = _dem_signal(state.elevation)
        climate_signal = _climate_signal(state.climate_class)
        ocean_signal = "ocean" if state.ocean else "land"
        landcover_signal = _landcover_signal(state)

        return {
            "dem_signal":          dem_signal,
            "dem_confidence":      _dem_confidence(state.elevation),
            "climate_signal":      climate_signal,
            "climate_confidence":  _climate_confidence(state.climate_class),
            "ocean_signal":        ocean_signal,
            "ocean_confidence":    _ocean_confidence(state),
            "landcover_signal":    landcover_signal,
            "landcover_confidence": _landcover_confidence(state),
        }


# ---------------------------------------------------------------------------
# Signal translation helpers
# ---------------------------------------------------------------------------

def _dem_signal(elevation: Optional[float]) -> str:
    if elevation is None:
        return "unknown"
    return "ocean" if elevation < 0 else "land"


def _dem_confidence(elevation: Optional[float]) -> float:
    if elevation is None:
        return 0.10
    return _clamp(0.55 + min(abs(float(elevation)), 3000.0) / 3000.0 * 0.40)


def _climate_signal(climate_class: Optional[int]) -> Optional[str]:
    return "land" if climate_class is not None and climate_class > 0 else None


def _climate_confidence(climate_class: Optional[int]) -> float:
    return 0.86 if climate_class is not None and climate_class > 0 else 0.0


def _ocean_confidence(state: SpatialState) -> float:
    rule = str(state.source.get("ocean_rule", ""))
    if "overridden" in rule:
        return 0.88
    if state.ocean:
        return _clamp(0.70 + min(abs(state.elevation), 5000.0) / 5000.0 * 0.25)
    return _clamp(0.65 + min(max(state.elevation, 0.0), 3000.0) / 3000.0 * 0.25)


def _landcover_signal(state: SpatialState) -> str:
    if state.ocean:
        return "ocean"
    climate_class = state.climate_class
    if climate_class in {1, 2, 3}:
        return "forest"
    if climate_class in {4, 5, 6, 7}:
        return "desert"
    if climate_class in {29, 30}:
        return "ice"
    if state.elevation > 4500:
        return "ice"
    return "land"


def _landcover_confidence(state: SpatialState) -> float:
    if state.ocean:
        return 0.82
    if state.climate_class is not None:
        return 0.72
    return 0.55


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))
