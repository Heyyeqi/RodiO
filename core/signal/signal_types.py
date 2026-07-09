"""
Signal Types — primitive type aliases for the signal provider interface.

These are the raw data values returned by a BaseSignalProvider before any
semantic interpretation by the SAL / M0 pipeline layers.
"""

from typing import Optional

# Raw DEM elevation in metres (positive = above sea level, negative = below)
DEMValue = float

# Integer landcover class code (provider-defined; 0 = unknown / no data)
LandcoverClass = int

# Optional Köppen-Geiger or equivalent climate class (None = no data)
ClimateClass = Optional[int]

# Boolean ocean flag (True = point is classified as ocean by the source)
OceanFlag = bool
