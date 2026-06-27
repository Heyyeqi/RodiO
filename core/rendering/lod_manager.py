"""Deterministic LOD selection for Earth visual textures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class LODManager:
    """Select safe render texture sizes from logical source resolution."""

    capability_map: Dict[str, int] = field(default_factory=lambda: {
        "high": 16384,
        "medium": 8192,
        "low": 4096,
    })
    asset_registry: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "bmng_topo_bathy": {
            "logical_21k": "/assets/earth/bmng21k/topo_bathy/21600x10800_jpeg_preview/world.topo.bathy.200408.3x21600x10800_geo.jpg",
            "canonical_16k": "/assets/earth/bmng21k/topo_bathy/lod/world.topo.bathy.200408.16384x8192.jpg",
            "fallback_8k": "/assets/earth/candidates/d6_topo_blend_8192x4096.jpg",
            "fallback_4k": "/assets/earth_day_8k.jpg",
        },
        "bmng_base_map": {
            "logical_21k": "/assets/earth/bmng21k/base_map/21600x10800_jpeg_preview/world.200407.3x21600x10800_geo.jpg",
            "canonical_16k": "/assets/earth/bmng21k/base_map/lod/world.base_map.16384x8192.jpg",
            "fallback_8k": "/assets/earth/production/d5z_b_8192x4096.jpg",
            "fallback_4k": "/assets/earth_day_8k.jpg",
        },
    })

    def select_render_resolution(
        self,
        source_resolution: str | Tuple[int, int],
        capability: str = "high",
        max_texture_size: int | None = None,
    ) -> Tuple[int, int]:
        """Return safe equirectangular (width, height) render resolution."""
        source_w, source_h = _parse_resolution(source_resolution)
        cap = self._capability_limit(capability, max_texture_size)
        width = min(source_w, cap)
        # Preserve 2:1 equirectangular shape and never exceed source height.
        height = min(source_h, max(1, width // 2))
        return width, height

    def fallback_chain(
        self,
        source_resolution: str | Tuple[int, int] = (21600, 10800),
        capability: str = "high",
        max_texture_size: int | None = None,
    ) -> list[Tuple[int, int]]:
        """Return deterministic fallback chain from best safe LOD downward."""
        selected = self.select_render_resolution(source_resolution, capability, max_texture_size)
        candidates = [
            (16384, 8192),
            (8192, 4096),
            (4096, 2048),
        ]
        chain = [c for c in candidates if c[0] <= selected[0]]
        if selected not in chain:
            chain.insert(0, selected)
        return chain

    def _capability_limit(self, capability: str, max_texture_size: int | None) -> int:
        if capability not in self.capability_map:
            raise ValueError(
                f"Unknown LOD capability {capability!r}; expected one of {sorted(self.capability_map)}"
            )
        limit = self.capability_map[capability]
        if max_texture_size is not None:
            limit = min(limit, int(max_texture_size))
        return int(limit)


def _parse_resolution(value: str | Tuple[int, int]) -> Tuple[int, int]:
    if isinstance(value, tuple):
        if len(value) != 2:
            raise ValueError(f"resolution tuple must be (width, height), got {value!r}")
        return int(value[0]), int(value[1])
    if isinstance(value, str):
        parts = value.lower().split("x")
        if len(parts) != 2:
            raise ValueError(f"resolution string must be 'WxH', got {value!r}")
        return int(parts[0]), int(parts[1])
    raise TypeError(f"Unsupported resolution type {type(value).__name__}")
