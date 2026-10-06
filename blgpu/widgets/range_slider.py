import gpu
import math
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIRangeSlider(UIElement):
    """
    Dual-Handle Range Slider widget.
    Allows defining an active numerical interval [val_min, val_max] in a single track.
    Features:
    - Independent draggable Min and Max handles.
    - Draggable central span to shift the entire interval.
    - Automatic clamping (val_min <= val_max).
    - Sub-pixel anti-aliased rendering.
    - Live HUD readout of the active interval.
    """

    def __init__(
        self,
        text="Range",
        min_range=0.0,
        max_range=1.0,
        val_min=0.2,
        val_max=0.8,
        step=0.01,
        precision=2,
        x=0,
        y=0,
        width=200,
        height=38,
        corner_radius=3.5,
        on_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.min_range = float(min_range)
        self.max_range = float(max_range)
        self.val_min = max(self.min_range, min(float(val_min), self.max_range))
        self.val_max = max(self.val_min, min(float(val_max), self.max_range))
        self.step = float(step)
        self.precision = int(precision)
        self.corner_radius = corner_radius
        self.on_change = on_change

        # Interaction state
        self.drag_mode = None  # 'MIN', 'MAX', 'SPAN'
        self.hover_target = None  # 'MIN', 'MAX', 'SPAN', 'TRACK'
        self.drag_start_x = 0.0
        self.drag_start_min = 0.0
        self.drag_start_max = 0.0

        # Colors
        self.track_bg = BlenderTheme.BG_INSET
        self.track_border = BlenderTheme.BORDER_DARK
        self.span_color = BlenderTheme.PRIMARY_BLUE
        self.span_hover = BlenderTheme.PRIMARY_BLUE_HOVER
        self.handle_bg = (0.26, 0.26, 0.26, 1.0)
        self.handle_hover = (0.35, 0.35, 0.35, 1.0)
        self.handle_active = (0.45, 0.45, 0.45, 1.0)
        self.handle_border = (0.6, 0.6, 0.6, 0.9)

    def _get_track_bounds(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        # Header takes top 16px
        header_h = 16.0 * scale
        margin_x = 8.0 * scale
        track_h = 8.0 * scale

        tx = abs_x + margin_x
        tw = max(20.0, self.width - margin_x * 2.0)
        ty = abs_y + (self.height - header_h - track_h) * 0.5

        return tx, ty, tw, track_h

    def _val_to_x(self, val, tx, tw):
        span = max(1e-6, self.max_range - self.min_range)
        norm = (val - self.min_range) / span
        return tx + norm * tw

    def _x_to_val(self, x, tx, tw, snap=False):
        norm = max(0.0, min(1.0, (x - tx) / max(1.0, tw)))
        val = self.min_range + norm * (self.max_range - self.min_range)
        if snap and self.step > 0:
            val = round(val / self.step) * self.step
        return round(val, self.precision)

    def _get_handle_rects(self, tx, ty, tw, th):
        scale = BlenderTheme.get_ui_scale()
        hw = 10.0 * scale
        hh = 18.0 * scale

        hx_min = self._val_to_x(self.val_min, tx, tw)
        hx_max = self._val_to_x(self.val_max, tx, tw)
        hy = ty + (th - hh) * 0.5

        rect_min = (hx_min - hw * 0.5, hy, hw, hh)
        rect_max = (hx_max - hw * 0.5, hy, hw, hh)
        return rect_min, rect_max

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        tx, ty, tw, th = self._get_track_bounds(origin_x, origin_y)
        rect_min, rect_max = self._get_handle_rects(tx, ty, tw, th)

        # 1. Header (Label on left, live range readout on right)
        header_y = abs_y + self.height - (13.0 * scale)
        if self.text:
            self.draw_text(self.text, abs_x + 2.0, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        range_str = f"[{self.val_min:.{self.precision}f} .. {self.val_max:.{self.precision}f}]"
        readout_color = BlenderTheme.PRIMARY_BLUE if self.drag_mode else BlenderTheme.TEXT_MAIN
        self.draw_text(range_str, abs_x + self.width - (80.0 * scale), header_y, font_id=0, size=10, color=readout_color)

        # 2. Recessed Background Track
        track_r = th * 0.5
        self.draw_rounded_rect(tx, ty, tw, th, track_r, self.track_bg)
        self.draw_rounded_rect_outline(tx, ty, tw, th, track_r, self.track_border, line_width=1.0)

        # 3. Active Interval Span Bar
        hx_min = self._val_to_x(self.val_min, tx, tw)
        hx_max = self._val_to_x(self.val_max, tx, tw)
        span_w = max(0.0, hx_max - hx_min)

        span_col = self.span_hover if (self.hover_target == 'SPAN' or self.drag_mode == 'SPAN') else self.span_color
        if span_w > 0:
            self.draw_rounded_rect(hx_min, ty, span_w, th, min(track_r, span_w * 0.5), span_col)

        # 4. Min & Max Draggable Handles (Pill shape)
        pill_r = 3.0 * scale
        for handle_rect, is_hover, is_drag in (
            (rect_min, self.hover_target == 'MIN', self.drag_mode == 'MIN'),
            (rect_max, self.hover_target == 'MAX', self.drag_mode == 'MAX'),
        ):
            hx, hy, hw, hh = handle_rect
            col = self.handle_active if is_drag else (self.handle_hover if is_hover else self.handle_bg)

            # Handle body
            self.draw_rounded_rect(hx, hy, hw, hh, pill_r, col)
            # Handle outline
            outline_col = (1.0, 1.0, 1.0, 0.9) if (is_drag or is_hover) else self.handle_border
            self.draw_rounded_rect_outline(hx, hy, hw, hh, pill_r, outline_col, line_width=1.0)

            # Center vertical grip line on handle
            cx = hx + hw * 0.5
            grip_pad = 4.0 * scale
            GpuShapes.draw_smooth_line(cx, hy + grip_pad, cx, hy + hh - grip_pad, (0.7, 0.7, 0.7, 0.8), line_width=1.0)

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        tx, ty, tw, th = self._get_track_bounds(origin_x, origin_y)
        rect_min, rect_max = self._get_handle_rects(tx, ty, tw, th)

        # Hit testing helpers (with 3px padding)
        def inside_rect(r, px, py):
            pad = 3.0 * scale
            return (r[0] - pad <= px <= r[0] + r[2] + pad) and (r[1] - pad <= py <= r[1] + r[3] + pad)

        hit_min = inside_rect(rect_min, mx, my)
        hit_max = inside_rect(rect_max, mx, my)

        hx_min = self._val_to_x(self.val_min, tx, tw)
        hx_max = self._val_to_x(self.val_max, tx, tw)
        hit_span = (hx_min <= mx <= hx_max) and (ty - 4.0 * scale <= my <= ty + th + 4.0 * scale)
        hit_track = (tx <= mx <= tx + tw) and (ty - 4.0 * scale <= my <= ty + th + 4.0 * scale)

        if not self.drag_mode:
            if hit_min:
                self.hover_target = 'MIN'
            elif hit_max:
                self.hover_target = 'MAX'
            elif hit_span:
                self.hover_target = 'SPAN'
            elif hit_track:
                self.hover_target = 'TRACK'
            else:
                self.hover_target = None

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                snap = event.ctrl
                if hit_min:
                    self.drag_mode = 'MIN'
                    return True
                elif hit_max:
                    self.drag_mode = 'MAX'
                    return True
                elif hit_span:
                    self.drag_mode = 'SPAN'
                    self.drag_start_x = mx
                    self.drag_start_min = self.val_min
                    self.drag_start_max = self.val_max
                    return True
                elif hit_track:
                    # Jump closest handle to clicked position
                    clicked_val = self._x_to_val(mx, tx, tw, snap=snap)
                    d_min = abs(clicked_val - self.val_min)
                    d_max = abs(clicked_val - self.val_max)
                    if d_min <= d_max:
                        self.val_min = min(clicked_val, self.val_max)
                        self.drag_mode = 'MIN'
                    else:
                        self.val_max = max(clicked_val, self.val_min)
                        self.drag_mode = 'MAX'
                    if self.on_change:
                        self.on_change(self.val_min, self.val_max)
                    return True

            elif event.value == 'RELEASE' and self.drag_mode:
                self.drag_mode = None
                return True

        elif event.type == 'MOUSEMOVE' and self.drag_mode:
            snap = event.ctrl
            current_val = self._x_to_val(mx, tx, tw, snap=snap)

            if self.drag_mode == 'MIN':
                self.val_min = max(self.min_range, min(current_val, self.val_max))
                if self.on_change:
                    self.on_change(self.val_min, self.val_max)
                return True

            elif self.drag_mode == 'MAX':
                self.val_max = max(self.val_min, min(current_val, self.max_range))
                if self.on_change:
                    self.on_change(self.val_min, self.val_max)
                return True

            elif self.drag_mode == 'SPAN':
                span_width = self.drag_start_max - self.drag_start_min
                dx = mx - self.drag_start_x
                d_val = (dx / max(1.0, tw)) * (self.max_range - self.min_range)

                new_min = self.drag_start_min + d_val
                new_max = self.drag_start_max + d_val

                if new_min < self.min_range:
                    new_min = self.min_range
                    new_max = new_min + span_width
                elif new_max > self.max_range:
                    new_max = self.max_range
                    new_min = new_max - span_width

                if snap and self.step > 0:
                    new_min = round(new_min / self.step) * self.step
                    new_max = new_min + span_width

                self.val_min = max(self.min_range, round(new_min, self.precision))
                self.val_max = min(self.max_range, round(new_max, self.precision))

                if self.on_change:
                    self.on_change(self.val_min, self.val_max)
                return True

        return False
