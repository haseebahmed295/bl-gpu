import re
import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader

from .engine_bridge import HAS_ENGINE, my_engine
from .draw_utils import GpuDrawManager
from .canvas import GpuCanvas
from .event_handler import create_event_handler_class

TIMER_INTERVAL = 0.2


class GpuManager:
    """
    Isolated GPU UI manager for an addon.
    Dynamically binds to any number of GpuCanvas panels and provides conflict-free
    operator registration, event handling, and drawing.
    """
    def __init__(self, addon_id: str = "blgpu"):
        clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', addon_id).lower().strip('_')
        self.addon_id = clean_id if clean_id else "blgpu"
        self.canvases = []

        self.draw_handle = None
        self.is_modal_running = False
        self.operator_cls = create_event_handler_class(self)

    @property
    def operator_idname(self) -> str:
        return self.operator_cls.bl_idname if self.operator_cls else ""

    def create_canvas(self, category: str, panel_label: str, panel_idname: str = None, min_height: float = 100.0) -> GpuCanvas:
        canvas = GpuCanvas(category=category, panel_label=panel_label, panel_idname=panel_idname, min_height=min_height)
        self.canvases.append(canvas)
        return canvas

    def add_canvas(self, canvas: GpuCanvas):
        if canvas not in self.canvases:
            self.canvases.append(canvas)
        return canvas

    def register_canvas(self, canvas: GpuCanvas):
        """Convenience alias for add_canvas."""
        return self.add_canvas(canvas)


    def remove_canvas(self, canvas: GpuCanvas):
        if canvas in self.canvases:
            self.canvases.remove(canvas)

    def register(self):
        """Registers the dynamic operator and watchdog timer."""
        if self.operator_cls:
            try:
                bpy.utils.register_class(self.operator_cls)
            except Exception:
                pass

        if not bpy.app.timers.is_registered(self.watchdog_timer_check):
            bpy.app.timers.register(self.watchdog_timer_check)

    def unregister(self):
        """Unregisters watchdog timer, tears down draw handler and operator."""
        if bpy.app.timers.is_registered(self.watchdog_timer_check):
            bpy.app.timers.unregister(self.watchdog_timer_check)

        self.teardown_draw_handler()

        if self.operator_cls:
            try:
                bpy.utils.unregister_class(self.operator_cls)
            except Exception:
                pass

    def _is_any_canvas_active(self) -> bool:
        if not HAS_ENGINE or not my_engine:
            return False
        ui_region = GpuDrawManager.get_3d_view_ui_region()
        if not ui_region or ui_region.width <= 1:
            return False

        active_cat = my_engine.get_active_category(ui_region.as_pointer())
        if not active_cat:
            return False

        for c in self.canvases:
            if c.category == active_cat:
                return True
        return False

    def watchdog_timer_check(self):
        """Runs continuously to mount/unmount the GPU draw handler and modal operator."""
        active = self._is_any_canvas_active()

        # STATE 1: At least one canvas active -> start up draw handler & modal
        if active and self.draw_handle is None:
            self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_panel_boxes, (), 'UI', 'POST_PIXEL'
            )

            if not self.is_modal_running:
                self.is_modal_running = True
                op_idname = self.operator_cls.bl_idname
                mod_name, sub_name = op_idname.split(".")
                try:
                    getattr(getattr(bpy.ops, mod_name), sub_name)('INVOKE_DEFAULT')
                except Exception as e:
                    print(f"[{self.addon_id}] Failed to invoke modal operator {op_idname}: {e}")

            GpuDrawManager.tag_redraw_all_3d_views()

        # STATE 2: Inactive -> tear down draw handler & signal modal to exit
        elif not active and self.draw_handle is not None:
            self.teardown_draw_handler()
            GpuDrawManager.tag_redraw_all_3d_views()

        return TIMER_INTERVAL

    def teardown_draw_handler(self):
        if self.draw_handle is not None:
            self.is_modal_running = False
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'UI')
            except Exception:
                pass
            self.draw_handle = None

    def draw_panel_boxes(self):
        if not HAS_ENGINE or not my_engine:
            return

        ui_region = GpuDrawManager.get_3d_view_ui_region()
        if not ui_region or ui_region.width <= 1:
            return

        active_category = my_engine.get_active_category(ui_region.as_pointer())
        panels = my_engine.get_region_panels(ui_region.as_pointer())
        scroll = my_engine.get_region_scroll(ui_region.as_pointer())
        scroll_ymax = scroll.get('cur_ymax', 0) if scroll else 0

        # Build lookup of open panels
        open_panels_by_label = {}
        for p in panels:
            if p.get('is_open', False):
                open_panels_by_label[p['label']] = p

        gpu.state.blend_set('ALPHA')
        region_w = ui_region.width
        region_h = ui_region.height

        for canvas in self.canvases:
            # 1. Check if canvas category matches active tab
            if canvas.category != active_category:
                canvas.is_visible = False
                canvas.current_rect = None
                continue

            # 2. Check if panel is present and open
            p = open_panels_by_label.get(canvas.panel_label)
            if not p:
                canvas.is_visible = False
                canvas.current_rect = None
                continue

            # 3. Calculate panel screen coordinates
            x = p['offset_x']
            y = region_h + p['offset_y'] - scroll_ymax
            w = p['size_x']
            h = p['size_y']

            canvas.current_rect = (x, y, w, h)
            canvas.is_visible = True

            scissor_x = max(0, int(x))
            scissor_y = max(0, int(y))
            scissor_w = max(0, min(int(w), int(region_w - scissor_x)))
            scissor_h = max(0, min(int(h), int(region_h - scissor_y)))

            if scissor_w <= 0 or scissor_h <= 0:
                continue

            gpu.state.scissor_test_set(True)
            gpu.state.scissor_set(scissor_x, scissor_y, scissor_w, scissor_h)

            # Solid background to prevent 3D viewport bleed
            try:
                from ..widgets.theme import BlenderTheme
            except ImportError:
                from ..bl_ui_widgets.theme import BlenderTheme

            bg_verts = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
            bg_indices = ((0, 1, 2), (2, 3, 0))
            shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
            bg_batch = batch_for_shader(shader_2d, 'TRIS', {"pos": bg_verts}, indices=bg_indices)
            shader_2d.uniform_float("color", BlenderTheme.BG_PANEL)
            bg_batch.draw(shader_2d)

            # Update layout sizes
            for widget in canvas.widgets:
                if hasattr(widget, "update_layout"):
                    widget.update_layout(w, h)

            # Draw canvas elements relative to panel origin (x, y)
            for widget in canvas.widgets:
                if widget.visible:
                    widget.draw(origin_x=x, origin_y=y)

            # Reset scissor for floating popups/overlays
            gpu.state.scissor_test_set(False)

            for widget in canvas.widgets:
                if widget.visible and hasattr(widget, "draw_overlay"):
                    widget.draw_overlay(origin_x=x, origin_y=y)

        gpu.state.scissor_test_set(False)
        gpu.state.blend_set('NONE')

    def handle_event(self, context, event) -> str:
        ui_region = GpuDrawManager.get_3d_view_ui_region()
        if not ui_region:
            return "PASS_THROUGH"

        rx = event.mouse_x - ui_region.x
        ry = event.mouse_y - ui_region.y

        # Check for focused widget
        focused_widget = None
        for canvas in self.canvases:
            if not canvas.is_visible:
                continue
            for w in canvas.widgets:
                f = self._find_focused(w)
                if f:
                    focused_widget = f
                    break
            if focused_widget:
                break

        # Keyboard routing for focused widget
        is_mouse_or_timer = event.type in {'TIMER', 'MOUSEMOVE', 'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
        if focused_widget and not is_mouse_or_timer:
            focused_widget.handle_keyboard_event(event)
            GpuDrawManager.tag_redraw_all_3d_views()
            return "RUNNING_MODAL"

        # Check if any widget holds active drag capture
        any_dragging = False
        for canvas in self.canvases:
            if not canvas.is_visible:
                continue
            for w in canvas.widgets:
                if self._check_dragging(w):
                    any_dragging = True
                    break
            if any_dragging:
                break

        # Defocus on click outside
        if not any_dragging and not (0 <= rx <= ui_region.width and 0 <= ry <= ui_region.height):
            if focused_widget and event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                focused_widget.is_focused = False
                if hasattr(focused_widget, 'on_commit') and focused_widget.on_commit:
                    try:
                        focused_widget.on_commit(focused_widget, focused_widget.text)
                    except Exception:
                        pass
                GpuDrawManager.tag_redraw_all_3d_views()

            cleared = False
            for canvas in self.canvases:
                for w in canvas.widgets:
                    if self._clear_hover(w):
                        cleared = True
            if cleared:
                GpuDrawManager.tag_redraw_all_3d_views()
            return "PASS_THROUGH"

        needs_redraw = False
        event_consumed = False

        for canvas in self.canvases:
            if not canvas.is_visible or not canvas.current_rect:
                continue

            cx, cy, cw, ch = canvas.current_rect
            inside_canvas = (cx <= rx <= cx + cw and cy <= ry <= cy + ch)

            if not inside_canvas and not any_dragging:
                for w in canvas.widgets:
                    if self._clear_hover(w):
                        needs_redraw = True
                continue

            for widget in canvas.widgets:
                consumed = widget.handle_event(
                    event=event,
                    mouse_x=rx,
                    mouse_y=ry,
                    origin_x=cx,
                    origin_y=cy
                )
                if consumed:
                    needs_redraw = True
                    event_consumed = True

        if needs_redraw:
            GpuDrawManager.tag_redraw_all_3d_views()

        if event_consumed and event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'}:
            return "RUNNING_MODAL"

        return "PASS_THROUGH"

    def _find_focused(self, widget):
        if getattr(widget, 'is_focused', False) and hasattr(widget, 'handle_keyboard_event'):
            return widget
        if hasattr(widget, 'children'):
            for c in widget.children:
                f = self._find_focused(c)
                if f:
                    return f
        return None

    def _check_dragging(self, widget) -> bool:
        if getattr(widget, 'is_dragging', False):
            return True
        if hasattr(widget, 'children'):
            for c in widget.children:
                if self._check_dragging(c):
                    return True
        return False

    def _clear_hover(self, widget) -> bool:
        cleared = False
        if getattr(widget, 'hovered', False):
            widget.hovered = False
            cleared = True
        if getattr(widget, 'is_hovered', False):
            widget.is_hovered = False
            cleared = True
        if getattr(widget, 'pressed', False):
            widget.pressed = False
            cleared = True
        if hasattr(widget, 'children'):
            for c in widget.children:
                if self._clear_hover(c):
                    cleared = True
        return cleared


# Default manager for simple single-addon usage
default_manager = GpuManager(addon_id="blgpu")
default_canvas = default_manager.create_canvas(category="My Engine", panel_label="Custom GPU Engine")
panel_widgets = default_canvas.widgets
