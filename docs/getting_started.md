# Getting Started & Vendoring Guide

This guide explains how to vendor `blgpu` directly into your Blender addon and connect GPU widgets to Blender scene properties.

---

## 1. Vendoring `blgpu` into Your Addon

`blgpu` is built to be vendored (copied) directly into your addon without external package managers or wheel installations.

### Directory Structure
Copy only the `blgpu/` folder from this repository into your addon's root directory:

```
my_addon/
├── __init__.py                  # Your addon's main entry point
└── blgpu/                       # Vendored blgpu package
    ├── __init__.py              # Library exports
    ├── core/                    # Engine, canvas, manager, event handler
    ├── widgets/                 # 20+ GPU widgets
    └── binaries/                # my_engine.cp313-win_amd64.pyd
```

> [!NOTE]
> The `demo/` and `docs/` folders from the `blgpu` repository are left out. The `blgpu/` folder is completely self-contained and weighs ~180 KB.

---

## 2. Minimal Working Example

In your addon's `__init__.py`:

```python
bl_info = {
    "name": "My Tool",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "category": "3D View",
}

import bpy
from .blgpu import GpuManager, GpuCanvas
from .blgpu.widgets import UIColumn, UIButton, UISlider

# 1. Initialize isolated manager with your addon's unique ID
gpu = GpuManager(addon_id="my_tool")

# 2. Create canvas bound to your N-panel Category and Label
canvas = gpu.create_canvas(category="My Tool", panel_label="Settings")

# 3. Add widgets
col = UIColumn(padding_x=14, padding_top=14, spacing=10)

btn = UIButton(x=0, y=0, width=180, height=28, text="Run Task")
btn.on_click(lambda w: print("Task executed!"))
col.add_child(btn)

slider = UISlider(x=0, y=0, width=180, height=22, min_value=0.0, max_value=100.0, value=50.0)
slider.on_value_change(lambda w, val: print(f"Value: {val:.1f}"))
col.add_child(slider)

canvas.add_widget(col)

# 4. Standard Blender Panel
class MYTOOL_PT_panel(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "MYTOOL_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Tool"

    def draw(self, context):
        # Automatically reserves layout space to prevent 3D viewport bleed
        canvas.draw_placeholder(self.layout)

def register():
    bpy.utils.register_class(MYTOOL_PT_panel)
    gpu.register()

def unregister():
    gpu.unregister()
    bpy.utils.unregister_class(MYTOOL_PT_panel)

if __name__ == "__main__":
    register()
```

---

## 3. Dynamic Layout Spacers (`canvas.draw_placeholder`)

Because Blender's native UI layout does not automatically know that custom GPU elements are being drawn on top of the panel, we must reserve vertical layout space.

`GpuCanvas` handles this dynamically:
1. `canvas.get_content_height()` automatically inspects all registered widgets and containers (including `UIColumn` and `UIRow`).
2. `canvas.draw_placeholder(self.layout)` inserts a spacer into Blender's layout scaled to match the exact vertical pixel height:
   ```python
   def draw(self, context):
       canvas.draw_placeholder(self.layout)
   ```
This guarantees that:
- Blender native buttons below your GPU widgets are pushed down correctly.
- Panels below your panel in the N-panel stack never overlap.
- Widgets never bleed into the 3D Viewport when the panel is collapsed or scrolled.

---

## 4. Multi-Addon Isolation (`addon_id`)

Multiple addons using `blgpu` can run concurrently in the same Blender session without conflicts.

When instantiating `GpuManager`:
```python
# Pass a unique identifier (lowercase letters, digits, and underscores)
gpu = GpuManager(addon_id="my_rig_toolkit")
```
This dynamically creates an isolated modal operator:
`my_rig_toolkit.gpu_panel_handler`

If another installed addon uses:
```python
gpu_other = GpuManager(addon_id="shader_forge")
```
It registers `shader_forge.gpu_panel_handler`. The two operators and their watchdog timers operate completely independently without colliding.

---

## 5. Two-Way Data Binding with Blender Properties (`bpy.props`)

To synchronize GPU widgets with Blender scene or object properties:

```python
# 1. Define your scene property
bpy.types.Scene.roughness = bpy.props.FloatProperty(name="Roughness", default=0.5, min=0.0, max=1.0)

# 2. Wire the widget callback to update the Blender property:
slider = UISlider(x=0, y=0, width=180, height=22, min_value=0.0, max_value=1.0, value=0.5)

def on_slider_drag(w, val):
    bpy.context.scene.roughness = val

slider.on_value_change(on_slider_drag)

# 3. In your panel draw() method, synchronize state if changed externally:
class MYTOOL_PT_panel(bpy.types.Panel):
    bl_label = "Settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "My Tool"

    def draw(self, context):
        # Sync widget display value if Blender property changed via python or animation
        slider.value = context.scene.roughness
        canvas.draw_placeholder(self.layout)
```

---

## 6. Multiple Canvases & Panels in One Addon

You can bind multiple panels under the same tab or across multiple tabs using a single `GpuManager`:

```python
gpu = GpuManager(addon_id="my_tool")

# Canvas 1: Main Panel
canvas_main = gpu.create_canvas(category="My Tool", panel_label="Main")
canvas_main.add_widget(btn_generate)

# Canvas 2: Settings Panel (under the same tab)
canvas_settings = gpu.create_canvas(category="My Tool", panel_label="Advanced")
canvas_settings.add_widget(slider_quality)

# In your respective Panel classes:
class MYTOOL_PT_main(bpy.types.Panel):
    bl_label = "Main"
    bl_category = "My Tool"
    ...
    def draw(self, context):
        canvas_main.draw_placeholder(self.layout)

class MYTOOL_PT_settings(bpy.types.Panel):
    bl_label = "Advanced"
    bl_category = "My Tool"
    ...
    def draw(self, context):
        canvas_settings.draw_placeholder(self.layout)
```
