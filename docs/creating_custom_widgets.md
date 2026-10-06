# Creating Custom Widgets

This guide walks you through building your own hardware-accelerated 2D widgets in `blgpu`. You will learn how the rendering loop, coordinate transforms, hit-testing, and event handling work, concluding with a complete, production-ready custom widget example.

---

## 1. The Anatomy of a Widget

Every widget in `blgpu` inherits from `UIElement` (defined in [`blgpu/widgets/base.py`](../blgpu/widgets/base.py)).

A standard widget implements:
1. `__init__(...)`: Initializes dimensions, values, state flags, and callback storage.
2. `draw(self, origin_x, origin_y)`: Renders background, geometry, icons, and text using GPU shaders.
3. `handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool`: Intercepts mouse and keyboard inputs and triggers callbacks.
4. `draw_overlay(self, origin_x, origin_y)` *(Optional)*: Renders floating popups or tooltips above all other panel elements.

---

## 2. Coordinate System & DPI Scaling

### Relative vs. Absolute Coordinates
- **Widget Coordinates** (`self.x`, `self.y`): Stored **relative** to the panel or parent layout container.
- **Panel Origin** (`origin_x`, `origin_y`): The absolute lower-left or top-left origin of the panel in Blender's 3D Viewport UI region.
- **Absolute Position in Region**:
  ```python
  abs_x = origin_x + self.x
  abs_y = origin_y + self.y
  ```

### High-DPI UI Scaling
Blender users can change their display resolution scale in `Preferences > Interface > Resolution Scale`.
Always scale pixel offsets, radii, and font sizes using `BlenderTheme.get_ui_scale()`:

```python
from .theme import BlenderTheme

scale = BlenderTheme.get_ui_scale()
scaled_radius = 8.0 * scale
```

---

## 3. GPU Drawing Utilities

`UIElement` and `GpuShapes` provide ready-to-use GPU drawing primitives:

### Base Methods (`UIElement`)
- `self.draw_rect(x, y, w, h, color)`: Simple flat filled quad.
- `self.draw_rounded_rect(x, y, w, h, radius, color)`: Anti-aliased rounded rectangle.
- `self.draw_rounded_rect_outline(x, y, w, h, radius, color, line_width=1.0)`: Sub-pixel border ribbon.
- `self.draw_text(text, x, y, font_id=0, size=11, color=(1, 1, 1, 1), max_width=None)`: Scaled text drawing with optional automatic truncation (`...`).

### Advanced Vector Primitives (`GpuShapes`)
For high-performance vector rendering without OpenGL line aliasing:
```python
from .shapes import GpuShapes

# Anti-aliased line segment
GpuShapes.draw_smooth_line(x1, y1, x2, y2, color=(0.2, 0.6, 1.0, 1.0), line_width=2.0)

# Multi-point continuous spline / polyline
GpuShapes.draw_smooth_polyline(points, color=(1, 1, 1, 1), line_width=2.0)

# Anti-aliased filled circle / disc
GpuShapes.draw_smooth_circle(cx, cy, radius=12.0, color=(1.0, 0.4, 0.2, 1.0))

# Anti-aliased hollow ring
GpuShapes.draw_smooth_ring(cx, cy, radius=20.0, color=(0.3, 0.3, 0.3, 1.0), thickness=2.0)

# 270° rotary progress arc
GpuShapes.draw_smooth_arc(cx, cy, radius=24.0, a_start=math.pi * 0.75, a_end=math.pi * 2.25, color=(0.2, 0.5, 0.9, 1.0), thickness=3.0)
```

---

## 4. Handling Input Events

`handle_event` is called on active widgets during Blender's modal loop:

```python
def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
    if not self.visible or not self.enabled:
        return False

    abs_x = origin_x + self.x
    abs_y = origin_y + self.y
    inside = (abs_x <= mouse_x <= abs_x + self.width) and (abs_y <= mouse_y <= abs_y + self.height)
    state_changed = False

    # 1. Hover state
    if event.type == 'MOUSEMOVE':
        if not self.is_dragging and inside != self.hovered:
            self.hovered = inside
            state_changed = True
        if self.is_dragging:
            self._update_drag_value(mouse_x, abs_x)
            state_changed = True
        return state_changed

    # 2. Click & Drag
    elif event.type == 'LEFTMOUSE':
        if event.value == 'PRESS' and inside:
            self.pressed = True
            self.is_dragging = True
            self._update_drag_value(mouse_x, abs_x)
            return True
        elif event.value == 'RELEASE' and self.is_dragging:
            self.pressed = False
            self.is_dragging = False
            return True

    return False
```

