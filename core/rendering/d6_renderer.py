"""D6 Scientific Renderer — per-point and windowed CPU rendering.

Entry point for the RodiO semantic → RGB pipeline:

    SpatialState (from M0 SpatialRuntime)
    + TimeState
    → RGB

No raster files are written. render_window returns an in-memory numpy array.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from core.runtime import SpatialProfile
from core.runtime.runtime_types import SpatialState

from .color_model import ColorModel
from .d6_texture_baker import D6TextureBaker
from .frame_budget import FrameBudgetController
from .gpu_texture_manager import GPUTextureManager
from .light_model import LightModel
from .lod_manager import LODManager
from .renderer_types import RGB, DayCycleState, LightState, SeasonalState, TimeState
from .temporal_model import TemporalModel
from .texture_streaming import TextureStreamingLayer
from .visual_grammar import VisualGrammar
from .visual_rule_resolver import PixelContext, VisualRuleResolver
from .visual_weight_harmonizer import VisualWeightHarmonizer


class D6Renderer:

    def __init__(
        self,
        spatial_runtime,
        resolution_mode: Optional[str] = None,
        enable_explainability: bool = False,
        enable_temporal_stability: bool = False,
        max_gpu_memory_mb: int = 2048,
        enable_texture_streaming: bool = True,
        frame_budget_ms: float = 16.0,
    ):
        self.runtime = spatial_runtime
        self.resolution_mode = resolution_mode or getattr(spatial_runtime, "resolution_mode", "8k")
        self.temporal = TemporalModel()
        self.light_model = LightModel()
        self.color_model = ColorModel()
        self.lod_manager = LODManager()
        self.canonical_render_resolution = self.lod_manager.select_render_resolution(
            self.profile_resolution()
        )
        self.texture_baker = D6TextureBaker(self.resolution_mode)
        self.visual_grammar = VisualGrammar()
        self.rule_resolver = VisualRuleResolver(debug=enable_explainability)
        self.harmonizer = VisualWeightHarmonizer()
        self.gpu_texture_manager = GPUTextureManager(max_memory_mb=max_gpu_memory_mb)
        self.texture_streaming = TextureStreamingLayer() if enable_texture_streaming else None
        self.frame_budget = FrameBudgetController(max_frame_time_ms=frame_budget_ms)
        self._explainability_enabled = enable_explainability
        self._temporal_stability_enabled = enable_temporal_stability
        self._texture_streaming_enabled = enable_texture_streaming
        self._last_streamed_tiles = {}
        if enable_temporal_stability:
            from .visual_stability_engine import VisualStabilityEngine
            self._stability_engine = VisualStabilityEngine()
            self.rule_resolver.set_stability_engine(self._stability_engine)
        else:
            self._stability_engine = None

    def set_resolution(self, mode: str) -> None:
        """Set render sampling profile. Does not change colour/shader logic."""
        SpatialProfile().get_resolution(mode)
        self.resolution_mode = mode
        self.canonical_render_resolution = self.lod_manager.select_render_resolution(
            self.profile_resolution()
        )
        self.texture_baker = D6TextureBaker(mode)
        self.frame_budget.current_lod = _lod_label(self.canonical_render_resolution[0])

    # ── Explainability API ─────────────────────────────────────────────────────

    def get_render_metadata(self) -> dict:
        """Return accumulated resolver traces and explainability state.

        Only call after one or more render_point() invocations.
        When enable_explainability=False (default), visual_traces is always [].
        Pixel output is not affected by this call.
        """
        return {
            "resolver_enabled": self._explainability_enabled,
            "visual_traces": self.rule_resolver.get_debug_traces(),
            "production_optimization": self.get_production_metadata(),
        }

    def clear_render_metadata(self) -> None:
        """Discard accumulated traces.  No-op when explainability is disabled."""
        self.rule_resolver.clear_traces()
        self._last_streamed_tiles = {}

    # ── Production optimization API ───────────────────────────────────────────

    def get_production_metadata(self) -> dict:
        """Return resource-control state without affecting visual output."""
        return {
            "gpu_memory": self.gpu_texture_manager.memory_pressure_check(),
            "texture_streaming_enabled": self._texture_streaming_enabled,
            "streamed_tile_count": len(self._last_streamed_tiles),
            "streamed_tiles": [
                {"x": tile.x, "y": tile.y, "lod": tile.lod}
                for tile in sorted(self._last_streamed_tiles)
            ],
            "frame_budget": self.frame_budget.status(),
            "pipeline": "LOD -> TileStream -> GPUManager -> Render",
            "decision_core": "VisualRuleResolver(stability_embedded)",
        }

    def record_frame_time(self, frame_time_ms: float) -> dict:
        """Update frame budget state and return the current recommendation."""
        return self.frame_budget.record_frame_time(frame_time_ms)

    def prepare_texture_stream(self, texture: np.ndarray, camera_state=None) -> dict:
        """Register a texture and lazily expose visible tile views.

        This is a resource-management step only.  It does not resample or mutate
        texture pixels, preserving Stage 9 visual correctness.
        """
        arr = np.asarray(texture)
        if arr.ndim != 3:
            raise ValueError("texture must be an image array shaped (H, W, C)")
        lod = _lod_label(arr.shape[1])
        full_texture_bytes = 0 if self.texture_streaming is not None else arr.nbytes
        self.gpu_texture_manager.load_texture_lod(
            "earth_day",
            lod,
            arr,
            memory_bytes=full_texture_bytes,
            metadata={
                "shape": arr.shape,
                "source": "renderer",
                "logical_only": self.texture_streaming is not None,
            },
        )
        if self.texture_streaming is None:
            self._last_streamed_tiles = {}
            return {}
        state = dict(camera_state or {})
        state.setdefault("lod", lod)
        self._last_streamed_tiles = self.texture_streaming.lazy_load_tiles(arr, state)
        for tile, view in self._last_streamed_tiles.items():
            self.gpu_texture_manager.load_texture_lod(
                f"earth_day_tile_{tile.x}_{tile.y}",
                tile.lod,
                view,
                memory_bytes=view.nbytes,
                metadata={"tile": (tile.x, tile.y), "view": True},
            )
        return self._last_streamed_tiles

    # ── Temporal stability lifecycle ───────────────────────────────────────────

    def begin_frame(self, frame_id: int = 0) -> None:
        """Open a new render frame for temporal stability tracking.

        Call before rendering a batch of pixels that belong to the same animation
        frame.  No-op when enable_temporal_stability=False (default).
        """
        if self._temporal_stability_enabled and self._stability_engine is not None:
            self._stability_engine.begin_frame(frame_id)

    def end_frame(self, frame_id: int = 0) -> None:
        """Close the current render frame for temporal stability tracking.

        Call after all pixels for the frame have been rendered.  No-op when
        enable_temporal_stability=False (default).
        """
        if self._temporal_stability_enabled and self._stability_engine is not None:
            self._stability_engine.end_frame(frame_id)
        self.rule_resolver.clear_traces()

    def profile_resolution(self) -> tuple[int, int]:
        """Return full raster profile (width, height) used for sampling interpretation."""
        return SpatialProfile().get_resolution(self.resolution_mode)

    def default_window_shape(self, base_px: int = 64) -> tuple[int, int]:
        """Return profile-scaled preview window shape (width, height)."""
        scale = SpatialProfile().scale(self.resolution_mode)
        size = max(1, int(round(base_px * scale)))
        return size, size

    # ── Public API ────────────────────────────────────────────────────────────

    def render_point(self, lon: float, lat: float, time_state: TimeState) -> RGB:
        """Return RGB colour at (lon, lat) for the given TimeState.

        Pipeline:
          1. query_point  → SpatialState
          2. sun position → SunState
          3. light build  → LightState
          4. season       → SeasonalState
          5. day cycle    → DayCycleState
          6. color model  → RGB (clamped)
        """
        state = self.runtime.query_point(lon, lat)
        return self._render_from_state(state, lon, lat, time_state)

    # Hard cap for render_window to prevent accidental 8K batch computation.
    # Pass allow_large=True only in explicit test contexts.
    _MAX_WINDOW_PIXELS: int = 512 * 512

    def render_window(
        self,
        bbox: tuple,
        time_state: TimeState,
        width: Optional[int] = None,
        height: Optional[int] = None,
        allow_large: bool = False,
        texture_bake: bool = False,
        bmng_base=None,
        bmng_topo=None,
    ) -> np.ndarray:
        """Return uint8 (height, width, 3) RGB array. No file output.

        bbox = (west, south, east, north).
        Default is profile-scaled from 64×64. Hard cap at 512×512 unless
        allow_large=True.
        """
        if texture_bake:
            if bmng_base is None or bmng_topo is None:
                if self.resolution_mode == "21k":
                    raise ValueError("texture_bake=True requires bmng_base and bmng_topo")
            else:
                return self.bake_textures(bmng_base, bmng_topo, time_state=time_state)

        if width is None or height is None:
            default_w, default_h = self.default_window_shape()
            width = default_w if width is None else width
            height = default_h if height is None else height
        if not allow_large and width * height > self._MAX_WINDOW_PIXELS:
            raise ValueError(
                f"render_window size {width}×{height} = {width * height} pixels exceeds "
                f"safety cap {self._MAX_WINDOW_PIXELS}. Pass allow_large=True to override."
            )
        west, south, east, north = bbox
        lons = np.linspace(west, east, width, endpoint=False)
        lats = np.linspace(north, south, height, endpoint=False)

        out = np.zeros((height, width, 3), dtype=np.uint8)
        for row_idx, lat in enumerate(lats):
            for col_idx, lon in enumerate(lons):
                rgb = self.render_point(float(lon), float(lat), time_state)
                r, g, b = rgb.to_uint8()
                out[row_idx, col_idx] = (r, g, b)
        return out

    def bake_textures(self, bmng_base, bmng_topo, time_state: Optional[TimeState] = None) -> dict:
        """Bake visual BMNG inputs into D6 texture outputs."""
        textures = self.texture_baker.bake(bmng_base, bmng_topo)
        sun_angle = 90.0 if time_state is None else self.visual_grammar.time_grammar.angle_from_hour(time_state.hour)
        textures["base_texture"] = self.visual_grammar.apply_to_texture(
            textures["base_texture"], sun_angle=sun_angle
        )
        textures["overlay_texture"] = self.visual_grammar.apply_to_texture(
            textures["overlay_texture"], sun_angle=sun_angle
        )
        # Step 3: VisualWeightHarmonizer — constrain grammar output to Noon Air spec
        textures["base_texture"] = self.harmonizer.harmonize_texture(textures["base_texture"])
        textures["overlay_texture"] = self.harmonizer.harmonize_texture(textures["overlay_texture"])
        self.prepare_texture_stream(textures["base_texture"], camera_state={"lon": 0.0, "lat": 0.0})
        textures["visual_grammar"] = {
            "name": "stage7",
            "sun_angle": round(float(sun_angle), 4),
        }
        textures["production_optimization"] = self.get_production_metadata()
        return textures

    def compute_semantic_color(self, state: SpatialState, light: LightState) -> RGB:
        """Map semantic state + pre-computed LightState → RGB.

        Used for batch pipelines where light is pre-computed once per scene.
        Temporal state is neutral (noon, midsummer).
        """
        neutral_season = SeasonalState(season_factor=0.65, snow_factor=0.0, vegetation_boost=0.3)
        neutral_cycle = DayCycleState(phase="noon", warmth=0.0, contrast=1.0, saturation=1.0, blue_bias=0.0)
        # Step 2: resolve visual rule conflicts
        candidates = self.visual_grammar.generate_rule_candidates(
            climate_class=state.climate_class,
            elevation=state.elevation,
            ocean=state.ocean,
            sun_angle=90.0,
        )
        ctx = PixelContext(
            climate_class=state.climate_class,
            elevation=state.elevation,
            ocean=state.ocean,
            biome_proxy=state.biome_proxy,
            sun_angle=90.0,
        )
        resolved = self.rule_resolver.resolve_conflicts(candidates, ctx)

        # Step 3: base colour uses resolved ocean flag
        rgb = self.color_model.final_color(
            biome_proxy=state.biome_proxy,
            ocean=resolved.ocean,
            light=light,
            season=neutral_season,
            day_cycle=neutral_cycle,
        )
        grammar_rgb = self.visual_grammar.apply_to_rgb(
            rgb,
            climate_class=state.climate_class,
            elevation=state.elevation,
            ocean=resolved.ocean,
            sun_angle=90.0,
        )
        # Step 4: harmonizer as pure constraint (classification from resolver)
        return self.harmonizer.harmonize(
            grammar_rgb,
            ocean=resolved.ocean,
            climate_family=resolved.climate_family,
            elevation=state.elevation,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _render_from_state(
        self, state: SpatialState, lon: float, lat: float, time_state: TimeState
    ) -> RGB:
        sun = self.temporal.get_sun_position(lat, lon, time_state)
        season = self.temporal.get_season_factor(lat, time_state.day_of_year)
        day_cycle = self.temporal.get_day_cycle(time_state.hour)
        light = self.light_model.build(sun.elevation, state.slope_proxy, state.ocean)

        # Step 2: VisualGrammar → rule candidates → VisualRuleResolver
        candidates = self.visual_grammar.generate_rule_candidates(
            climate_class=state.climate_class,
            elevation=state.elevation,
            ocean=state.ocean,
            sun_angle=sun.elevation,
        )
        ctx = PixelContext(
            climate_class=state.climate_class,
            elevation=state.elevation,
            ocean=state.ocean,
            biome_proxy=state.biome_proxy,
            sun_angle=sun.elevation,
        )
        resolved = self.rule_resolver.resolve_conflicts(candidates, ctx, pixel_key=(lon, lat))

        # Step 3: BMNG base colour (ocean flag from resolver)
        rgb = self.color_model.final_color(
            biome_proxy=state.biome_proxy,
            ocean=resolved.ocean,
            light=light,
            season=season,
            day_cycle=day_cycle,
        )
        grammar_rgb = self.visual_grammar.apply_to_rgb(
            rgb,
            climate_class=state.climate_class,
            elevation=state.elevation,
            ocean=resolved.ocean,
            sun_angle=sun.elevation,
        )
        # Step 4: VisualWeightHarmonizer — pure constraint, classification from resolver
        return self.harmonizer.harmonize(
            grammar_rgb,
            ocean=resolved.ocean,
            climate_family=resolved.climate_family,
            elevation=state.elevation,
            sun_angle=sun.elevation,
        )

    # ── Validation helpers ────────────────────────────────────────────────────

    def temporal_consistency_check(
        self,
        lon: float,
        lat: float,
        day_of_year: int = 180,
    ) -> dict:
        """Render the same point at 4 times and verify colour variation.

        Returns a dict of RGB values and variation metrics.
        """
        hours = {"morning": 7.0, "noon": 12.0, "sunset": 18.0, "night": 23.0}
        results = {}
        for label, hour in hours.items():
            ts = TimeState(hour=hour, day_of_year=day_of_year)
            rgb = self.render_point(lon, lat, ts)
            results[label] = {"rgb": rgb, "uint8": rgb.to_uint8(), "lum": rgb.luminance()}

        lums = [v["lum"] for v in results.values()]
        lum_range = max(lums) - min(lums)
        consistent = lum_range > 0.05  # must have meaningful diurnal variation

        return {
            "point": (lon, lat),
            "day_of_year": day_of_year,
            "per_time": results,
            "luminance_range": round(lum_range, 4),
            "diurnal_variation_ok": consistent,
        }

    def biome_stability_check(self, day_of_year: int = 180) -> dict:
        """Measure colour stability across 24 h for 3 representative biomes.

        Stability = inverse of mean RGB Euclidean distance across hours.
        Expected order (highest stability first): ocean → forest → desert.

        Ocean has high lum variation (sun reflection) but stable hue.
        Forest has consistent green across the day.
        Desert has strong diurnal amplitude (hot midday vs cold night tone).
        """
        biomes = {
            "tropical_forest": (20.0, -3.0),   # Equatorial, dense forest
            "sahara_desert":   (23.0, 25.0),    # Saharan core
            "south_pacific":   (180.0, -30.0),  # Open deep ocean
        }
        hours = np.linspace(6, 22, 8)
        results = {}

        for name, (lon, lat) in biomes.items():
            rgbs = []
            for h in hours:
                ts = TimeState(hour=float(h), day_of_year=day_of_year)
                rgb = self.render_point(lon, lat, ts)
                rgbs.append((rgb.r, rgb.g, rgb.b))

            arr = np.array(rgbs)
            mean_rgb = arr.mean(axis=0)
            dists = np.sqrt(((arr - mean_rgb) ** 2).sum(axis=1))
            stability = 1.0 - float(dists.mean())

            results[name] = {
                "lon_lat": (lon, lat),
                "mean_rgb": tuple(round(float(v), 3) for v in mean_rgb),
                "color_stability": round(stability, 4),
                "max_rgb_drift": round(float(dists.max()), 4),
            }

        return results


def _lod_label(width: int) -> str:
    if width >= 16000:
        return "16k"
    if width >= 8000:
        return "8k"
    if width >= 4000:
        return "4k"
    return f"{width}px"
