import bpy
from ..blgpu import GpuCanvas, GpuManager
from ..blgpu.widgets import (
    UIButton, UISlider, UILabel, UICheckbox, UIColorPicker,
    UITextBox, UIDropdown, UIColumn, UIRow, UICurveEditor, UIGradientRamp, UIVectorPad, UIRangeSlider,
    UIRadialKnob, UIColorWheel, UIOrbitSphere, UITimelineScrubber, UIMiniNodeGraph, UIWaveformView,
    UITransformBox, UIImageInspector
)

def on_demo_button_clicked(btn):
    if not hasattr(btn, "clicks"):
        btn.clicks = 0
    btn.clicks += 1
    btn.text = f"Clicked {btn.clicks}x"
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

def on_curve_changed(curve, pts):
    print(f"[blgpu] Curve updated: {len(pts)} points")

def on_gradient_changed(ramp, stops):
    print(f"[blgpu] Gradient ramp updated: {len(stops)} stops")

def init_demo_widgets(canvas: GpuCanvas):
    canvas.clear()
    
    # Auto-layout column container with padding and spacing
    col = UIColumn(padding_x=14, padding_top=14, spacing=9)
    
    # 1. Section Header with vector icon
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

    # 7. Buttons with GPU Vector Icons
    row = UIRow(spacing=6, height=26)
    btn_gear = UIButton(
        text="Options",
        icon="GEAR",
        on_click=on_demo_button_clicked
    )
    btn_eye = UIButton(
        text="Isolate",
        icon="EYE",
        on_click=lambda b: print("[blgpu] Isolate toggled")
    )
    row.add(btn_gear)
    row.add(btn_eye)
    col.add(row)

    # 8. Advanced GPU Feature 1: Interactive Curve Graph Editor
    curve_header = UILabel(text="FALLOFF CURVE (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(curve_header)
    curve = UICurveEditor(
        points=[(0.0, 0.0), (0.25, 0.75), (0.75, 0.25), (1.0, 1.0)],
        default_points=[(0.0, 0.0), (0.25, 0.75), (0.75, 0.25), (1.0, 1.0)],
        max_points=8,
        height=85,
        on_change=on_curve_changed
    )
    col.add(curve)

    # 9. Advanced GPU Feature 2: Realtime Multi-Stop Color Ramp
    ramp_header = UILabel(text="COLOR RAMP (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(ramp_header)
    ramp = UIGradientRamp(
        stops=[
            [0.0, (0.08, 0.08, 0.12, 1.0)],
            [0.45, (0.278, 0.447, 0.702, 1.0)],
            [1.0, (1.0, 0.85, 0.35, 1.0)]
        ],
        default_stops=[
            [0.0, (0.08, 0.08, 0.12, 1.0)],
            [0.45, (0.278, 0.447, 0.702, 1.0)],
            [1.0, (1.0, 0.85, 0.35, 1.0)]
        ],
        max_stops=8,
        height=52,
        on_change=on_gradient_changed
    )
    col.add(ramp)

    # 10. Advanced GPU Feature 3: Interactive 2D Vector / XY Trackpad
    pad_header = UILabel(text="DIRECTION / TILT (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(pad_header)
    pad = UIVectorPad(
        text="XY Pad",
        min_x=-1.0,
        max_x=1.0,
        min_y=-1.0,
        max_y=1.0,
        default_x=0.0,
        default_y=0.0,
        value_x=0.35,
        value_y=0.50,
        height=125,
        on_change=lambda vx, vy: print(f"[blgpu] Vector pad: X={vx:+.2f}, Y={vy:+.2f}")
    )
    col.add(pad)

    # 11. Advanced GPU Feature 4: Dual-Handle Range Slider [Min .. Max]
    range_slider = UIRangeSlider(
        text="Threshold Range",
        min_range=0.0,
        max_range=1.0,
        val_min=0.20,
        val_max=0.75,
        height=38,
        on_change=lambda vmin, vmax: print(f"[blgpu] Range changed: [{vmin:.2f} .. {vmax:.2f}]")
    )
    col.add(range_slider)

    # 12. Advanced GPU Feature 5: Rotary Knob / Radial Dials
    knob_header = UILabel(text="ROTARY DIALS (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(knob_header)

    knob_row = UIRow(spacing=10, height=95)
    knob1 = UIRadialKnob(
        text="Rotation",
        min_value=0.0,
        max_value=360.0,
        default_value=45.0,
        step=1.0,
        precision=0,
        unit="°",
        on_change=lambda v: print(f"[blgpu] Rotation knob: {v:.0f}°")
    )
    knob2 = UIRadialKnob(
        text="Gain",
        min_value=-12.0,
        max_value=12.0,
        default_value=0.0,
        step=0.5,
        precision=1,
        unit=" dB",
        on_change=lambda v: print(f"[blgpu] Gain knob: {v:+.1f} dB")
    )
    knob_row.add(knob1)
    knob_row.add(knob2)
    col.add(knob_row)

    # 13. Advanced GPU Feature 6: Embedded Continuous HSV Color Wheel
    wheel_header = UILabel(text="EMBEDDED COLOR WHEEL (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(wheel_header)

    color_wheel = UIColorWheel(
        text="Base Tint",
        default_color=(0.22, 0.65, 1.0, 1.0),
        height=145,
        wheel_radius=38.0,
        on_color_change=lambda c: print(f"[blgpu] Color wheel: R={c[0]:.2f}, G={c[1]:.2f}, B={c[2]:.2f}")
    )
    col.add(color_wheel)

    # 14. Advanced GPU Feature 7: Interactive 3D Viewport Sphere / Arcball Trackball
    sphere_header = UILabel(text="3D DIRECTION / ORBIT SPHERE (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(sphere_header)

    orbit_sphere = UIOrbitSphere(
        text="Light Direction",
        height=135,
        radius=38.0,
        on_change=lambda v: print(f"[blgpu] 3D Vector: X={v[0]:+.2f}, Y={v[1]:+.2f}, Z={v[2]:+.2f}")
    )
    col.add(orbit_sphere)

    # 15. Advanced GPU Feature 8: Interactive Timeline & Keyframe Scrubber
    timeline_header = UILabel(text="ANIMATION TIMELINE (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(timeline_header)

    timeline = UITimelineScrubber(
        text="Playback",
        start_frame=1,
        end_frame=120,
        current_frame=24,
        keyframes=[1, 24, 48, 72, 96, 120],
        height=68,
        on_frame_change=lambda f: print(f"[blgpu] Timeline frame: {f:.1f}")
    )
    col.add(timeline)

    # 16. Advanced GPU Feature 9: Interactive Mini Node Graph & Wireflow
    graph_header = UILabel(text="MINI NODE GRAPH (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(graph_header)

    node_graph = UIMiniNodeGraph(
        text="Material Flow",
        height=175,
        on_connect=lambda src_n, src_s, dst_n, dst_s: print(f"[blgpu] Connected: {src_n}.{src_s} -> {dst_n}.{dst_s}")
    )
    col.add(node_graph)

    # 17. Advanced GPU Feature 10: Interactive Audio Waveform & Loop Region
    wave_header = UILabel(text="AUDIO WAVEFORM (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(wave_header)

    waveform = UIWaveformView(
        text="Voice_Track_01.wav",
        duration=8.0,
        playhead_time=2.4,
        loop_in=1.5,
        loop_out=6.2,
        height=85,
        on_scrub=lambda t: print(f"[blgpu] Audio playhead: {t:.2f}s"),
        on_loop_change=lambda li, lo: print(f"[blgpu] Loop region: [{li:.2f}s .. {lo:.2f}s]")
    )
    col.add(waveform)

    # 18. Advanced GPU Feature 11: Interactive 2D UV / Transform Box Manipulator
    trans_header = UILabel(text="2D UV / TRANSFORM GIZMO (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(trans_header)

    transform_box = UITransformBox(
        text="UV Box",
        pos_x=0.0,
        pos_y=0.0,
        scale_x=1.0,
        scale_y=1.0,
        rotation_deg=15.0,
        height=150,
        on_transform_change=lambda p, s, r: print(f"[blgpu] Transform: Pos=({p[0]:+.2f}, {p[1]:+.2f}), S=({s[0]:.2f}, {s[1]:.2f}), R={r:.0f}°")
    )
    col.add(transform_box)

    # 19. Advanced GPU Feature 12: Interactive Image & Texture Inspector (Pan, Zoom, Probe)
    img_header = UILabel(text="IMAGE & TEXTURE INSPECTOR (GPU)", font_size=10, color=(0.6, 0.6, 0.6, 1.0), height=14)
    col.add(img_header)

    img_inspector = UIImageInspector(
        text="Albedo_Test.png",
        height=165,
        on_pixel_probe=lambda u, v, rgba: None
    )
    col.add(img_inspector)
    
    canvas.add(col)


# The standard Blender Panel that hosts the demo canvas
class CUSTOM_PT_gpu_canvas(bpy.types.Panel):
    bl_idname = "CUSTOM_PT_gpu_canvas"
    bl_label = "Custom GPU Engine"     
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'My Engine'          

    # Canvas assigned at registration time
    canvas = None

    def draw(self, context):
        if self.canvas:
            self.canvas.draw_placeholder(self.layout)
        else:
            col = self.layout.column()
            col.scale_y = 118.0
            col.label(text="")