> [!TIP]
> Return `True` whenever your widget's state changes or an action is consumed. This signals `GpuManager` to automatically trigger a 3D Viewport redraw.

---

## 5. Complete Step-by-Step Example: `UISegmentedControl`

Below is a complete, production-ready custom widget: a **Segmented Control (Tab Switcher)** that allows users to pick between multiple options.

Save this in your addon as `my_segmented_control.py`:

```python
import blf
from blgpu.widgets.base import UIElement
from blgpu.widgets.theme import BlenderTheme

class UISegmentedControl(UIElement):
    """
    Horizontal tabbed segmented control for switching between options.
    """
    def __init__(self, x=0, y=0, width=180, height=26, items=None, selected_index=0):
        super().__init__(x=x, y=y, width=width, height=height)
        self.items = items or ["Option A", "Option B"]
        self.selected_index = max(0, min(selected_index, len(self.items) - 1))
        self.hover_index = -1
        self._on_change_callbacks = []

    def on_change(self, callback):
        """Register callback: callback(widget, index, text)"""
        self._on_change_callbacks.append(callback)

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        ax = origin_x + self.x
        ay = origin_y + self.y
        w = self.width
        h = self.height

        num_segments = len(self.items)
        seg_w = w / max(1, num_segments)
        corner_r = 4.0 * scale

        # 1. Background pill track
        track_color = (0.14, 0.14, 0.14, 1.0)
        self.draw_rounded_rect(ax, ay, w, h, corner_r, track_color)
        self.draw_rounded_rect_outline(ax, ay, w, h, corner_r, (0.25, 0.25, 0.25, 1.0), line_width=1.0)

        # 2. Draw segments
        for i, text in enumerate(self.items):
            seg_x = ax + i * seg_w
            is_selected = (i == self.selected_index)
            is_hovered = (i == self.hover_index) and not is_selected

            # Highlight selected segment
            if is_selected:
                pill_col = (0.28, 0.45, 0.70, 1.0)  # Primary theme blue
                self.draw_rounded_rect(seg_x + 2, ay + 2, seg_w - 4, h - 4, corner_r - 1, pill_col)
            elif is_hovered:
                hover_col = (0.20, 0.20, 0.20, 1.0)
                self.draw_rounded_rect(seg_x + 2, ay + 2, seg_w - 4, h - 4, corner_r - 1, hover_col)

            # Center text in segment
            tw, th = self.get_text_dimensions(text, size=10)
            tx = seg_x + (seg_w - tw) * 0.5
            ty = ay + (h - th) * 0.5 + 1.0 * scale

            text_col = (1.0, 1.0, 1.0, 1.0) if is_selected else (0.7, 0.7, 0.7, 1.0)
            self.draw_text(text, tx, ty, size=10, color=text_col)

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled or not self.items:
            return False

        ax = origin_x + self.x
        ay = origin_y + self.y
        inside = (ax <= mouse_x <= ax + self.width) and (ay <= mouse_y <= ay + self.height)

        seg_w = self.width / len(self.items)

        if event.type == 'MOUSEMOVE':
            if inside:
                new_hover = int((mouse_x - ax) // seg_w)
                new_hover = max(0, min(new_hover, len(self.items) - 1))
                if new_hover != self.hover_index:
                    self.hover_index = new_hover
                    return True
            else:
                if self.hover_index != -1:
                    self.hover_index = -1
                    return True

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS' and inside:
            clicked_idx = int((mouse_x - ax) // seg_w)
            clicked_idx = max(0, min(clicked_idx, len(self.items) - 1))
            if clicked_idx != self.selected_index:
                self.selected_index = clicked_idx
                # Fire callbacks
                for cb in self._on_change_callbacks:
                    cb(self, self.selected_index, self.items[self.selected_index])
                return True

        return False
```

---

## 6. Using Your Custom Widget in a Panel

Add your custom widget to any canvas or layout container:

```python
from blgpu import GpuManager
from blgpu.widgets import UIColumn
from .my_segmented_control import UISegmentedControl

gpu = GpuManager(addon_id="my_custom_tool")
canvas = gpu.create_canvas(category="My Tool", panel_label="Display Mode")

col = UIColumn(padding_x=14, padding_top=14, spacing=10)

tabs = UISegmentedControl(
    x=0, y=0, width=180, height=26,
    items=["Low", "Medium", "High", "Ultra"],
    selected_index=1
)

def on_quality_change(widget, index, text):
    print(f"Quality switched to: {text} (#{index})")

tabs.on_change(on_quality_change)
col.add_child(tabs)
canvas.add_widget(col)
```
