"""
Legacy module compatibility for blgpu.event_handler.
All event handling classes now live in blgpu.core.event_handler.
"""
from .blgpu.core.event_handler import (
    MODEL_TIMER_INTERVAL,
    create_event_handler_class,
    EventHandler,
)

__all__ = [
    "MODEL_TIMER_INTERVAL",
    "create_event_handler_class",
    "EventHandler",
]