# Widget Catalog & API Reference

Complete reference for all 20+ GPU widgets in `blgpu`, including constructor arguments, callbacks, and code examples.

---

## 1. Basic Interactive Controls

### `UIButton`
**Module**: `blgpu/widgets/button.py`  
Interactive push button with hover illumination and click animations.

```python
from .blgpu.widgets import UIButton

btn = UIButton(
    x=0, y=0, width=180, height=28,
    text="Generate Mesh",
    icon="GEAR"  # Optional icon name
)

btn.on_click(lambda w: print("Button clicked!"))
```
- **Supported Icons**: `"GEAR"`, `"EYE"`, `"CHECK"`, `"CHEVRON_DOWN"`, `"CHEVRON_RIGHT"`, `"PLUS"`, `"CLOSE"`, `"LOCK"`, `"SEARCH"`.

---

### `UILabel`
**Module**: `blgpu/widgets/label.py`  
Hardware anti-aliased text label for headers, captions, and descriptions.

```python
from .blgpu.widgets import UILabel

label = UILabel(
    text="SUBDIVISION SETTINGS",
    font_size=10,
    color=(0.6, 0.6, 0.6, 1.0),
    height=16
)
```

---

### `UISlider`
**Module**: `blgpu/widgets/slider.py`  
Scalar numerical slider with draggable bar, click-to-jump, and live readout.

```python
from .blgpu.widgets import UISlider

slider = UISlider(
    x=0, y=0, width=180, height=22,
    min_value=0.0, max_value=1.0, value=0.5,
    precision=2, show_value=True
)

slider.on_value_change(lambda w, val: print(f"Slider value: {val:.2f}"))
```

---

### `UICheckbox`
**Module**: `blgpu/widgets/checkbox.py`  
Toggle checkbox with smooth checkmark drawing and state feedback.

```python
from .blgpu.widgets import UICheckbox

chk = UICheckbox(
    x=0, y=0, width=180, height=20,
    text="Wireframe Overlay",
    state=True
)

chk.on_state_change(lambda w, state: print(f"State is now: {state}"))
```

---

### `UIDropdown`
**Module**: `blgpu/widgets/dropdown.py`  
Compact dropdown menu with an expandable popup option list.

```python
from .blgpu.widgets import UIDropdown

dd = UIDropdown(
    x=0, y=0, width=180, height=24,
    items=["Solid", "Wireframe", "Material Preview", "Rendered"],
    selected_index=0
)

dd.on_select(lambda w, idx, text: print(f"Selected: {text} (#{idx})"))
```

---

## 2. Text & Numerical Input

### `UITextBox`
**Module**: `blgpu/widgets/textbox.py`  
Full text editing engine with mouse drag selection, double-click word selection, clipboard copy/cut/paste (`Ctrl+C`, `Ctrl+X`, `Ctrl+V`), undo history (`Ctrl+Z`), exact cursor placement, and outside-click commit.

```python
from .blgpu.widgets import UITextBox

txt = UITextBox(
    x=0, y=0, width=180, height=24,
    text="Sphere_01",
    placeholder="Enter object name..."
)

txt.on_commit(lambda w, text: print(f"Committed text: {text}"))
```

---

### `UIRadialKnob`
**Module**: `blgpu/widgets/radial_knob.py`  
Rotary knob with circular $(X, Y)$ angular tracking ($d\theta$ across all 4 quadrants), linear scrub fallback, 10x Shift precision mode with dynamic sub-integer decimals, and Ctrl step snapping.

```python
from .blgpu.widgets import UIRadialKnob

knob = UIRadialKnob(
    x=0, y=0, radius=24,
    min_value=0.0, max_value=360.0, value=45.0,
    unit="°", precision=1, step=15.0
)

# Hold Shift while dragging for 10x fine precision adjustments (e.g. 45.24°)
knob.on_value_change(lambda w, val: print(f"Knob angle: {val:.2f}°"))
```

---

### `UIRangeSlider`
**Module**: `blgpu/widgets/range_slider.py`  
Dual-handle numerical interval slider `[Min .. Max]` with a center draggable span bar.

```python
from .blgpu.widgets import UIRangeSlider

range_slider = UIRangeSlider(
    x=0, y=0, width=180, height=36,
    min_range=0.0, max_range=1.0,
    val_min=0.20, val_max=0.75
)

range_slider.on_change(lambda vmin, vmax: print(f"Range: [{vmin:.2f} .. {vmax:.2f}]"))
```

---

## 3. Color & Gradients

### `UIColorPicker`
**Module**: `blgpu/widgets/color_picker.py`  
Color swatch button that opens a floating native HSV color wheel disc, continuous luminance slider, hex readout, and quick preset palette.

