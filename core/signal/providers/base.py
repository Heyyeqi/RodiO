"""
BaseSignalProvider — abstract interface for pluggable data source adapters.

Implementors translate any raw geospatial data source (GEBCO DEM, MODIS
landcover, Köppen-Geiger climate, satellite ocean masks, etc.) into the four
primitive signal values that the RodiO runtime understands.

Each method must be a pure function of (lon, lat) — no required side effects.
Implementations may cache internally.

Coordinates:
    lon: float — longitude in degrees, range [−180, 180]
    lat: float — latitude in degrees, range [−90, 90]
"""

from abc import ABC, abstractmethod

from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag


class BaseSignalProvider(ABC):
    """
    Abstract base class for geospatial signal data sources.

    All four methods must be implemented. Return types are primitive
    (no nested objects, no numpy arrays) to keep the interface stable
    across data source changes.
    """

    @abstractmethod
    def get_dem(self, lon: float, lat: float) -> DEMValue:
        """
        Return surface elevation in metres at (lon, lat).

        Positive → above sea level (land). Negative → below (ocean / basin).
        Return 0.0 when no data is available.
        """

    @abstractmethod
    def get_landcover(self, lon: float, lat: float) -> LandcoverClass:
        """
        Return integer landcover class code at (lon, lat).

        0 = unknown / no data. Class codes are provider-defined.
        """

    @abstractmethod
    def get_climate(self, lon: float, lat: float) -> ClimateClass:
        """
        Return climate class at (lon, lat), or None when unavailable.

        Typically a Köppen-Geiger integer (1–30). Return None for ocean points
        or when the climate layer has no coverage at this location.
        """

    @abstractmethod
    def get_ocean(self, lon: float, lat: float) -> OceanFlag:
        """
        Return True if (lon, lat) is classified as ocean by the source data.

        False when no data or when point is land.
        """
