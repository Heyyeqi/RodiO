"""In-memory spatial runtime engine for RodiO geospatial semantics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterable, Optional, Tuple

import numpy as np
import tifffile as tiff

from .feature_composer import FeatureComposer
from .runtime_types import BBox, FeatureVector, GlobalGridLock, SpatialState, WindowState

if TYPE_CHECKING:
    from core.signal.providers.base import BaseSignalProvider


class DEMOceanTruthKernel:
    """Runtime ocean rule: ocean is true when DEM elevation/depth is below 0."""

    def classify(self, elevation: Optional[float]) -> bool:
        return elevation is not None and elevation < 0


class ClimateRasterLayer:
    """Lazy Köppen-Geiger climate lookup gated by GlobalGridLock alignment."""

    def __init__(self, path: str | Path, grid_lock: GlobalGridLock):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self.grid_lock = grid_lock
        self._metadata: Optional[Dict[str, object]] = None
        self._array: Optional[np.ndarray] = None
        validation = self.grid_lock.validate_layer_metadata(self.metadata)
        if not validation["ok"]:
            raise ValueError(f"Climate layer is not grid-locked: {validation['issues']}")

    @property
    def metadata(self) -> Dict[str, object]:
        if self._metadata is None:
            with tiff.TiffFile(str(self.path)) as tf:
                page = tf.pages[0]
                scale = page.tags["ModelPixelScaleTag"].value
                tiepoint = page.tags["ModelTiepointTag"].value
                self._metadata = {
                    "path": str(self.path),
                    "shape": tuple(int(v) for v in page.shape),
                    "dtype": str(page.dtype),
                    "origin_x": float(tiepoint[3]),
                    "origin_y": float(tiepoint[4]),
                    "pixel_x": float(scale[0]),
                    "pixel_y": float(scale[1]),
                    "crs": "EPSG:4326",
                }
        return self._metadata

    def _load_array(self) -> np.ndarray:
        if self._array is None:
            with tiff.TiffFile(str(self.path)) as tf:
                page = tf.pages[0]
                self._array = tiff.memmap(str(self.path)) if page.is_memmappable else page.asarray()
        return self._array

    def get_value(self, lon: float, lat: float) -> Optional[int]:
        index = self.grid_lock.index_for(lon, lat)
        value = int(self._load_array()[index.row, index.col])
        return value if value > 0 else None


_BLEND_MODES = frozenset({"synthetic", "hybrid"})
_RESOLUTION_MODES = frozenset({"8k", "21k"})

_SYNTHETIC_WEIGHT = 0.8
_GROUNDING_WEIGHT = 0.2


class SpatialRuntime:
    def __init__(
        self,
        dem_registry=None,
        grid_lock: Optional[GlobalGridLock] = None,
        ocean_kernel: Optional[DEMOceanTruthKernel] = None,
        climate_layer: Optional[ClimateRasterLayer] = None,
        feature_composer: Optional[FeatureComposer] = None,
        signal_provider: Optional["BaseSignalProvider"] = None,
        signal_blend_mode: str = "synthetic",
        grounding_provider: Optional["BaseSignalProvider"] = None,
        real_world_provider: Optional["BaseSignalProvider"] = None,
        resolution_mode: str = "8k",
    ):
        if dem_registry is None and signal_provider is None and real_world_provider is None:
            raise ValueError(
                "SpatialRuntime requires at least one of: dem_registry, signal_provider, "
                "or real_world_provider"
            )
        if signal_blend_mode not in _BLEND_MODES:
            raise ValueError(
                f"signal_blend_mode must be one of {sorted(_BLEND_MODES)!r}, "
                f"got {signal_blend_mode!r}"
            )
        if resolution_mode not in _RESOLUTION_MODES:
            raise ValueError(
                f"resolution_mode must be one of {sorted(_RESOLUTION_MODES)!r}, "
                f"got {resolution_mode!r}"
            )
        self.dem_registry = dem_registry
        self.grid_lock = grid_lock or GlobalGridLock()
        self.ocean_kernel = ocean_kernel or DEMOceanTruthKernel()
        self.climate_layer = climate_layer
        self.feature_composer = feature_composer or FeatureComposer()
        self._signal_provider: Optional["BaseSignalProvider"] = signal_provider
        self.signal_blend_mode: str = signal_blend_mode
        self._grounding_provider: Optional["BaseSignalProvider"] = grounding_provider
        self._real_world_provider: Optional["BaseSignalProvider"] = real_world_provider
        self.resolution_mode: str = resolution_mode
        self.m1 = None
        self.vc = None
        self.d6_renderer = None

    def set_signal_provider(self, provider: Optional["BaseSignalProvider"]) -> None:
        """Inject or replace the signal provider at runtime."""
        self._signal_provider = provider

    def set_grounding_provider(self, provider: Optional["BaseSignalProvider"]) -> None:
        """Inject or replace the grounding provider used in hybrid blend mode."""
        self._grounding_provider = provider

    def set_real_world_provider(self, provider: Optional["BaseSignalProvider"]) -> None:
        """
        Inject or replace the real-world signal provider.

        When set, this provider takes highest priority in query_point() —
        overriding both signal_provider (Stage 2 synthetic/hybrid path) and
        the legacy dem_registry path. Fallback to lower-priority paths is
        automatic when real_world_provider is None.
        """
        self._real_world_provider = provider

    def set_resolution(self, mode: str) -> None:
        """
        Set the raster resolution mode for future provider bindings.

        This is a scale switch only. It does not mutate existing provider
        objects or alter SAL / M1 / VC / D6 logic. Attached visual modules
        receive the mode as sampling metadata.
        """
        if mode not in _RESOLUTION_MODES:
            raise ValueError(
                f"resolution mode must be one of {sorted(_RESOLUTION_MODES)!r}, got {mode!r}"
            )
        self.resolution_mode = mode
        for module in (self.m1, self.vc, self.d6_renderer):
            if module is not None and hasattr(module, "set_resolution"):
                module.set_resolution(mode)

    def attach_visual_pipeline(self, m1=None, vc=None, d6_renderer=None) -> None:
        """Attach optional visual modules for resolution-mode propagation."""
        self.m1 = m1
        self.vc = vc
        self.d6_renderer = d6_renderer
        for module in (self.m1, self.vc, self.d6_renderer):
            if module is not None and hasattr(module, "set_resolution"):
                module.set_resolution(self.resolution_mode)

    def set_earth_loader(self, registry) -> None:
        """
        Build a RasterBackedProvider from a RasterLayerRegistry and activate it.

        One-call binding: reads "ocean" (GEBCO), "dem" (ETOPO1), and "climate"
        (Köppen) layers from the registry, constructs the matching provider
        adapters, and injects the assembled RasterBackedProvider via
        set_real_world_provider(). Layers absent from the registry are silently
        skipped; the provider falls back to safe defaults for those signals.

        Args:
            registry: RasterLayerRegistry with pre-loaded numpy arrays.
        """
        from core.signal.raster_indexer import RasterIndexer
        from core.signal.providers.gebco_provider import GEBCOProvider
        from core.signal.providers.etopo_provider import ETOPOProvider
        from core.signal.providers.koppen_provider import KoppenProvider
        from core.signal.providers.raster_backed_provider import RasterBackedProvider

        def _indexer(layer):
            if layer is None:
                return None
            if self.resolution_mode == "8k":
                return RasterIndexer.from_array(layer["array"])
            return RasterIndexer.from_array(
                layer["array"], resolution_mode=self.resolution_mode
            )

        gebco  = (GEBCOProvider(_indexer(registry.get_layer("ocean")), resolution_mode=self.resolution_mode)
                  if registry.is_loaded("ocean") else None)
        etopo  = (ETOPOProvider(_indexer(registry.get_layer("dem")), resolution_mode=self.resolution_mode)
                  if registry.is_loaded("dem") else None)
        koppen = (KoppenProvider(_indexer(registry.get_layer("climate")), resolution_mode=self.resolution_mode)
                  if registry.is_loaded("climate") else None)

        self.set_real_world_provider(RasterBackedProvider(gebco=gebco, etopo=etopo, koppen=koppen))

    def enable_lite_grounding(self) -> None:
        """
        Switch the current signal provider into lite-grounding mode.

        Only effective when the active provider is a RuntimeStubProvider.
        If the provider does not support lite grounding, a ValueError is raised
        so callers are never silently left in stub-only mode.
        """
        provider = self._signal_provider
        if provider is None:
            raise ValueError(
                "enable_lite_grounding() requires an active signal_provider; "
                "this SpatialRuntime uses dem_registry only"
            )
        if not hasattr(provider, "enable_lite_grounding"):
            raise ValueError(
                f"signal_provider {type(provider).__name__!r} does not support "
                "lite grounding (missing enable_lite_grounding attribute)"
            )
        provider.enable_lite_grounding = True

    @classmethod
    def from_source_cache(cls, source_cache_root: str | Path) -> "SpatialRuntime":
        from core.dem import DEMRegistry

        root = Path(source_cache_root)
        grid_lock = GlobalGridLock()
        climate_path = root / "external_processed_8k/koppen_geiger_1991_2020_8192x4096.tif"
        climate_layer = ClimateRasterLayer(climate_path, grid_lock) if climate_path.exists() else None
        return cls(
            dem_registry=DEMRegistry.from_source_cache(root),
            grid_lock=grid_lock,
            ocean_kernel=DEMOceanTruthKernel(),
            climate_layer=climate_layer,
        )

    def _blend_dem(self, lon: float, lat: float, synthetic_elev: float) -> float:
        """Return blended elevation when hybrid mode is active and a grounding provider exists."""
        if (
            self.signal_blend_mode != "hybrid"
            or self._grounding_provider is None
        ):
            return synthetic_elev
        grounding_elev = float(self._grounding_provider.get_dem(lon, lat))
        return _SYNTHETIC_WEIGHT * synthetic_elev + _GROUNDING_WEIGHT * grounding_elev

    def _blend_climate(self, lon: float, lat: float, synthetic_climate) -> Optional[int]:
        """Return blended climate class. Grounding only fills when synthetic has no class."""
        if (
            self.signal_blend_mode != "hybrid"
            or self._grounding_provider is None
            or synthetic_climate is not None
        ):
            return synthetic_climate
        return self._grounding_provider.get_climate(lon, lat)

    def query_point(self, lon: float, lat: float) -> SpatialState:
        """Return full semantic state at a point.

        Priority chain (highest to lowest):
          1. real_world_provider — real Earth data with built-in safe fallback
          2. signal_provider     — synthetic / stub / Stage 2 hybrid blend
          3. dem_registry        — legacy real-data path via DEM registry
        """

        if self._real_world_provider is not None:
            # Stage 3 path: real Earth data, fully wrapped with fallback inside provider.
            elevation    = float(self._real_world_provider.get_dem(lon, lat))
            ocean        = bool(self._real_world_provider.get_ocean(lon, lat))
            climate_class = self._real_world_provider.get_climate(lon, lat)
            ocean_rule   = "real_world_provider"
            if ocean and climate_class is not None and climate_class > 0:
                ocean = False
                ocean_rule = "real_world_provider overridden by climate land class"
        elif self._signal_provider is not None:
            # Stage 2 provider path: synthetic / stub / hybrid blend.
            # No DEM registry or climate layer is consulted.
            synthetic_elev = float(self._signal_provider.get_dem(lon, lat))
            elevation      = self._blend_dem(lon, lat, synthetic_elev)
            ocean          = bool(self._signal_provider.get_ocean(lon, lat))
            climate_class  = self._blend_climate(
                lon, lat, self._signal_provider.get_climate(lon, lat)
            )
            ocean_rule   = (
                "signal_provider+hybrid_blend"
                if self.signal_blend_mode == "hybrid"
                else "signal_provider"
            )
        else:
            # Original synthetic/real-data path — behavior is identical to
            # the pre-provider version of this method.
            elevation = self.dem_registry.query(lon, lat)
            ocean = self.ocean_kernel.classify(elevation)
            climate_class = self.climate_layer.get_value(lon, lat) if self.climate_layer else None

            # Köppen climate veto: classes 1–30 are only assigned to land pixels.
            # If the climate layer returns a valid land class, the pixel cannot be
            # ocean regardless of DEM sign. This handles below-sea-level land
            # (Dead Sea ~−430 m, Caspian Depression, Death Valley, etc.).
            ocean_rule = "DEM < 0"
            if ocean and climate_class is not None and climate_class > 0:
                ocean = False
                ocean_rule = "DEM < 0 overridden by Köppen land class"

        slope_proxy = self._slope_proxy(lon, lat)
        feature_vector = self.feature_composer.compose(elevation, ocean, climate_class, slope_proxy)
        normalized_vector = self.feature_composer.normalize(feature_vector)
        biome_proxy = self.feature_composer.biome_proxy(elevation, ocean, climate_class)
        return SpatialState(
            elevation=float(elevation) if elevation is not None else 0.0,
            ocean=ocean,
            climate_class=climate_class,
            biome_proxy=biome_proxy,
            slope_proxy=slope_proxy,
            feature_vector=feature_vector,
            normalized_vector=normalized_vector,
            source={
                "dem_priority": "Copernicus(land) -> GEBCO(ocean) -> ETOPO1(fallback)",
                "ocean_rule": ocean_rule,
                "climate_grid_locked": self.climate_layer is not None,
            },
        )

    def query_window(self, bbox: BBox, samples_per_axis: int = 8) -> WindowState:
        """Return aggregated semantic features using in-memory point samples."""

        west, south, east, north = bbox
        if east <= west or north <= south:
            raise ValueError("bbox must be (west, south, east, north)")
        lons = np.linspace(west, east, samples_per_axis)
        lats = np.linspace(south, north, samples_per_axis)
        states = [self.query_point(float(lon), float(lat)) for lat in lats for lon in lons]
        elevations = [state.elevation for state in states]
        ocean_flags = [state.ocean for state in states]
        climates = Counter(state.climate_class for state in states if state.climate_class is not None)
        metrics = self.consistency_metrics([(float(lon), float(lat)) for lat in lats for lon in lons])
        return WindowState(
            bbox=bbox,
            sample_count=len(states),
            ocean_fraction=sum(ocean_flags) / len(ocean_flags),
            mean_elevation=float(np.mean(elevations)),
            min_elevation=float(np.min(elevations)),
            max_elevation=float(np.max(elevations)),
            climate_histogram=dict(climates),
            consistency_score=metrics["consistency_score"],
        )

    def compute_feature_vector(self, lon: float, lat: float) -> FeatureVector:
        """Return fused feature vector [elevation, ocean_flag, climate_class, slope_proxy]."""

        return self.query_point(lon, lat).feature_vector

    def consistency_metrics(self, points: Optional[Iterable[Tuple[float, float]]] = None) -> Dict[str, float]:
        sample_points = list(points) if points is not None else _default_metric_points()
        states = [self.query_point(lon, lat) for lon, lat in sample_points]
        ocean_conflicts = [
            state for state in states
            if (state.ocean and state.elevation >= 0)
            or (
                (not state.ocean)
                and state.elevation < 0
                # Köppen veto is valid: below-sea-level land with a real climate
                # class is correct semantics, not a conflict.
                and not (state.climate_class is not None and state.climate_class > 0)
            )
        ]
        climate_elevation_conflicts = [
            state
            for state in states
            if state.climate_class in {1, 2, 3} and state.elevation > 3500
        ]
        boundary_conflicts = self._boundary_conflicts(sample_points)
        conflict_count = len(ocean_conflicts) + len(climate_elevation_conflicts) + boundary_conflicts
        total_checks = len(states) * 3
        ocean_conflict_rate = len(ocean_conflicts) / len(states) if states else 0.0
        consistency_score = 1.0 - (conflict_count / total_checks if total_checks else 0.0)
        vectors = np.array([state.normalized_vector.as_list() for state in states], dtype=float)
        finite_ratio = float(np.isfinite(vectors).sum() / vectors.size) if vectors.size else 1.0
        bounded_ratio = float(((vectors >= 0.0) & (vectors <= 1.0)).sum() / vectors.size) if vectors.size else 1.0
        return {
            "consistency_score": round(consistency_score, 6),
            "ocean_conflict_rate": round(ocean_conflict_rate, 6),
            "feature_vector_stability": round(min(finite_ratio, bounded_ratio), 6),
            "sample_count": float(len(states)),
            "boundary_conflict_count": float(boundary_conflicts),
            "climate_elevation_conflict_count": float(len(climate_elevation_conflicts)),
        }

    def _slope_proxy(self, lon: float, lat: float) -> float:
        if self.dem_registry is None:
            return 0.0
        delta = self.grid_lock.pixel_x
        center = self.dem_registry.query(lon, lat)
        east = self.dem_registry.query(lon + delta, lat)
        north = self.dem_registry.query(lon, lat + delta)
        if center is None or east is None or north is None:
            return 0.0
        return float(max(abs(east - center), abs(north - center)))

    def _boundary_conflicts(self, points: Iterable[Tuple[float, float]]) -> int:
        if self.dem_registry is None:
            return 0
        conflicts = 0
        delta = self.grid_lock.pixel_x
        for lon, lat in points:
            state = self.query_point(lon, lat)
            neighbors = [
                self.ocean_kernel.classify(self.dem_registry.query(lon + delta, lat)),
                self.ocean_kernel.classify(self.dem_registry.query(lon - delta, lat)),
                self.ocean_kernel.classify(self.dem_registry.query(lon, lat + delta)),
                self.ocean_kernel.classify(self.dem_registry.query(lon, lat - delta)),
            ]
            if state.ocean and any(not value for value in neighbors) and abs(state.elevation) > 200:
                conflicts += 1
            if (not state.ocean) and any(value for value in neighbors) and abs(state.elevation) > 200:
                conflicts += 1
        return conflicts


def _default_metric_points() -> list[Tuple[float, float]]:
    return [
        (0.0, 0.0),
        (120.0, 30.0),
        (-60.0, -20.0),
        (-150.0, 30.0),
        (86.925, 27.988),
        (-122.4, 37.8),
        (140.0, -35.0),
        (30.0, 10.0),
        (-70.0, -20.0),
        (10.0, 50.0),
    ]
