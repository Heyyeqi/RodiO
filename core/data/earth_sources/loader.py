"""
EarthDataLoader — lazy, memory-efficient loader for real Earth data layers.

Layer catalogue:
    "dem"       — ETOPO1 / Copernicus priority DEM (via DEMRegistry)
    "ocean"     — GEBCO sub-ice bathymetry (via GEBCOAdapter)
    "landcover" — MODIS / ESA landcover (via RasterIndexer, when present)
    "climate"   — Köppen-Geiger 1991-2020 (via ClimateRasterLayer / RasterIndexer)

All layers are lazy: no data is read until load_layer() is called.
load_layer() returns None when the underlying file does not exist, allowing
RealWorldSignalProvider to fall back to synthetic values gracefully.

Directory layout assumed under source_root:
    dem/
        exported_8k/etopo1_bedrock_8192x4096.tif
        exported_8k/copernicus_dem_glo30_elevation_8192x4096.tif
        external_raw/gebco/gebco_2026_sub_ice_topo_geotiff/   (tile dir)
    landcover/
        <any single-band GeoTIFF>
    climate/
        external_processed_8k/koppen_geiger_1991_2020_8192x4096.tif
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


_LAYER_NAMES = frozenset({"dem", "ocean", "landcover", "climate"})


class EarthDataLoader:
    """
    Lazy loader that maps layer names to the appropriate adapter / indexer.

    Args:
        source_root: root directory that contains dem/, landcover/, climate/ sub-dirs.
                     Defaults to the project-level "cache/" directory if omitted.
    """

    def __init__(
        self,
        source_root: Optional[str | Path] = None,
        resolution_mode: str = "8k",
    ) -> None:
        if source_root is None:
            # GEE source cache: contains exported_8k/, external_raw/, external_processed_8k/
            self.source_root = Path(__file__).parents[3] / "d5b_processor_v3/source_cache/gee_global"
        else:
            self.source_root = Path(source_root)
        self.resolution_mode = resolution_mode
        self._cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_layer(self, name: str) -> Optional[Any]:
        """
        Return the loaded layer object for the given name, or None if unavailable.

        The return type varies by layer:
            "dem"       → DEMRegistry (has .query(lon, lat) → Optional[int])
            "ocean"     → GEBCOAdapter (has .get_value(lon, lat) → Optional[int])
            "landcover" → RasterIndexer (has .sample(lon, lat) → Optional[int])
            "climate"   → object with .get_value(lon, lat) → Optional[int]

        Returns None when the underlying data file does not exist.
        """
        if name not in _LAYER_NAMES:
            raise ValueError(f"Unknown layer {name!r}. Known: {sorted(_LAYER_NAMES)}")
        if name in self._cache:
            return self._cache[name]
        loader = getattr(self, f"_load_{name}")
        result = loader()
        self._cache[name] = result
        return result

    def set_resolution(self, mode: str) -> None:
        """Set resolution mode for future RasterIndexer-backed layers."""
        if mode not in {"8k", "21k"}:
            raise ValueError(f"resolution mode must be '8k' or '21k', got {mode!r}")
        if mode != self.resolution_mode:
            self._cache.clear()
        self.resolution_mode = mode

    # ------------------------------------------------------------------
    # Layer loaders
    # ------------------------------------------------------------------

    def _load_dem(self) -> Optional[Any]:
        try:
            from core.dem import DEMRegistry
            return DEMRegistry.from_source_cache(self.source_root)
        except (FileNotFoundError, Exception):
            return None

    def _load_ocean(self) -> Optional[Any]:
        tile_dir = self.source_root / "external_raw/gebco/gebco_2026_sub_ice_topo_geotiff"
        if not tile_dir.exists():
            return None
        try:
            from core.dem import GEBCOAdapter
            return GEBCOAdapter(tile_dir)
        except Exception:
            return None

    def _load_landcover(self) -> Optional[Any]:
        from core.signal.raster_indexer import RasterIndexer
        candidates = list(self.source_root.glob("landcover/**/*.tif"))
        if not candidates:
            return None
        try:
            return RasterIndexer(candidates[0], resolution_mode=self.resolution_mode)
        except Exception:
            return None

    def _load_climate(self) -> Optional[Any]:
        from core.signal.raster_indexer import RasterIndexer
        candidate = self.source_root / "external_processed_8k/koppen_geiger_1991_2020_8192x4096.tif"
        if not candidate.exists():
            return None
        try:
            return RasterIndexer(candidate, nodata=0, resolution_mode=self.resolution_mode)
        except Exception:
            return None
