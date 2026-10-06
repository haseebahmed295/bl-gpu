# Layout Containers

`blgpu` provides automatic layout containers that manage $(X, Y)$ coordinate math, margins, padding, and spacing automatically.

---

## 1. `UIColumn` (Vertical Stack)

**Module**: `blgpu/widgets/layout.py`

`UIColumn` stacks child widgets vertically from top to bottom.

### Parameters
| Parameter | Type | Default | Description |
|---|---|---|---|
| `x` | `float` | `0.0` | Container left offset (relative to panel). |
| `y` | `float` | `0.0` | Container top offset (relative to panel). |
| `padding_x` | `float` | `14.0` | Left and right internal margin in pixels. |
| `padding_top` | `float` | `14.0` | Top margin in pixels. |
| `spacing` | `float` | `8.0` | Vertical gap between adjacent child widgets. |

### Example
```python
from .blgpu.widgets import UIColumn, UIButton, UISlider, UICheckbox

col = UIColumn(padding_x=14, padding_top=14, spacing=10)

col.add_child(UIButton(x=0, y=0, width=180, height=28, text="Action 1"))
col.add_child(UIButton(x=0, y=0, width=180, height=28, text="Action 2"))
col.add_child(UISlider(x=0, y=0, width=180, height=22, min_value=0, max_value=100, value=50))
col.add_child(UICheckbox(x=0, y=0, width=180, height=20, text="Enable Feature", state=True))

canvas.add_widget(col)
```

### Height Calculation
`col.get_total_height()` returns the cumulative height of all children plus margins and spacing. `canvas.draw_placeholder(self.layout)` uses this value to reserve the exact vertical space in the Blender N-panel.

---

## 2. `UIRow` (Horizontal Row)

**Module**: `blgpu/widgets/row.py`

`UIRow` arranges child widgets side-by-side on the same horizontal line.

### Parameters
| Parameter | Type | Default | Description |
|---|---|---|---|
| `x` | `float` | `0.0` | Row left offset. |
| `y` | `float` | `0.0` | Row top offset. |
| `spacing` | `float` | `6.0` | Horizontal gap between adjacent child widgets. |
| `height` | `float` | `24.0` | Row line height. |

### Example
```python
from .blgpu.widgets import UIRow, UIButton

row = UIRow(spacing=8, height=26)
row.add_child(UIButton(x=0, y=0, width=86, height=26, text="Apply"))
row.add_child(UIButton(x=0, y=0, width=86, height=26, text="Reset"))

col.add_child(row)
```

---

## 3. Nesting: Combining Columns & Rows

You can nest rows inside columns to create complex toolbars and parameter rows:

```python
from .blgpu.widgets import UIColumn, UIRow, UILabel, UIButton, UITextBox, UISlider

col = UIColumn(padding_x=14, padding_top=14, spacing=10)

# Section Header
col.add_child(UILabel(text="OBJECT SETTINGS", font_size=11, color=(0.7, 0.7, 0.7, 1.0)))

# Row 1: Name text box with quick rename button
name_row = UIRow(spacing=6, height=24)
name_row.add_child(UITextBox(x=0, y=0, width=130, height=24, text="Cube_01"))
name_row.add_child(UIButton(x=0, y=0, width=44, height=24, text="Set"))
col.add_child(name_row)

# Row 2: Two numeric buttons
axis_row = UIRow(spacing=6, height=24)
axis_row.add_child(UIButton(x=0, y=0, width=87, height=24, text="X Axis"))
axis_row.add_child(UIButton(x=0, y=0, width=87, height=24, text="Y Axis"))
col.add_child(axis_row)

# Full-width slider below
col.add_child(UISlider(x=0, y=0, width=180, height=22, min_value=0.0, max_value=1.0, value=0.5))

canvas.add_widget(col)
```
