"""
RasterLayerRegistry — in-memory registry for pre-loaded Earth raster arrays.

Complements the file-based EarthDataLoader (core.data.earth_sources.loader).
Use when arrays arrive from external pipelines: GEE exports read into memory,
calibration harnesses, or test fixtures. No file I/O is performed here.

Each registered layer is stored as:
    {"array": np.ndarray (2D), "bbox": (min_lon, max_lon, min_lat, max_lat)}

For global equirectangular grids the bbox is always (-180, 180, -90, 90).
Downstream consumers (RasterIndexer, RasterBackedProvider) may ignore the bbox
and use the standard global formula, but the field is kept for provenance.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


_LAYER_NAMES: frozenset[str] = frozenset({"dem", "ocean", "climate", "landcover"})

BBox = Tuple[float, float, float, float]  # (min_lon, max_lon, min_lat, max_lat)

GLOBAL_BBOX: BBox = (-180.0, 180.0, -90.0, 90.0)


class RasterLayerRegistry:
    """
    In-memory registry that maps layer names to pre-loaded numpy arrays.

    Args:
        data_root: optional path hint for provenance / logging; not used for I/O.
    """

    def __init__(self, data_root: Optional[str] = None) -> None:
        self.data_root = data_root
        self._layers: Dict[str, Optional[Dict[str, Any]]] = {
            name: None for name in _LAYER_NAMES
        }

    # ------------------------------------------------------------------
    # Write side
    # ------------------------------------------------------------------

    def load_layer(self, name: str, array: np.ndarray, bbox: BBox = GLOBAL_BBOX) -> None:
        """
        Register a pre-loaded 2D numpy array as a named layer.

        Args:
            name:  one of "dem", "ocean", "climate", "landcover"
            array: 2D numpy array, global equirectangular (shape [H, W])
            bbox:  (min_lon, max_lon, min_lat, max_lat); defaults to global extent
        """
        if name not in _LAYER_NAMES:
            raise ValueError(f"Unknown layer {name!r}. Known: {sorted(_LAYER_NAMES)}")
        if not isinstance(array, np.ndarray):
            raise TypeError(f"array must be numpy.ndarray, got {type(array).__name__}")
        if array.ndim != 2:
            raise ValueError(f"Layer array must be 2-D, got shape {array.shape}")
        self._layers[name] = {"array": array, "bbox": bbox}

    def auto_register(self, file_loader, raster_decoder) -> List[str]:
        """
        Discover files through file_loader and register the first file per layer.

        The registry does not parse files directly. raster_decoder owns decoding
        and must return {"array": np.ndarray, "bbox": BBox}. Missing layers are
        skipped, preserving lazy file-to-array behavior at the decoder boundary.
        """
        files = file_loader.scan()
        registered: List[str] = []
        for layer, paths in files.items():
            if not paths:
                continue
            raster = raster_decoder.load(paths[0])
            self.load_layer(layer, raster["array"], raster["bbox"])
            registered.append(layer)
        return registered

    def bind_to_registry(self, registry) -> List[str]:
        """
        Bind loaded layers into an external registry-like object.

        The target must provide register(name, layer). This is intentionally
        small so downstream runtime registries can share the same layer payloads
        without copying arrays.
        """
        bound: List[str] = []
        for name in ("dem", "ocean", "climate"):
            layer = self._layers.get(name)
            if layer is None:
                continue
            registry.register(name, layer)
            bound.append(name)
        return bound

    # ------------------------------------------------------------------
    # Read side
    # ------------------------------------------------------------------

    def get_layer(self, name: str) -> Optional[Dict[str, Any]]:
        """Return {"array": ..., "bbox": ...} for the named layer, or None."""
        if name not in _LAYER_NAMES:
            raise ValueError(f"Unknown layer {name!r}. Known: {sorted(_LAYER_NAMES)}")
        return self._layers[name]

    def is_loaded(self, name: str) -> bool:
        """Return True if the named layer has been registered."""
        return self._layers.get(name) is not None

    def loaded_layers(self) -> List[str]:
        """Return names of all currently loaded layers, in consistent order."""
        return [n for n in sorted(_LAYER_NAMES) if self._layers[n] is not None]

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def to_indexers(
        self,
        nodata: Optional[int] = None,
        resolution_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a RasterIndexer for each loaded layer.

        Returns {layer_name: RasterIndexer} for loaded layers only.
        Uses RasterIndexer.from_array() — global equirectangular formula,
        no GDAL dependency.
        """
        from core.signal.raster_indexer import RasterIndexer

        return {
            name: RasterIndexer.from_array(
                layer["array"],
                nodata=nodata,
                resolution=layer["array"].shape[1],
                resolution_mode=resolution_mode,
            )
            for name, layer in self._layers.items()
            if layer is not None
        }
