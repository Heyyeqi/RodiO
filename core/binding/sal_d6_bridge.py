"""
SAL → D6 Bridge

Top-level entry point for the binding layer. Given a lon/lat coordinate and
a TemporalState, it:
  1. Calls the SemanticArbitrator to obtain a semantic decision
  2. Passes the result through RenderingContextBuilder
  3. Returns a D6RenderInput ready for the renderer

No raster output, no GPU ops, no modification of SAL or M0 logic.
"""

from typing import Optional

from core.sal import SemanticArbitrator
from .binding_types import D6RenderInput, TemporalState
from .rendering_context_builder import RenderingContextBuilder


class SALD6Bridge:
    """
    Connects SemanticArbitrator output to D6 renderer input.

    Usage:
        bridge = SALD6Bridge(sal=SemanticArbitrator(), runtime=None)
        ctx = bridge.convert(lon=35.5, lat=31.5, time_state=TemporalState(...),
                             dem_signal="ocean", climate_signal="land", ...)
    """

    def __init__(self, sal: Optional[SemanticArbitrator] = None, runtime=None):
        """
        Args:
            sal:     SemanticArbitrator instance (default: new with default weights)
            runtime: optional runtime/context object (reserved for M0 integration)
        """
        self._sal = sal or SemanticArbitrator()
        self._runtime = runtime
        self._builder = RenderingContextBuilder()

    def convert(
        self,
        lon: float,
        lat: float,
        time_state: Optional[TemporalState] = None,
        # Source signals
        dem_signal: Optional[str] = None,
        dem_confidence: float = 1.0,
        climate_signal: Optional[str] = None,
        climate_confidence: float = 1.0,
        ocean_signal: Optional[str] = None,
        ocean_confidence: float = 1.0,
        landcover_signal: Optional[str] = None,
        landcover_confidence: float = 1.0,
    ) -> D6RenderInput:
        """
        Convert a geographic point + source signals into a D6 render input.

        Args:
            lon, lat:   geographic coordinates (unused in SAL but carried for
                        future spatial context / M0 integration)
            time_state: temporal context for seasonal and diurnal modulation
            *_signal:   semantic class from each source layer (or None)
            *_confidence: per-source confidence (0–1)

        Returns:
            D6RenderInput with all visual parameters set.
        """
        # Propagate lat into TemporalState if not already set
        if time_state is None:
            time_state = TemporalState(month=6, hour=12, lat=lat)
        else:
            # Attach lat for solar/seasonal calculations
            object.__setattr__(time_state, 'lat', lat) \
                if hasattr(time_state, '__dataclass_fields__') else None
            time_state = TemporalState(
                month=time_state.month,
                hour=time_state.hour,
                lat=lat,
                climate_zone=time_state.climate_zone,
                snow_cover=time_state.snow_cover,
                cloud_cover=time_state.cloud_cover,
            )

        # SAL arbitration
        sal_result = self._sal.resolve(
            dem_signal=dem_signal,           dem_confidence=dem_confidence,
            climate_signal=climate_signal,   climate_confidence=climate_confidence,
            ocean_signal=ocean_signal,       ocean_confidence=ocean_confidence,
            landcover_signal=landcover_signal, landcover_confidence=landcover_confidence,
        )

        # Build D6 context
        return self._builder.build(sal_result, time_state)

    def convert_from_sal_result(
        self,
        sal_result,
        time_state: Optional[TemporalState] = None,
    ) -> D6RenderInput:
        """
        Convert a pre-computed ArbitrationResult directly into a D6 render input.
        Useful when SAL has already been run upstream (e.g., in batch pipelines).
        """
        return self._builder.build(sal_result, time_state)
