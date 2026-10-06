# Core Engine Architecture

This document details the internal architecture of `blgpu`, explaining how it communicates with Blender's C/C++ DNA structures, coordinates event loops, and guarantees conflict-free operation across multiple addons.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Blender Host                          │
│                                                             │
│   ┌──────────────────┐          ┌───────────────────────┐   │
│   │ 3D Viewport      │          │ Sidebar (N-Panel)     │   │
│   │ POST_PIXEL Hook  │          │ ARegion / Panel DNA   │   │
│   └─────────┬────────┘          └───────────┬───────────┘   │
└─────────────┼───────────────────────────────┼───────────────┘
              │                               │
              ▼                               ▼
    ┌──────────────────┐           ┌────────────────────┐
    │ GpuDrawManager   │           │ my_engine (C++)    │
    │ (GPU Batch Draw) │           │ (ReadProcessMemory)│
    └─────────▲────────┘           └──────────┬─────────┘
              │                               │
              │         ┌─────────────┐       │
              └─────────┤ GpuCanvas   │◄──────┘
                        │ (UI Bounds) │
                        └──────▲──────┘
                               │
                        ┌──────┴──────┐
                        │ GpuManager  │
                        │ (Modal Loop)│
                        └─────────────┘
```

---

## 2. The Native DNA Bridge (`my_engine`)

### The Problem
Blender's official Python API does not expose:
- The exact runtime pixel coordinates $(X, Y, W, H)$ of individual sidebar panels.
- The vertical scroll offset of the sidebar region (`v2d.cur.ymin`).
- Which N-Panel category tab is currently active.

### The Solution
`blgpu` bundles `my_engine`, a lightweight C++ extension built with `pybind11`.
- It finds the host Blender process and inspects the `ARegion` and `Panel` DNA structs in memory via Windows `ReadProcessMemory`.
- It reads:
  - `region->winrct`: Sidebar region window rect.
  - `region->v2d.cur`: Scroll offsets and zoom factors.
  - `panel->runtime.panel_category`: Currently active category tab.
  - `panel->runtime.rect`: Panel header and content rectangle.
- Reads are read-only and non-intrusive—no DLL injection or memory patching occurs.

---

## 3. `GpuManager` (Lifecycle & Event Loop)

**Module**: `blgpu/core/manager.py`

`GpuManager` manages the active lifecycle of your addon's custom GPU interface.

### Dynamic Operator Creation
To prevent `bl_idname` collisions when multiple addons vendor `blgpu`, `GpuManager` calls `create_event_handler_class(manager)`.
- It sanitizes `addon_id` (e.g. `"my_addon"`) and creates:
  ```python
  class MY_ADDON_OT_gpu_panel_handler(bpy.types.Operator):
      bl_idname = "my_addon.gpu_panel_handler"
  ```
- Calling `gpu.register()` registers this class with `bpy.utils.register_class()`.
- Calling `gpu.unregister()` unregisters the class from Blender's operator table.

### Memory-Only Modal Tracking
The modal operator checks `manager.is_modal_running` in Python memory.
- No properties are attached to `bpy.types.Scene` or `bpy.context.window_manager`.
- The operator terminates cleanly when `manager.is_modal_running = False` is set during unregistration or viewport changes.

### The Watchdog Timer
A non-intrusive background timer (`bpy.app.timers`) checks every 0.1 seconds whether the 3D Viewport is visible and active.
- If the mouse enters the 3D Viewport sidebar and the modal operator is not running, it starts the modal operator automatically.
- This ensures zero CPU/GPU overhead when the user is not actively interacting with the sidebar.

---

## 4. `GpuCanvas` (Panel Binding & Layout)

**Module**: `blgpu/core/canvas.py`

A `GpuCanvas` represents an isolated 2D drawing area mapped directly to one Blender N-Panel.

### Dynamic Binding
```python
canvas = gpu.create_canvas(category="Rigging", panel_label="Bone Controls")
```
Each frame:
1. `GpuManager` queries `my_engine` for a panel matching `category="Rigging"` and `panel_label="Bone Controls"`.
2. If found and visible, `canvas.current_rect` is updated with the panel's exact pixel boundaries $(X, Y, W, H)$.
3. Widgets belonging to that canvas are rendered within the panel's scissor rectangle.

### Automatic Height Calculation
`canvas.get_content_height()` traverses all registered widgets and layout containers:
```python
total_h = sum(widget.get_total_height() for widget in canvas.widgets)
```
Inside `Panel.draw(context)`:
```python
canvas.draw_placeholder(self.layout)
```
This automatically computes `col.scale_y = max(1.0, total_h / 20.0)`, reserving the exact vertical pixel height so native Blender elements below never overlap.

---

## 5. Event Routing & Keyboard Isolation

**Module**: `blgpu/core/event_handler.py`

The modal operator captures user input and routes it hierarchically:

1. **Hover & Drag Routing**:
   - Mouse screen coordinates $(mx, my)$ are translated to panel-local coordinates $(local\_x, local\_y)$.
   - Hover states (`is_hovered`) are evaluated for widgets under the cursor.
   - When a widget is actively dragged (such as a slider, curve point, or knob), all mouse move events are locked to that widget until release.

2. **Overlay Priority**:
   - Floating popups (such as `UIColorPicker`'s HSV wheel dialog or `UIDropdown`'s option menu) receive first priority for mouse events, intercepting clicks before underlying widgets.

3. **Safe Keyboard Isolation**:
   - When a `UITextBox` has focus, all keyboard events are consumed by the modal operator (`return {'RUNNING_MODAL'}`).
   - Viewport hotkeys (like `G`, `S`, `R`, `X`, `Space`) are blocked from leaking into Blender while typing.
   - Clicking outside the text field immediately clears focus and restores full hotkey control to the 3D Viewport.
