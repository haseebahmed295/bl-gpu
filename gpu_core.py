"""
Legacy module compatibility for blgpu.gpu_core.
All core classes now live in blgpu.core.
"""
from .blgpu.core import (
    HAS_ENGINE,
    my_engine,
    GpuDrawManager,
    GpuCanvas,
    GpuManager,
    default_manager,
    default_canvas,
    panel_widgets,
    create_event_handler_class,
    EventHandler,
)

__all__ = [
    "HAS_ENGINE",
    "my_engine",
    "GpuDrawManager",
    "GpuCanvas",
    "GpuManager",
    "default_manager",
    "default_canvas",
    "panel_widgets",
    "create_event_handler_class",
    "EventHandler",
]