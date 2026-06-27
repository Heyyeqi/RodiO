"""
core/binding — SAL → D6 Rendering Binding Layer

Public surface:
    SALD6Bridge             — top-level entry point
    D6RenderInput           — standardized render input type
    TemporalState           — time/climate context
    SemanticToVisualMapper  — class → color mapping
    UncertaintyVisualizer   — entropy → visual degradation
    RenderingContextBuilder — full context assembly
"""

from .sal_d6_bridge import SALD6Bridge
from .binding_types import D6RenderInput, TemporalState, ColorVector, VisualAdjustment
from .semantic_to_visual_mapper import SemanticToVisualMapper
from .uncertainty_visualizer import UncertaintyVisualizer
from .rendering_context_builder import RenderingContextBuilder

__all__ = [
    "SALD6Bridge",
    "D6RenderInput",
    "TemporalState",
    "ColorVector",
    "VisualAdjustment",
    "SemanticToVisualMapper",
    "UncertaintyVisualizer",
    "RenderingContextBuilder",
]
