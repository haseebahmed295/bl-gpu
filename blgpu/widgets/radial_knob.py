import gpu
import math
import time
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIRadialKnob(UIElement):
    """
    Rotary Knob / Radial Dial widget.
    Provides compact circular parameter adjustment (angles, rotation, audio/color grading dials).
    Features:
    - 270° glowing progress arc.
    - Radial perimeter tick marks.
    - Rotating pointer needle on knob face.
    - Vertical scrub dragging with Shift (precision) and Ctrl (snapping).
    - Double-click to reset to default value.
    - Sub-pixel anti-aliased rendering via GpuShapes.
    """

    def __init__(
        self,
        text="Angle",
        min_value=0.0,
        max_value=360.0,
        default_value=45.0,
        value=None,
        step=1.0,
        precision=1,
        unit="°",
        x=0,
        y=0,
        width=100,
        height=95,
        radius=22.0,
        on_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.min_value = float(min_value)
        self.max_value = float(max_value)
        self.default_value = float(default_value)
        self.value = float(value if value is not None else default_value)
        self.step = float(step)
        self.precision = int(precision)
        self.unit = unit
        self.radius = float(radius)
        self.on_change = on_change

        self.is_dragging = False
        self.is_hovered = False
        self.prev_mouse_x = 0.0
        self.prev_mouse_y = 0.0
        self._drag_val_float = float(self.value)
        self._is_shift_active = False
        self._last_click_time = 0.0

        # Colors
        self.track_bg = (0.22, 0.22, 0.22, 0.5)
        self.arc_color = BlenderTheme.PRIMARY_BLUE
        self.knob_bg = (0.22, 0.22, 0.22, 1.0)
        self.knob_hover = (0.28, 0.28, 0.28, 1.0)
        self.knob_active = (0.18, 0.18, 0.18, 1.0)
        self.needle_color = (0.95, 0.95, 0.95, 1.0)
        self.tick_color = (0.45, 0.45, 0.45, 0.7)

    def _get_knob_center(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx = abs_x + self.width * 0.5
        # Center in remaining vertical space below header and above readout
        cy = abs_y + (self.height * 0.5) + (2.0 * scale)
        return cx, cy

    def _get_angles(self):
        # 270 degree sweep: from 225 deg (bottom-left) to -45 deg (bottom-right)
        start_rad = math.radians(225.0)
        total_sweep = math.radians(270.0)

        span = max(1e-6, self.max_value - self.min_value)
        ratio = max(0.0, min(1.0, (self.value - self.min_value) / span))
        current_rad = start_rad - (ratio * total_sweep)
        end_rad = start_rad - total_sweep

        return start_rad, end_rad, current_rad, total_sweep

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx, cy = self._get_knob_center(origin_x, origin_y)
        r = self.radius * scale
        arc_r = r + 4.5 * scale

        start_rad, end_rad, current_rad, total_sweep = self._get_angles()

        # 1. Header Title
        if self.text:
            tw, _ = self.get_text_dimensions(self.text, font_id=0, size=10)
            self.draw_text(self.text, cx - tw * 0.5, abs_y + self.height - 12.0 * scale, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        # 2. Perimeter Tick Marks (Min, 25%, 50%, 75%, Max)
        tick_len = 3.0 * scale
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            ang = start_rad - (frac * total_sweep)
            cos_a = math.cos(ang)
            sin_a = math.sin(ang)
            t_in = arc_r + 2.0 * scale
            t_out = t_in + tick_len
            GpuShapes.draw_smooth_line(
                cx + cos_a * t_in, cy + sin_a * t_in,
                cx + cos_a * t_out, cy + sin_a * t_out,
                self.tick_color,
                line_width=1.0
            )

        # 3. Background Inactive Arc Track (24 samples)
        arc_samples = 28
        track_pts = []
        for i in range(arc_samples + 1):
            ang = start_rad - (i / arc_samples) * total_sweep
            track_pts.append((cx + math.cos(ang) * arc_r, cy + math.sin(ang) * arc_r))
        GpuShapes.draw_smooth_polyline(track_pts, self.track_bg, line_width=max(2.0, 2.0 * scale))

        # 4. Glowing Active Progress Arc (from start_rad to current_rad)
        span = max(1e-6, self.max_value - self.min_value)
        ratio = max(0.0, min(1.0, (self.value - self.min_value) / span))
        if ratio > 0.005:
            active_samples = max(2, int(arc_samples * ratio))
            active_pts = []
            for i in range(active_samples + 1):
                ang = start_rad - (i / active_samples) * (ratio * total_sweep)
                active_pts.append((cx + math.cos(ang) * arc_r, cy + math.sin(ang) * arc_r))
            arc_col = BlenderTheme.PRIMARY_BLUE_HOVER if (self.is_dragging or self.is_hovered) else self.arc_color
            GpuShapes.draw_smooth_polyline(active_pts, arc_col, line_width=max(2.5, 2.5 * scale))

        # 5. Circular Knob Body
        body_col = self.knob_active if self.is_dragging else (self.knob_hover if self.is_hovered else self.knob_bg)
        GpuShapes.draw_smooth_circle(cx, cy, r, body_col)
        outline_col = (1.0, 1.0, 1.0, 0.8) if (self.is_dragging or self.is_hovered) else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_ring(cx, cy, r, outline_col, thickness=1.0)

        # Inner subtle bevel ring
        GpuShapes.draw_smooth_ring(cx, cy, r * 0.75, (0.15, 0.15, 0.15, 0.6), thickness=1.0)

        # 6. Rotating Pointer Needle
        n_in = r * 0.30
        n_out = r * 0.88
        nx1 = cx + math.cos(current_rad) * n_in
        ny1 = cy + math.sin(current_rad) * n_in
        nx2 = cx + math.cos(current_rad) * n_out
        ny2 = cy + math.sin(current_rad) * n_out
        GpuShapes.draw_smooth_line(nx1, ny1, nx2, ny2, self.needle_color, line_width=max(2.0, 2.0 * scale))

        # Center micro-pivot dot
        GpuShapes.draw_smooth_circle(cx, cy, 2.0 * scale, (0.8, 0.8, 0.8, 0.9))

        # 7. Value Readout (Bottom centered)
        is_fine = self.is_dragging and getattr(self, '_is_shift_active', False)
        if is_fine:
            val_str = f"{self.value:.{self.precision + 2}f}{self.unit}"
        elif self.value % 1 != 0 and self.precision == 0:
            val_str = f"{self.value:.2f}".rstrip('0').rstrip('.') + self.unit
        else:
            val_str = f"{self.value:.{self.precision}f}{self.unit}"

        vw, _ = self.get_text_dimensions(val_str, font_id=0, size=10)
        readout_col = BlenderTheme.PRIMARY_BLUE if self.is_dragging else BlenderTheme.TEXT_MAIN
        self.draw_text(val_str, cx - vw * 0.5, abs_y + 2.0 * scale, font_id=0, size=10, color=readout_col)

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        cx, cy = self._get_knob_center(origin_x, origin_y)
        dist_sq = (mx - cx) ** 2 + (my - cy) ** 2
        hit_radius = (self.radius + 8.0) * scale
        hit = dist_sq <= (hit_radius * hit_radius)

        self.is_hovered = hit or self.is_dragging

        if event.type == 'LEFTMOUSE':
            if event.value in {'PRESS', 'DOUBLE_CLICK'} and hit:
                now = time.time()
                # Double click to reset to default
                if (event.value == 'DOUBLE_CLICK') or (now - self._last_click_time < 0.28):
                    self.value = self.default_value
                    self._drag_val_float = float(self.default_value)
                    self.is_dragging = False
                    self._is_shift_active = False
                    self._last_click_time = 0.0
                    if self.on_change:
                        self.on_change(self.value)
                    return True

                self._last_click_time = now
                self.is_dragging = True
                self.prev_mouse_x = mx
                self.prev_mouse_y = my
                self._drag_val_float = float(self.value)
                self._is_shift_active = bool(getattr(event, 'shift', False))
                return True

            elif event.value == 'RELEASE' and self.is_dragging:
                self.is_dragging = False
                self._is_shift_active = False
                return True

        elif event.type == 'MOUSEMOVE' and self.is_dragging:
            self._is_shift_active = bool(getattr(event, 'shift', False))
            prev_x = self.prev_mouse_x
            prev_y = self.prev_mouse_y
            self.prev_mouse_x = mx
            self.prev_mouse_y = my

            dx = mx - prev_x
            dy = my - prev_y

            if abs(dx) < 1e-5 and abs(dy) < 1e-5:
                return False

            span = self.max_value - self.min_value
            total_sweep = math.radians(270.0)

            # Circular & Linear tracking using both X and Y positions
            r = math.hypot(mx - cx, my - cy)
            linear_delta = ((dx + dy) / (140.0 * scale)) * span

            if r < 6.0 * scale:
                # Center deadzone: use linear delta
                delta_val = linear_delta
            else:
                prev_ang = math.atan2(prev_y - cy, prev_x - cx)
                curr_ang = math.atan2(my - cy, mx - cx)
                d_ang = curr_ang - prev_ang

                # Normalize d_ang to [-pi, pi]
                while d_ang > math.pi:
                    d_ang -= 2.0 * math.pi
                while d_ang < -math.pi:
                    d_ang += 2.0 * math.pi

                # Clockwise rotation: math angle decreases (d_ang < 0), so -d_ang is positive
                angular_delta = (-d_ang / total_sweep) * span

                # If movement is purely radial (directly away/towards center), d_ang is ~0.
                # In that case, use linear_delta (dx + dy) to support straight drags.
                if abs(d_ang) < 0.002 and (abs(dx) > 0.4 or abs(dy) > 0.4):
                    delta_val = linear_delta
                else:
                    delta_val = angular_delta

            # Precision mode (Shift) -> 10x finer adjustment
            if self._is_shift_active:
                delta_val *= 0.1

            # Accumulate in high-precision float
            self._drag_val_float += delta_val
            self._drag_val_float = max(self.min_value, min(self.max_value, self._drag_val_float))

            # Snapping & Rounding
            if getattr(event, 'ctrl', False) and self.step > 0:
                step_val = (self.step * 0.1) if self._is_shift_active else self.step
                new_val = round(self._drag_val_float / step_val) * step_val
            else:
                effective_prec = (self.precision + 2) if self._is_shift_active else self.precision
                new_val = round(self._drag_val_float, effective_prec)

            new_val = max(self.min_value, min(self.max_value, new_val))
            if new_val != self.value:
                self.value = new_val
                if self.on_change:
                    self.on_change(self.value)
            return True

        return False
