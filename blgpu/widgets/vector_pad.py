import gpu
import math
import time
from gpu_extras.batch import batch_for_shader
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIVectorPad(UIElement):
    """
    Interactive 2D Vector / XY Trackpad widget.
    Enables simultaneous 2-axis vector manipulation (UV coordinates, direction vectors,
    pan/tilt, forces) inside Blender's N-Panel.
    """

    def __init__(
        self,
        text="2D Vector",
        min_x=-1.0,
        max_x=1.0,
        min_y=-1.0,
        max_y=1.0,
        default_x=0.0,
        default_y=0.0,
        value_x=None,
        value_y=None,
        precision=2,
        width=140,
        height=130,
        corner_radius=4.0,
        border_width=None,
        border_color=None,
        on_change=None
    ):
        super().__init__(x=0, y=0, width=width, height=height)
        self.text = text
        self.min_x = float(min_x)
        self.max_x = float(max_x)
        self.min_y = float(min_y)
        self.max_y = float(max_y)

        self.default_x = float(default_x)
        self.default_y = float(default_y)
        self.value_x = float(value_x if value_x is not None else default_x)
        self.value_y = float(value_y if value_y is not None else default_y)

        self.precision = precision
        self.corner_radius = corner_radius
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.border_color = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.on_change = on_change

        self.is_dragging = False
        self.is_hovered = False
        self._last_click_time = 0.0

        # Colors
        self.bg_color = (0.13, 0.13, 0.13, 1.0)
        self.grid_color = (0.22, 0.22, 0.22, 0.7)
        self.axis_color = (0.35, 0.35, 0.35, 0.9)
        self.vector_line_color = (0.28, 0.58, 0.95, 0.45)
        self.puck_color = BlenderTheme.PRIMARY_BLUE
        self.puck_border_color = (1.0, 1.0, 1.0, 0.9)

    def _get_pad_bounds(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        # Reserve top 18px for label & readout
        header_h = 18.0 * scale
        pad_margin = 2.0 * scale

        px = abs_x + pad_margin
        py = abs_y + pad_margin
        pw = max(10.0, self.width - pad_margin * 2.0)
        ph = max(10.0, self.height - header_h - pad_margin * 2.0)

        return px, py, pw, ph

    def _val_to_pad_pos(self, px, py, pw, ph):
        # Normalize to 0..1
        range_x = max(1e-6, self.max_x - self.min_x)
        range_y = max(1e-6, self.max_y - self.min_y)

        nx = (self.value_x - self.min_x) / range_x
        ny = (self.value_y - self.min_y) / range_y

        puck_x = px + nx * pw
        puck_y = py + ny * ph
        return puck_x, puck_y

    def _pad_pos_to_val(self, mx, my, px, py, pw, ph, snap_step=None):
        range_x = self.max_x - self.min_x
        range_y = self.max_y - self.min_y

        nx = max(0.0, min(1.0, (mx - px) / max(1.0, pw)))
        ny = max(0.0, min(1.0, (my - py) / max(1.0, ph)))

        val_x = self.min_x + nx * range_x
        val_y = self.min_y + ny * range_y

        if snap_step and snap_step > 0:
            val_x = round(val_x / snap_step) * snap_step
            val_y = round(val_y / snap_step) * snap_step

        val_x = max(self.min_x, min(self.max_x, round(val_x, self.precision)))
        val_y = max(self.min_y, min(self.max_y, round(val_y, self.precision)))
        return val_x, val_y

    def draw(self, origin_x=0, origin_y=0):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        px, py, pw, ph = self._get_pad_bounds(origin_x, origin_y)

        # 1. Header (Title on left, coordinate readout on right)
        header_y = abs_y + self.height - (14.0 * scale)
        if self.text:
            self.draw_text(self.text, abs_x + 2.0, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        coord_str = f"X: {self.value_x:+.{self.precision}f}  Y: {self.value_y:+.{self.precision}f}"
        readout_color = BlenderTheme.PRIMARY_BLUE if self.is_dragging else BlenderTheme.TEXT_MAIN
        # Right align readout text
        self.draw_text(coord_str, abs_x + self.width - (110.0 * scale), header_y, font_id=0, size=10, color=readout_color)

        # 2. Recessed Pad Background
        r = self.corner_radius * scale
        pad_bg = (0.16, 0.16, 0.16, 1.0) if self.is_hovered else self.bg_color
        self.draw_rounded_rect(px, py, pw, ph, r, pad_bg)

        # 3. Grid Lines & Axis Center Crosshair
        center_val_x = (self.min_x + self.max_x) * 0.5
        center_val_y = (self.min_y + self.max_y) * 0.5
        range_x = max(1e-6, self.max_x - self.min_x)
        range_y = max(1e-6, self.max_y - self.min_y)

        cx = px + ((center_val_x - self.min_x) / range_x) * pw
        cy = py + ((center_val_y - self.min_y) / range_y) * ph

        line_w = max(1.0, 1.0 * scale)

        # Polar reference circle at 50% & 100% radius
        r_circ_max = min(pw, ph) * 0.46
        for factor in (0.5, 1.0):
            rf = r_circ_max * factor
            GpuShapes.draw_smooth_ring(cx, cy, rf, self.grid_color, thickness=line_w)

        # Center Axis crosshairs
        axis_lines = [
            (px, cy), (px + pw, cy),
            (cx, py), (cx, py + ph)
        ]
        GpuShapes.draw_smooth_lines(axis_lines, self.axis_color, line_width=line_w)

        # 4. Connecting Vector Ray from Center to Puck
        puck_x, puck_y = self._val_to_pad_pos(px, py, pw, ph)
        GpuShapes.draw_smooth_line(cx, cy, puck_x, puck_y, self.vector_line_color, line_width=max(1.5, 1.5 * scale))

        # 5. Interactive Draggable Puck Handle
        puck_r = (7.0 if self.is_dragging else (6.0 if self.is_hovered else 5.0)) * scale

        # Outer halo glow when active
        if self.is_dragging or self.is_hovered:
            halo_r = puck_r + 3.0 * scale
            halo_col = (self.puck_color[0], self.puck_color[1], self.puck_color[2], 0.25)
            GpuShapes.draw_smooth_circle(puck_x, puck_y, halo_r, halo_col)

        # Puck filled body
        GpuShapes.draw_smooth_circle(puck_x, puck_y, puck_r, self.puck_color)

        # Puck crisp outline
        GpuShapes.draw_smooth_ring(puck_x, puck_y, puck_r, self.puck_border_color, thickness=line_w)

        # Puck center white micro-dot
        dot_r = max(1.0, 1.5 * scale)
        GpuShapes.draw_smooth_circle(puck_x, puck_y, dot_r, (1.0, 1.0, 1.0, 1.0))

        # 6. Recessed Outer Border
        outline_col = BlenderTheme.BORDER_LIGHT if (self.is_hovered or self.is_dragging) else self.border_color
        self.draw_rounded_rect_outline(px, py, pw, ph, r, outline_col, line_width=self.border_width)
        gpu.state.blend_set('NONE')

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)
        px, py, pw, ph = self._get_pad_bounds(origin_x, origin_y)

        # Expand hit target slightly for puck handle
        hit_pad = (px - 5.0 <= mx <= px + pw + 5.0) and (py - 5.0 <= my <= py + ph + 5.0)
        self.is_hovered = hit_pad

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and hit_pad:
                now = time.time()
                # Double click to reset to default
                if now - self._last_click_time < 0.28:
                    self.value_x = self.default_x
                    self.value_y = self.default_y
                    self.is_dragging = False
                    if self.on_change:
                        self.on_change(self.value_x, self.value_y)
                    return True

                self._last_click_time = now
                self.is_dragging = True

                snap = 0.1 if event.ctrl else None
                self.value_x, self.value_y = self._pad_pos_to_val(mx, my, px, py, pw, ph, snap_step=snap)
                if self.on_change:
                    self.on_change(self.value_x, self.value_y)
                return True

            elif event.value == 'RELEASE' and self.is_dragging:
                self.is_dragging = False
                return True

        elif event.type == 'MOUSEMOVE' and self.is_dragging:
            snap = 0.1 if event.ctrl else None
            self.value_x, self.value_y = self._pad_pos_to_val(mx, my, px, py, pw, ph, snap_step=snap)
            if self.on_change:
                self.on_change(self.value_x, self.value_y)
            return True

        return False
