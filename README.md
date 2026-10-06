# blgpu

> **Modern, High-Performance GPU UI Framework for Blender N-Panels**

[![Blender](https://img.shields.io/badge/Blender-4.2%20%7C%205.0%20%7C%205.2+-orange?logo=blender)](https://www.blender.org/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.13-blue?logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20x64-lightgrey?logo=windows)]()
[![Rendering](https://img.shields.io/badge/GPU-Hardware%20Accelerated-green)]()
[![License](https://img.shields.io/badge/License-MIT-brightgreen)]()

**blgpu** is a hardware-accelerated 2D UI framework designed for Blender addon developers. It enables rich, fluid, pixel-perfect custom UI widgets (rotary knobs, bezier curve editors, gradient ramps, vector pads, orbit spheres, interactive color wheels) directly inside Blender's 3D Viewport Sidebar (N-Panel).

---
<img width="1919" height="1016" alt="image" src="https://github.com/user-attachments/assets/9f1b6515-f09b-4406-8cb7-7f33b41e34ed" />

## ✨ Main Features

- 🎯 **Pixel-Perfect Alignment**: In-process C++ DNA inspection (`ARegion`, `Panel`, `View2D`) calculates exact panel bounds and scroll offsets.
- ⚡ **20+ GPU-Accelerated Widgets**: Anti-aliased sub-pixel rendering, rounded corners, drop shadows, and responsive hover animations.
- 📦 **Zero-Config Vendoring**: Self-contained `blgpu/` folder ready to be copied directly into any addon.
- 🛡️ **Conflict-Free Multi-Addon Isolation**: Dynamic operator generation (`{addon_id}.gpu_panel_handler`) ensures multiple addons using `blgpu` never collide.
- 🧠 **Zero Scene Pollution**: Lifecycle and modal states are tracked in Python memory—no `bpy.types.Scene` property clutter.
- 📐 **Automatic Height Calculation**: `canvas.draw_placeholder(layout)` dynamically scales layout spacers to prevent 3D viewport bleed.
- ⌨️ **Safe Keyboard Isolation**: Text fields capture keystrokes locally, preventing hotkey leaks (e.g. `G`, `S`, `R`, `X`) into the 3D Viewport.

---

## ⚡ Quickstart

### 1. Copy `blgpu/` into your addon
```
my_addon/
├── __init__.py
└── blgpu/                 <-- Copy this folder directly
    ├── core/
    ├── widgets/
    └── binaries/
```

### 2. Add widgets to your panel
```python
import bpy
from .blgpu import GpuManager, GpuCanvas
from .blgpu.widgets import UIColumn, UIButton, UISlider, UIRadialKnob

# 1. Initialize isolated GPU manager for your addon
gpu = GpuManager(addon_id="my_tool")

# 2. Bind canvas to your N-panel Category tab and Panel label
canvas = gpu.create_canvas(category="My Tool", panel_label="Settings")

# 3. Add widgets using an auto-layout column
layout = UIColumn(padding_x=14, padding_top=14, spacing=10)

btn = UIButton(x=0, y=0, width=180, height=28, text="Run Action")
btn.on_click(lambda w: print("Button clicked!"))

slider = UISlider(x=0, y=0, width=180, height=22, min_value=0.0, max_value=1.0, value=0.5)
slider.on_value_change(lambda w, val: print(f"Slider: {val:.2f}"))

knob = UIRadialKnob(x=0, y=0, radius=24, min_value=0, max_value=360, value=45, unit="°")
knob.on_value_change(lambda w, val: print(f"Angle: {val:.1f}°"))

layout.add_child(btn)
layout.add_child(slider)
layout.add_child(knob)
canvas.add_widget(layout)

# 4. Standard Blender Panel
class MYTOOL_PT_panel(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "MYTOOL_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Tool"

    def draw(self, context):
        # Automatically reserves layout space to prevent viewport bleed
        canvas.draw_placeholder(self.layout)

def register():
    bpy.utils.register_class(MYTOOL_PT_panel)
    gpu.register()

def unregister():
    gpu.unregister()
    bpy.utils.unregister_class(MYTOOL_PT_panel)
```

---

## 📚 Documentation

Detailed documentation is organized into dedicated guides inside [`docs/`](docs/):

| Guide | Description |
|---|---|
| 🚀 [**Getting Started & Vendoring**](docs/getting_started.md) | Step-by-step setup, vendoring guide, two-way `bpy.props` data binding. |
| 🎨 [**Widget Catalog & Reference**](docs/widgets_reference.md) | Exhaustive parameter reference, callbacks, and examples for all 20+ widgets. |
| 🛠️ [**Creating Custom Widgets**](docs/creating_custom_widgets.md) | Developer guide for building custom GPU widgets with shaders, shapes, and events. |
| 📐 [**Layout Containers**](docs/layouts.md) | Automatic vertical stacks (`UIColumn`) and horizontal rows (`UIRow`). |
| 🏗️ [**Core Engine Architecture**](docs/core_architecture.md) | `GpuManager`, `GpuCanvas`, modal lifecycle, and keyboard isolation. |
| 🔌 [**Native C++ Memory Bridge**](docs/my_engine.md) | Blender DNA inspection source, Windows `ReadProcessMemory`, and build steps. |


---

## 📄 License

This project is licensed under the MIT License.
