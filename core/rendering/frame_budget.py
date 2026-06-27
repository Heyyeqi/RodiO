"""Frame-time budget controller for production rendering."""

from __future__ import annotations

from dataclasses import dataclass, field


LOD_ORDER = ("16k", "8k", "4k")


@dataclass
class FrameBudgetController:
    """Track frame time and recommend deterministic LOD fallback."""

    max_frame_time_ms: float = 16.0
    current_lod: str = "16k"
    frame_times: list[float] = field(default_factory=list)
    fallback_triggered: bool = False

    def record_frame_time(self, frame_time_ms: float) -> dict:
        if frame_time_ms < 0:
            raise ValueError("frame_time_ms must be non-negative")
        self.frame_times.append(float(frame_time_ms))
        if frame_time_ms > self.max_frame_time_ms:
            self.current_lod = self.fallback_lod(self.current_lod)
            self.fallback_triggered = True
        return self.status()

    def fallback_lod(self, lod: str | None = None) -> str:
        lod = lod or self.current_lod
        if lod not in LOD_ORDER:
            return "8k"
        idx = LOD_ORDER.index(lod)
        return LOD_ORDER[min(idx + 1, len(LOD_ORDER) - 1)]

    def recommend_tile_resolution(self) -> int:
        if self.current_lod == "16k":
            return 4096
        if self.current_lod == "8k":
            return 2048
        return 1024

    def should_reduce_resolution(self) -> bool:
        return bool(self.frame_times and self.frame_times[-1] > self.max_frame_time_ms)

    def status(self) -> dict:
        avg = sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0.0
        last = self.frame_times[-1] if self.frame_times else 0.0
        return {
            "max_frame_time_ms": self.max_frame_time_ms,
            "last_frame_time_ms": round(last, 4),
            "average_frame_time_ms": round(avg, 4),
            "current_lod": self.current_lod,
            "tile_resolution": self.recommend_tile_resolution(),
            "fallback_triggered": self.fallback_triggered,
            "over_budget": last > self.max_frame_time_ms,
        }
