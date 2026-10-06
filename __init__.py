bl_info = {
    "name": "Custom GPU Panel Engine",
    "author": "haseebahmed295",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > N-Panel > My Engine",
    "description": "High-performance GPU-accelerated UI framework for Blender N-Panels",
    "warning": "Requires custom my_engine binary",
    "category": "3D View",
}

import bpy

# 1. Export framework components and widgets from copyable .blgpu package
from .blgpu import (
    HAS_ENGINE,
    my_engine,
    GpuManager,
    GpuCanvas,
    GpuDrawManager,
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

# 3. Import demo showcase panel
from .demo import CUSTOM_PT_gpu_canvas, init_demo_widgets

# Standalone showcase instance when run as an addon
gpu = GpuManager(addon_id="my_engine")
demo_canvas = gpu.create_canvas(category="My Engine", panel_label="Custom GPU Engine")
CUSTOM_PT_gpu_canvas.canvas = demo_canvas

def register():
    try:
        bpy.utils.register_class(CUSTOM_PT_gpu_canvas)
    except ValueError:
        pass
    init_demo_widgets(demo_canvas)
    gpu.register()

def unregister():
    gpu.unregister()
    demo_canvas.clear()
    try:
        bpy.utils.unregister_class(CUSTOM_PT_gpu_canvas)
    except Exception:
        pass

if __name__ == "__main__":
    register()