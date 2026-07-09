"""
EarthFlags — feature-flag gate for Stage 3 real Earth data injection.

All real data layers are off by default. Enable flags incrementally once
corresponding data files are confirmed present and validated.

Rules:
    - Flags do not load data; they signal intent. Loading is lazy in RealWorldSignalProvider.
    - Disabling a flag after enabling does NOT unload in-memory data.
    - SAL / M1 / VC / D6 logic must never be conditioned on these flags —
      only the raw input values flowing into the pipeline change.
"""


class EarthFlags:
    ENABLE_REAL_DEM: bool = False
    ENABLE_REAL_OCEAN: bool = False
    ENABLE_REAL_CLIMATE: bool = False

    # Stage 3 Step 3 — per-source flags (aliases for the provider adapters above)
    ENABLE_GEBCO: bool = False
    ENABLE_ETOPO: bool = False
    ENABLE_KOPPEN: bool = False

    # Stage 3 Step 4 — binding layer capability flags
    # ENABLE_REAL_DATA: system is wired to accept real raster injection (always True)
    # ENABLE_FALLBACK:  safe-default fallback is active when layers are absent (always True)
    ENABLE_REAL_DATA: bool = True
    ENABLE_FALLBACK: bool = True
