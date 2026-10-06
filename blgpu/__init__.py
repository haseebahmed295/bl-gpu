"""
blgpu - High-Performance GPU UI Framework for Blender N-Panels

A lightweight, hardware-accelerated UI framework allowing Blender addon
developers to embed rich interactive 2D controls directly into sidebar panels.
"""

# Core framework engine
from .core import (
    GpuManager,
    GpuCanvas,
    GpuDrawManager,
    HAS_ENGINE,
    my_engine,
)

# 20+ GPU widgets
from .widgets import (
    UIElement,
    UIButton,
    UILabel,
    UISlider,
    UICheckbox,
    UIColorPicker,
    UITextBox,
    UIDropdown,
    UIColumn,
    UIRow,
    UIIcon,
    UICurveEditor,
    UIGradientRamp,
    UIVectorPad,
    UIRangeSlider,
    UIRadialKnob,
    UIColorWheel,
    UIOrbitSphere,
    UITimelineScrubber,
    UIMiniNodeGraph,
    UIWaveformView,
    UITransformBox,
    UIImageInspector,
    GpuShapes,
)

__version__ = "1.0.0"
__all__ = [
    # Core
    "GpuManager",
    "GpuCanvas",
    "GpuDrawManager",
    "HAS_ENGINE",
    "my_engine",
    # Base & Helpers
    "UIElement",
    "GpuShapes",
    # Basic Controls
    "UIButton",
    "UILabel",
    "UISlider",
    "UICheckbox",
    "UIDropdown",
    # Input & Color
    "UITextBox",
    "UIColorPicker",
    "UIColorWheel",
    "UIGradientRamp",
    # Advanced Controls & Visualizers
    "UICurveEditor",
    "UIVectorPad",
    "UIRangeSlider",
    "UIRadialKnob",
    "UIOrbitSphere",
    "UITimelineScrubber",
    "UIMiniNodeGraph",
    "UIWaveformView",
    "UITransformBox",
    "UIImageInspector",
    "UIIcon",
    # Layout Containers
    "UIColumn",
    "UIRow",
]
