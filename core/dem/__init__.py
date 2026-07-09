"""Canonical DEM interface layer for RodiO geospatial source rasters."""

from .copernicus_adapter import CopernicusDEMAdapter
from .dem_interface import DEMInterface, DEMRegistry, DEMWindow
from .etopo_adapter import ETOPO1Adapter
from .gebco_adapter import GEBCOAdapter

__all__ = [
    "CopernicusDEMAdapter",
    "DEMInterface",
    "DEMRegistry",
    "DEMWindow",
    "ETOPO1Adapter",
    "GEBCOAdapter",
]
