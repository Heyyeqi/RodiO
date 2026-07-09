"""GPU texture residency budget for production Earth rendering.

The manager is intentionally renderer-agnostic: it tracks logical texture
payloads, estimated GPU bytes, LOD, and LRU state without copying image data.
Actual WebGL upload is handled by the frontend runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextureRecord:
    """Resident texture metadata tracked by GPUTextureManager."""

    texture_id: str
    lod: str
    texture: Any
    memory_bytes: int
    frame_last_used: int
    metadata: dict = field(default_factory=dict)


class GPUTextureManager:
    """Bounded LRU registry for logical GPU texture residency."""

    def __init__(self, max_memory_mb: int = 2048):
        if max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        self.max_memory_mb = int(max_memory_mb)
        self.loaded_textures: dict[str, TextureRecord] = {}
        self._frame_counter = 0

    @property
    def max_memory_bytes(self) -> int:
        return self.max_memory_mb * 1024 * 1024

    @property
    def current_memory_bytes(self) -> int:
        return sum(record.memory_bytes for record in self.loaded_textures.values())

    def load_texture_lod(
        self,
        texture_id: str,
        lod: str,
        texture,
        *,
        memory_bytes: int | None = None,
        metadata: dict | None = None,
    ) -> TextureRecord:
        """Register a texture LOD and evict old entries until within budget.

        ``texture`` is stored by reference; this method never duplicates arrays
        or image buffers.
        """
        if not texture_id:
            raise ValueError("texture_id must be non-empty")
        if not lod:
            raise ValueError("lod must be non-empty")

        self._frame_counter += 1
        key = self._key(texture_id, lod)
        existing = self.loaded_textures.get(key)
        if existing is not None and existing.texture is texture:
            existing.frame_last_used = self._frame_counter
            if metadata:
                existing.metadata.update(metadata)
            return existing

        record = TextureRecord(
            texture_id=texture_id,
            lod=lod,
            texture=texture,
            memory_bytes=int(memory_bytes if memory_bytes is not None else _estimate_texture_bytes(texture)),
            frame_last_used=self._frame_counter,
            metadata=dict(metadata or {}),
        )
        self.loaded_textures[key] = record
        self.evict_unused_textures()
        return record

    def touch(self, texture_id: str, lod: str) -> bool:
        """Mark a resident texture as recently used."""
        key = self._key(texture_id, lod)
        record = self.loaded_textures.get(key)
        if record is None:
            return False
        self._frame_counter += 1
        record.frame_last_used = self._frame_counter
        return True

    def evict_unused_textures(self) -> list[str]:
        """Evict least-recently-used textures until memory is within budget."""
        evicted: list[str] = []
        while self.current_memory_bytes > self.max_memory_bytes and self.loaded_textures:
            key, _record = min(
                self.loaded_textures.items(),
                key=lambda item: item[1].frame_last_used,
            )
            del self.loaded_textures[key]
            evicted.append(key)
        return evicted

    def memory_pressure_check(self) -> dict:
        """Return current budget pressure and a deterministic recommendation."""
        used = self.current_memory_bytes
        ratio = used / self.max_memory_bytes if self.max_memory_bytes else 1.0
        if ratio >= 1.0:
            level = "critical"
            recommended_lod = "4k"
        elif ratio >= 0.85:
            level = "high"
            recommended_lod = "8k"
        elif ratio >= 0.65:
            level = "moderate"
            recommended_lod = "16k"
        else:
            level = "normal"
            recommended_lod = "native"
        return {
            "used_mb": round(used / (1024 * 1024), 3),
            "max_mb": self.max_memory_mb,
            "usage_ratio": round(ratio, 6),
            "pressure": level,
            "over_budget": used > self.max_memory_bytes,
            "recommended_lod": recommended_lod,
            "resident_textures": len(self.loaded_textures),
        }

    @staticmethod
    def _key(texture_id: str, lod: str) -> str:
        return f"{texture_id}:{lod}"


def _estimate_texture_bytes(texture) -> int:
    """Best-effort byte estimate for numpy arrays and image-like objects."""
    nbytes = getattr(texture, "nbytes", None)
    if nbytes is not None:
        return int(nbytes)
    size = getattr(texture, "size", None)
    if isinstance(size, tuple) and len(size) == 2:
        width, height = size
        return int(width) * int(height) * 4
    width = getattr(texture, "width", None)
    height = getattr(texture, "height", None)
    if width is not None and height is not None:
        return int(width) * int(height) * 4
    try:
        return len(texture)
    except TypeError:
        return 0