```python
from .blgpu.widgets import UIColorPicker

cp = UIColorPicker(
    x=0, y=0, width=180, height=24,
    color=(0.8, 0.2, 0.3, 1.0)
)

cp.on_color_change(lambda w, rgba: print(f"Color: {rgba}"))
```

---

### `UIColorWheel`
**Module**: `blgpu/widgets/color_wheel.py`  
Standalone circular HSV disc for color grading and tint control.

```python
from .blgpu.widgets import UIColorWheel

wheel = UIColorWheel(x=0, y=0, radius=45)
wheel.on_change(lambda w, rgb: print(f"Wheel RGB: {rgb}"))
```

---

### `UIGradientRamp`
**Module**: `blgpu/widgets/gradient_ramp.py`  
Multi-stop gradient ramp with draggable color pins, click to add stop, right-click to delete, and double-click pin to open a floating HSV color picker dialog.

```python
from .blgpu.widgets import UIGradientRamp

ramp = UIGradientRamp(
    x=0, y=0, width=180, height=48,
    stops=[
        [0.0, (0.05, 0.05, 0.1, 1.0)],
        [0.5, (0.28, 0.45, 0.7, 1.0)],
        [1.0, (1.0, 0.85, 0.35, 1.0)]
    ],
    max_stops=8,
    min_stops=2
)

ramp.on_change(lambda r, stops: print(f"Gradient stops: {len(stops)}"))
```

---

## 4. Curves & Graph Visualizers

### `UICurveEditor`
**Module**: `blgpu/widgets/curve_editor.py`  
Interactive spline/falloff curve editor with neighbor clamping (points cannot jump past adjacent neighbors), endpoint locking ($X=0$ and $X=1$ remain anchored), and double-click to add points.

```python
from .blgpu.widgets import UICurveEditor

curve = UICurveEditor(
    x=0, y=0, width=180, height=100,
    points=[(0.0, 0.0), (0.25, 0.75), (0.75, 0.25), (1.0, 1.0)],
    lock_endpoints_x=True,
    max_points=8,
    min_points=2
)

curve.on_change(lambda c, pts: print(f"Curve points: {pts}"))
```

---

### `UIWaveformView`
**Module**: `blgpu/widgets/waveform_view.py`  
Oscilloscope and audio/sensor waveform visualizer with smooth anti-aliased line rendering.

```python
from .blgpu.widgets import UIWaveformView
import math

wave = UIWaveformView(x=0, y=0, width=180, height=40)
wave.set_data([math.sin(i * 0.15) for i in range(120)])
```

---

### `UITimelineScrubber`
**Module**: `blgpu/widgets/timeline_scrubber.py`  
Frame playback and timeline navigation scrubber.

```python
from .blgpu.widgets import UITimelineScrubber

scrubber = UITimelineScrubber(
    x=0, y=0, width=180, height=26,
    start_frame=1, end_frame=250, current_frame=1
)

scrubber.on_frame_change(lambda w, frame: setattr(bpy.context.scene, "frame_current", int(frame)))
```

---

### `UIMiniNodeGraph`
**Module**: `blgpu/widgets/node_graph.py`  
Compact node wire graph visualizer for procedural graphs and material pipelines.

```python
from .blgpu.widgets import UIMiniNodeGraph

graph = UIMiniNodeGraph(x=0, y=0, width=180, height=80)
```

---

## 5. Spatial & 3D Manipulators

### `UIVectorPad`
**Module**: `blgpu/widgets/vector_pad.py`  
2D planar joystick / coordinate pad with center reticle for directional vectors, UV coordinates, or wind direction.

```python
from .blgpu.widgets import UIVectorPad

pad = UIVectorPad(
    x=0, y=0, width=120, height=120,
    min_x=-1.0, max_x=1.0,
    min_y=-1.0, max_y=1.0,
    value_x=0.0, value_y=0.0
)

pad.on_change(lambda w, vx, vy: print(f"Vector: ({vx:.2f}, {vy:.2f})"))
```

---

### `UIOrbitSphere`
**Module**: `blgpu/widgets/orbit_sphere.py`  
Interactive 3D trackball sphere for controlling directional light angles, surface normals, or sun positions.

```python
from .blgpu.widgets import UIOrbitSphere

sphere = UIOrbitSphere(x=0, y=0, radius=36)
sphere.on_change(lambda w, norm: print(f"Normal vector: {norm}"))
```

---

### `UITransformBox`
**Module**: `blgpu/widgets/transform_box.py`  
2D bounding box transform manipulator with corner resize handles.

```python
from .blgpu.widgets import UITransformBox

tbox = UITransformBox(x=0, y=0, width=140, height=100)
```

---

### `UIImageInspector`
**Module**: `blgpu/widgets/image_inspector.py`  
Interactive pan & zoom image viewer with pixel grid.

```python
from .blgpu.widgets import UIImageInspector

img_view = UIImageInspector(x=0, y=0, width=180, height=120)
```
