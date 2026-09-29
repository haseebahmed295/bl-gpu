bl_info = {
    "name": "Custom GPU Panel Engine",
    "author": "haseebahmed295",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > N-Panel > My Engine",
    "description": "Draws a custom GPU overlay inside the N-Panel",
    "warning": "Requires custom my_engine binary",
    "category": "3D View",
}

import bpy
from . import gpu_core
from . import event_handler

class CUSTOM_PT_gpu_canvas(bpy.types.Panel):
    bl_idname = "CUSTOM_PT_gpu_canvas"
    bl_label = "Custom GPU Engine"     
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'My Engine'          

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        # Reserve vertical height to make room for your custom GPU elements
        col.scale_y = 25.0 
        col.label(text="")

classes = (
    CUSTOM_PT_gpu_canvas,
    event_handler.EventHandler,
)

def on_demo_button_clicked(btn):
    if not hasattr(btn, "clicks"):
        btn.clicks = 0
    btn.clicks += 1
    btn.text = f"Clicked {btn.clicks} times!"
    print(f"[blgpu] Button clicked: count={btn.clicks}")

def on_slider_changed(slider, val):
    print(f"[blgpu] Slider value changed: {val:.2f}")

def on_checkbox_toggled(chk, val):
    print(f"[blgpu] Checkbox '{chk.text}' is now: {val}")

def on_color_swatch_changed(cp, col):
    print(f"[blgpu] Swatch color changed: {col}")

def on_dropdown_select(dp, index, text):
    print(f"[blgpu] Dropdown selected: '{text}' (index {index})")

def on_textbox_commit(tb, text):
    print(f"[blgpu] Text committed: '{text}'")

def init_demo_widgets():
    from .bl_ui_widgets import UIButton, UISlider, UILabel, UICheckbox, UIColorPicker, UITextBox, UIDropdown, UIColumn, UIRow
    gpu_core.panel_widgets.clear()
    
    # Auto-layout column container with padding and spacing
    col = UIColumn(padding_x=14, padding_top=14, spacing=9)
    
    # 1. Section Header
    header = UILabel(text="DISPLAY SETTINGS", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=16)
    col.add(header)
    
    # 2. Text Input Box
    textbox = UITextBox(
        placeholder="Type object name...",
        default_text="Sphere_01",
        height=24,
        on_commit=on_textbox_commit
    )
    col.add(textbox)

    # 3. Enum Dropdown Selector
    dropdown = UIDropdown(
        items=["Solid Mode", "Wireframe", "Material Preview", "Rendered"],
        default_index=0,
        height=24,
        on_select=on_dropdown_select
    )
    col.add(dropdown)

    # 4. Interactive Checkbox Toggle
    chk = UICheckbox(
        text="Wireframe Overlay",
        border_color=(1.0,0, 0,0 ),
        border_width=0.1,
        default_value=True,
        height=22,
        on_change=on_checkbox_toggled
    )
    col.add(chk)

    # 5. Interactive Slider
    slider = UISlider(
        text="Roughness",
        min_value=0.0,
        max_value=1.0,
        default_value=0.65,
        step=0.01,
        precision=2,
        height=24,
        on_change=on_slider_changed
    )
    col.add(slider)

    # 6. Color Swatch Picker
    cp = UIColorPicker(
        text="Accent Color",
        default_color=(0.25, 0.55, 0.95, 1.0),
        height=22,
        on_color_change=on_color_swatch_changed
    )
    col.add(cp)

    # 7. Side-by-side Buttons in a Row
    row = UIRow(spacing=6, height=26)
    btn1 = UIButton(
        text="Click Me!",
        on_click=on_demo_button_clicked
    )
    btn2 = UIButton(
        text="Reset",
        on_click=lambda b: _reset_demo(btn1)
    )
    row.add(btn1)
    row.add(btn2)
    col.add(row)
    
    gpu_core.panel_widgets.append(col)

def _reset_demo(target_btn):
    target_btn.clicks = 0
    target_btn.text = "Click Me!"
    print("[blgpu] Counter reset!")

def register(): 
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.gpu_event_handler_state = bpy.props.BoolProperty(default=False)

    init_demo_widgets()

    # Register Watchdog
    if not bpy.app.timers.is_registered(gpu_core.watchdog_timer_check):
        bpy.app.timers.register(gpu_core.watchdog_timer_check)

def unregister():   
    # Unregister Watchdog
    if bpy.app.timers.is_registered(gpu_core.watchdog_timer_check):
        bpy.app.timers.unregister(gpu_core.watchdog_timer_check)
        
    gpu_core.teardown_draw_handler()
    gpu_core.panel_widgets.clear()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    if hasattr(bpy.types.Scene, "gpu_event_handler_state"):
        del bpy.types.Scene.gpu_event_handler_state

if __name__ == "__main__":
    register()