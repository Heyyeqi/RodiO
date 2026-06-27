"""
SignalFlags — feature-flag gate for Stage 2 grounding injection.

All grounding providers are off by default. Set flags to True at
application startup to enable hybrid mode incrementally.

Rules:
    - ENABLE_HYBRID_MODE requires at least one grounding flag to be active
    - Flags are read at query time, not at construction time, so toggling
      mid-session takes effect immediately
    - SAL / M1 / VC logic must never change based on flag state —
      only the raw input values flowing into the pipeline change
"""


class SignalFlags:
    ENABLE_DEM_GROUNDING: bool = False
    ENABLE_CLIMATE_GROUNDING: bool = False
    ENABLE_HYBRID_MODE: bool = False
