"""Query engine wrapper for spatial runtime point and batch requests."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from .runtime_types import SpatialState


class QueryEngine:
    def __init__(self, runtime):
        self.runtime = runtime

    def point_query(self, lon: float, lat: float) -> SpatialState:
        """Single point semantic query."""

        return self.runtime.query_point(lon, lat)

    def batch_query(self, points: Iterable[Tuple[float, float]]) -> List[SpatialState]:
        """Vectorized point query with no raster output."""

        return [self.point_query(lon, lat) for lon, lat in points]

    def feature_vectors(self, points: Sequence[Tuple[float, float]]) -> List[List[float]]:
        return [self.runtime.compute_feature_vector(lon, lat).as_list() for lon, lat in points]
