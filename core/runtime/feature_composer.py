"""Semantic feature fusion for RodiO spatial runtime queries."""

from __future__ import annotations

from typing import Optional

from .runtime_types import FeatureVector


class FeatureComposer:
    """Compose DEM, ocean, climate, and slope signals into stable vectors."""

    def compose(
        self,
        dem_value: Optional[float],
        ocean_value: bool,
        climate_value: Optional[int] = None,
        slope_proxy: float = 0.0,
    ) -> FeatureVector:
        elevation = float(dem_value) if dem_value is not None else 0.0
        climate_class = float(climate_value) if climate_value is not None else 0.0
        return FeatureVector(
            elevation=elevation,
            ocean_flag=1.0 if ocean_value else 0.0,
            climate_class=climate_class,
            slope_proxy=float(slope_proxy),
        )

    def normalize(self, feature_vector: FeatureVector) -> FeatureVector:
        """Normalize to a bounded numeric space without mutating source data."""

        elevation_norm = _clamp((feature_vector.elevation + 11000.0) / 20000.0, 0.0, 1.0)
        climate_norm = _clamp(feature_vector.climate_class / 30.0, 0.0, 1.0)
        slope_norm = _clamp(feature_vector.slope_proxy / 5000.0, 0.0, 1.0)
        return FeatureVector(
            elevation=elevation_norm,
            ocean_flag=1.0 if feature_vector.ocean_flag >= 0.5 else 0.0,
            climate_class=climate_norm,
            slope_proxy=slope_norm,
        )

    def biome_proxy(self, dem_value: Optional[float], ocean_value: bool, climate_value: Optional[int]) -> float:
        """Return a simple continuous biome proxy for downstream M1-B prototyping."""

        if ocean_value:
            elevation = float(dem_value or 0.0)
            return 0.05 if elevation < -2000 else 0.15
        if climate_value in {1, 2, 3}:
            return 0.85
        if climate_value in {4, 5, 6, 7}:
            return 0.35
        if climate_value in {29, 30}:
            return 0.1
        if dem_value is not None and dem_value > 3000:
            return 0.45
        return 0.6


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
