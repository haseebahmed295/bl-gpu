import time
import math
import colorsys
import gpu
from gpu_extras.batch import batch_for_shader
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIGradientRamp(UIElement):
    """
    Interactive Realtime Multi-Stop Color Gradient Ramp.
    Features:
    - Multi-color smooth continuous gradient bar rendered on GPU
    - Draggable color stops positioned underneath
    - Full floating HSV Color Picker popup to select specific colors for any stop
    - Configurable default_stops and max_stops / min_stops constraints
    - Double-click any stop pin or click active color swatch to open color picker
    - Realtime gradient re-rendering and callback on color/position changes
    """

    PALETTE = [
        (0.85, 0.25, 0.25, 1.0), # Red
        (0.95, 0.55, 0.15, 1.0), # Orange
        (0.95, 0.85, 0.20, 1.0), # Yellow
        (0.25, 0.80, 0.35, 1.0), # Green
        (0.20, 0.75, 0.85, 1.0), # Cyan
        (0.278, 0.447, 0.702, 1.0), # Blender Blue
        (0.65, 0.35, 0.85, 1.0), # Purple
        (0.95, 0.95, 0.95, 1.0), # White
    ]

    def __init__(
        self,
        stops=None,
        default_stops=None,
        max_stops=8,
        min_stops=2,
        x=0,
        y=0,
        width=200,
        height=54,
        corner_radius=None,
        border_width=None,
        border_color=None,
        on_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)

        self.max_stops = max(2, int(max_stops))
        self.min_stops = max(2, min(self.max_stops, int(min_stops)))

        # Default stops
        if default_stops is not None:
            self.default_stops = [[float(s[0]), tuple(s[1])] for s in default_stops]
        elif stops is not None:
            self.default_stops = [[float(s[0]), tuple(s[1])] for s in stops]
        else:
            self.default_stops = [
                [0.0, (0.08, 0.08, 0.12, 1.0)],
                [0.45, (0.278, 0.447, 0.702, 1.0)],
                [1.0, (1.0, 0.85, 0.35, 1.0)]
            ]

        # Active stops list: [pos (0.0 - 1.0), (r, g, b, a)]
        init_stops = stops if stops is not None else self.default_stops
        self.stops = [[float(s[0]), tuple(s[1])] for s in init_stops]
        self.stops.sort(key=lambda s: s[0])

        self.on_change = on_change
        self.active_stop_idx = min(len(self.stops) - 1, max(0, 1 if len(self.stops) > 1 else 0))
        self.hovered_stop_idx = -1
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS
        self.border_color = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH

        # Color picker popup state
        self.is_expanded = False
        self._active_target = None  # 'WHEEL', 'VAL', or None
        self._last_click_time = 0.0
        self._last_click_x = 0.0
        self._initial_color = self.active_color

        self.hue = 0.6
        self.sat = 0.6
        self.val = 0.8
        self._sync_hsv_from_active()

    @property
    def active_color(self):
        if 0 <= self.active_stop_idx < len(self.stops):
            return self.stops[self.active_stop_idx][1]
        return (1.0, 1.0, 1.0, 1.0)

    @active_color.setter
    def active_color(self, col):
        if 0 <= self.active_stop_idx < len(self.stops):
            self.stops[self.active_stop_idx][1] = tuple(col)
            if self.on_change:
                self.on_change(self, self.stops)

    def reset_to_default(self):
        """Resets stops back to default_stops."""
        self.stops = [[float(s[0]), tuple(s[1])] for s in self.default_stops]
        self.stops.sort(key=lambda s: s[0])
        self.active_stop_idx = min(len(self.stops) - 1, self.active_stop_idx)
        self.is_expanded = False
        self._sync_hsv_from_active()
        if self.on_change:
            self.on_change(self, self.stops)

    def _sync_hsv_from_active(self):
        col = self.active_color
        r, g, b = col[0], col[1], col[2]
        self._initial_color = tuple(col)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        self.hue = float(h)
        self.sat = float(s)
        self.val = float(v)

    def _apply_hsv_to_active(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue, self.sat, self.val)
        cur_col = self.stops[self.active_stop_idx][1]
        a = cur_col[3] if len(cur_col) > 3 else 1.0
        self.stops[self.active_stop_idx][1] = (float(r), float(g), float(b), float(a))
        if self.on_change:
            self.on_change(self, self.stops)

    def _bar_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        bar_h = 16.0 * scale
        bar_y = origin_y + self.y + self.height - bar_h - (2.0 * scale)
        return (origin_x + self.x, bar_y, self.width, bar_h)

    def _pin_center(self, pos, origin_x, origin_y):
        bx, by, bw, bh = self._bar_rect(origin_x, origin_y)
        scale = BlenderTheme.get_ui_scale()
        cx = bx + pos * bw
        cy = by - (7.0 * scale)
        return cx, cy

    def _swatch_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        sw = 44.0 * scale
        sh = 15.0 * scale
        sx = abs_x + self.width - sw
        sy = abs_y + (2.0 * scale)
        return sx, sy, sw, sh

    def _get_popup_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        pw = 175.0 * scale
        ph = 205.0 * scale
        px = abs_x + self.width - pw
        py = abs_y - ph - (4.0 * scale)
        if py < 10.0:
            py = abs_y + self.height + (4.0 * scale)
        return px, py, pw, ph

    def _get_wheel_geometry(self, px, py, pw, ph, scale):
        cx = px + pw * 0.5
        wheel_r = 38.0 * scale
        cy = py + ph - (26.0 * scale) - wheel_r
        return cx, cy, wheel_r

    def _get_slider_geometry(self, px, py, pw, ph, scale):
        vx = px + (12.0 * scale)
        vw = pw - (24.0 * scale)
        vh = 10.0 * scale
        vy = py + (38.0 * scale)
        return vx, vy, vw, vh

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        pin_r = 6.0 * scale
        bx, by, bw, bh = self._bar_rect(origin_x, origin_y)
        sw_x, sw_y, sw_w, sw_h = self._swatch_rect(origin_x, origin_y)
        inside_swatch = (sw_x <= mouse_x <= sw_x + sw_w) and (sw_y <= mouse_y <= sw_y + sw_h)
        inside_widget = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)

        # -------------------------------------------------------------
        # STATE A: Color Picker Popup is OPEN
        # -------------------------------------------------------------
        if self.is_expanded:
            px, py, pw, ph = self._get_popup_rect(origin_x, origin_y)
            cx, cy, wheel_r = self._get_wheel_geometry(px, py, pw, ph, scale)
            vx, vy, vw, vh = self._get_slider_geometry(px, py, pw, ph, scale)

            inside_popup = (px <= mouse_x <= px + pw) and (py <= mouse_y <= py + ph)
            close_x = px + pw - (20.0 * scale)
            close_y = py + ph - (20.0 * scale)
            inside_close = (close_x - 4 <= mouse_x <= close_x + 16) and (close_y - 4 <= mouse_y <= close_y + 16)

            dist_sq = (mouse_x - cx) ** 2 + (mouse_y - cy) ** 2
            hit_wheel = dist_sq <= ((wheel_r + 4.0 * scale) ** 2)
            hit_slider = (vx - 4.0 * scale <= mouse_x <= vx + vw + 4.0 * scale) and (vy - 3.0 * scale <= mouse_y <= vy + vh + 3.0 * scale)

            if event.type == 'LEFTMOUSE':
                if event.value == 'PRESS':
                    if inside_close:
                        self.is_expanded = False
                        self._active_target = None
                        return True

                    if hit_wheel:
                        self._active_target = 'WHEEL'
                        self._update_from_wheel(mouse_x, mouse_y, cx, cy, wheel_r)
                        return True

                    if hit_slider:
                        self._active_target = 'VAL'
                        self._update_from_slider(mouse_x, vx, vw)
                        return True

                    # Check palette swatches at bottom of popup
                    palette_y = py + (12.0 * scale)
                    palette_h = 16.0 * scale
                    num_pal = len(self.PALETTE)
                    pal_spacing = 4.0 * scale
                    total_pal_w = pw - (24.0 * scale)
                    pal_box_w = (total_pal_w - (num_pal - 1) * pal_spacing) / num_pal

                    for i, pcol in enumerate(self.PALETTE):
                        pbx = px + (12.0 * scale) + i * (pal_box_w + pal_spacing)
                        if (pbx <= mouse_x <= pbx + pal_box_w) and (palette_y <= mouse_y <= palette_y + palette_h):
                            h, s, v = colorsys.rgb_to_hsv(pcol[0], pcol[1], pcol[2])
                            self.hue = float(h)
                            self.sat = float(s)
                            self.val = float(v)
                            self._apply_hsv_to_active()
                            return True

                    if inside_popup:
                        return True

                    # Clicked outside popup
                    self.is_expanded = False
                    return False

                elif event.value == 'RELEASE':
                    if self._active_target:
                        self._active_target = None
                        return True

            elif event.type == 'MOUSEMOVE':
                if self._active_target == 'WHEEL':
                    self._update_from_wheel(mouse_x, mouse_y, cx, cy, wheel_r)
                    return True
                elif self._active_target == 'VAL':
                    self._update_from_slider(mouse_x, vx, vw)
                    return True
                elif inside_popup:
                    return True

            return False

        # -------------------------------------------------------------
        # STATE B: Color Picker Popup is CLOSED (Main ramp interaction)
        # -------------------------------------------------------------
        # Check hover over stop pins
        hover_idx = -1
        for i, (pos, col) in enumerate(self.stops):
            cx, cy = self._pin_center(pos, origin_x, origin_y)
            if (mouse_x - cx)**2 + (mouse_y - cy)**2 <= (pin_r + 2)**2:
                hover_idx = i
                break

        if event.type == 'MOUSEMOVE':
            if self.is_dragging and 0 <= self.active_stop_idx < len(self.stops):
                new_pos = max(0.0, min(1.0, (mouse_x - bx) / max(1.0, bw)))
                self.stops[self.active_stop_idx][0] = round(new_pos, 3)
                if self.on_change:
                    self.on_change(self, self.stops)
                return True

            if hover_idx != self.hovered_stop_idx:
                self.hovered_stop_idx = hover_idx
                return True

        elif event.type == 'LEFTMOUSE':
            if event.value in {'PRESS', 'DOUBLE_CLICK'}:
                now = time.time()
                is_double = (event.value == 'DOUBLE_CLICK') or (
                    (now - self._last_click_time < 0.35) and abs(mouse_x - self._last_click_x) < 6
                )
                self._last_click_time = now
                self._last_click_x = mouse_x

                # 1. Click / Double-click on Stop Pin
                if hover_idx >= 0:
                    self.active_stop_idx = hover_idx
                    self._sync_hsv_from_active()
                    if is_double:
                        # Double click pin opens color picker popup
                        self.is_expanded = True
                        self.is_dragging = False
                    else:
                        self.is_dragging = True
                    return True

                # 2. Click on Active Color Swatch button to open color picker
                if inside_swatch:
                    self.is_expanded = True
                    self._sync_hsv_from_active()
                    return True

                # 3. Click on gradient bar to add a new stop (up to max_stops)
                if (bx <= mouse_x <= bx + bw) and (by <= mouse_y <= by + bh):
                    if len(self.stops) < self.max_stops:
                        new_pos = max(0.0, min(1.0, (mouse_x - bx) / max(1.0, bw)))
                        interp_col = self._sample_gradient(new_pos)
                        self.stops.append([round(new_pos, 3), interp_col])
                        self.stops.sort(key=lambda s: s[0])
                        for i, (pos, _) in enumerate(self.stops):
                            if abs(pos - new_pos) < 0.001:
                                self.active_stop_idx = i
                                break
                        self._sync_hsv_from_active()
                        self.is_dragging = True
                        if self.on_change:
                            self.on_change(self, self.stops)
                        return True
                    else:
                        # At max_stops limit: benign no-op, do NOT reset stops
                        return True

                # 4. Any other click inside the widget area: consume click, NEVER reset
                if inside_widget:
                    return True

            elif event.value == 'RELEASE':
                if self.is_dragging:
                    self.is_dragging = False
                    return True

        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            # Remove stop if more than min_stops remain
            if hover_idx >= 0 and len(self.stops) > self.min_stops:
                self.stops.pop(hover_idx)
                self.active_stop_idx = min(len(self.stops) - 1, max(0, self.active_stop_idx))
                self.hovered_stop_idx = -1
                self._sync_hsv_from_active()
                if self.on_change:
                    self.on_change(self, self.stops)
                return True

        return False

    def _update_from_wheel(self, mx, my, cx, cy, wheel_r):
        dx = mx - cx
        dy = my - cy
        dist = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        if angle < 0.0:
            angle += 2.0 * math.pi
        self.hue = float(angle / (2.0 * math.pi))
        self.sat = float(min(1.0, dist / max(1.0, wheel_r)))
        self._apply_hsv_to_active()

    def _update_from_slider(self, mx, vx, vw):
        self.val = float(max(0.0, min(1.0, (mx - vx) / max(1.0, vw))))
        self._apply_hsv_to_active()

    def _sample_gradient(self, t):
        sorted_stops = sorted(self.stops, key=lambda s: s[0])
        if t <= sorted_stops[0][0]:
            return sorted_stops[0][1]
        if t >= sorted_stops[-1][0]:
            return sorted_stops[-1][1]
        for i in range(len(sorted_stops) - 1):
            p0, c0 = sorted_stops[i]
            p1, c1 = sorted_stops[i + 1]
            if p0 <= t <= p1:
                fac = (t - p0) / max(0.0001, (p1 - p0))
                return (
                    c0[0] + (c1[0] - c0[0]) * fac,
                    c0[1] + (c1[1] - c0[1]) * fac,
                    c0[2] + (c1[2] - c0[2]) * fac,
                    1.0
                )
        return (1.0, 1.0, 1.0, 1.0)

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        bx, by, bw, bh = self._bar_rect(origin_x, origin_y)

        # Effective corner radius
        scaled_r = max(0.0, float(self.corner_radius) * scale)
        r = min(scaled_r, bw / 2.0, bh / 2.0)

        # 1. Build smoothly interpolated gradient mesh matching the exact boundary
        verts = []
        colors = []
        indices = []

        if r <= 0.5:
            # Sharp rectangle quads
            sorted_stops = sorted(self.stops, key=lambda s: s[0])
            full_stops = []
            if sorted_stops[0][0] > 0.0:
                full_stops.append((0.0, sorted_stops[0][1]))
            full_stops.extend([(s[0], s[1]) for s in sorted_stops])
            if sorted_stops[-1][0] < 1.0:
                full_stops.append((1.0, sorted_stops[-1][1]))

            for i in range(len(full_stops) - 1):
                p1, c1 = full_stops[i]
                p2, c2 = full_stops[i + 1]
                x1 = bx + p1 * bw
                x2 = bx + p2 * bw
                b = len(verts)
                verts.extend([(x1, by), (x2, by), (x2, by + bh), (x1, by + bh)])
                colors.extend([c1, c2, c2, c1])
                indices.extend([(b, b + 1, b + 2), (b, b + 2, b + 3)])
        else:
            # Rounded corner quad strip - exact circular arcs at ends
            x_vals = []
            steps_arc = 8
            for s in range(steps_arc + 1):
                ang = 0.5 * math.pi * (s / steps_arc)
                x_vals.append(bx + r * (1.0 - math.cos(ang)))

            for pos, _ in self.stops:
                sx = bx + pos * bw
                if bx + r < sx < bx + bw - r:
                    x_vals.append(sx)

            mid_steps = 24
            for s in range(mid_steps + 1):
                x_vals.append(bx + r + (bw - 2.0 * r) * (s / mid_steps))

            for s in range(steps_arc + 1):
                ang = 0.5 * math.pi * (s / steps_arc)
                x_vals.append(bx + bw - r + r * math.sin(ang))

            x_vals = sorted(list(set(round(val, 2) for val in x_vals)))

            slices = []
            for vx in x_vals:
                if vx < bx + r:
                    dx = (bx + r) - vx
                    dy = math.sqrt(max(0.0, r * r - dx * dx))
                    y_bot = by + r - dy
                    y_top = by + bh - r + dy
                elif vx > bx + bw - r:
                    dx = vx - (bx + bw - r)
                    dy = math.sqrt(max(0.0, r * r - dx * dx))
                    y_bot = by + r - dy
                    y_top = by + bh - r + dy
                else:
                    y_bot = by
                    y_top = by + bh

                t = max(0.0, min(1.0, (vx - bx) / max(1.0, bw)))
                col = self._sample_gradient(t)
                slices.append((vx, y_bot, y_top, col))

            for i in range(len(slices) - 1):
                x1, y1_bot, y1_top, c1 = slices[i]
                x2, y2_bot, y2_top, c2 = slices[i + 1]
                b = len(verts)
                verts.extend([(x1, y1_bot), (x2, y2_bot), (x2, y2_top), (x1, y1_top)])
                colors.extend([c1, c2, c2, c1])
                indices.extend([(b, b + 1, b + 2), (b, b + 2, b + 3)])

        shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')
        batch = batch_for_shader(shader_smooth, 'TRIS', {"pos": verts, "color": colors}, indices=indices)
        batch.draw(shader_smooth)

        # 2. Draw border outline perfectly aligned to the gradient mesh
        self.draw_rounded_rect_outline(bx, by, bw, bh, self.corner_radius, self.border_color, line_width=self.border_width)

        # 3. Draw draggable pins underneath
        pin_r = 5.0 * scale
        pin_border_w = max(1.0, 1.0 * scale)

        for i, (pos, col) in enumerate(self.stops):
            cx, cy = self._pin_center(pos, origin_x, origin_y)
            is_active = (i == self.active_stop_idx)
            is_hover = (i == self.hovered_stop_idx)

            # Arrow tip pointing to gradient bar
            tip_y = by - (1.0 * scale)
            tri_verts = ((cx, tip_y), (cx - pin_r, cy), (cx + pin_r, cy))
            batch_tri = batch_for_shader(self.shader_2d, 'TRIS', {"pos": tri_verts})
            self.shader_2d.uniform_float("color", col)
            batch_tri.draw(self.shader_2d)

            # Pin rounded body
            body_col = (1.0, 0.6, 0.1, 1.0) if is_active else ((0.9, 0.9, 0.9, 1.0) if is_hover else col)
            self.draw_rounded_rect(cx - pin_r, cy - pin_r, pin_r * 2.0, pin_r * 2.0, 2.0, body_col)
            outline_col = (1.0, 0.6, 0.1, 1.0) if is_active else (0.1, 0.1, 0.1, 1.0)
            self.draw_rounded_rect_outline(cx - pin_r, cy - pin_r, pin_r * 2.0, pin_r * 2.0, 2.0, outline_col, line_width=pin_border_w)

        # 4. Bottom Controls Row: Stop & Pos Readout + Active Stop Color Swatch Button
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        sw_x, sw_y, sw_w, sw_h = self._swatch_rect(origin_x, origin_y)

        if 0 <= self.active_stop_idx < len(self.stops):
            active_p, active_c = self.stops[self.active_stop_idx]
            info_str = f"Stop {self.active_stop_idx + 1}/{len(self.stops)}  Pos: {active_p:.3f}"
            self.draw_text(info_str, abs_x + 2.0 * scale, sw_y + 3.0 * scale, font_id=0, size=9, color=BlenderTheme.TEXT_MUTED)

            # Active Color Swatch button
            sw_border = BlenderTheme.BORDER_FOCUS if self.is_expanded else BlenderTheme.BORDER_DARK
            GpuShapes.draw_smooth_rounded_box(
                sw_x, sw_y, sw_w, sw_h,
                radius=3.0 * scale,
                fill_color=active_c,
                border_color=sw_border,
                border_width=1.0
            )

    def draw_overlay(self, origin_x, origin_y):
        """Draws the floating Color Picker dialog over all widgets."""
        if not self.visible or not self.is_expanded:
            return

        scale = BlenderTheme.get_ui_scale()
        px, py, pw, ph = self._get_popup_rect(origin_x, origin_y)
        cx, cy, wheel_r = self._get_wheel_geometry(px, py, pw, ph, scale)
        vx, vy, vw, vh = self._get_slider_geometry(px, py, pw, ph, scale)

        # 1. Floating Window Panel Backdrop with Drop-Shadow & Border
        GpuShapes.draw_smooth_rounded_box(
            px, py, pw, ph,
            radius=6.0 * scale,
            fill_color=(0.13, 0.13, 0.13, 0.98),
            border_color=(0.35, 0.35, 0.35, 0.9),
            border_width=1.0
        )

        curr_r, curr_g, curr_b = colorsys.hsv_to_rgb(self.hue, self.sat, self.val)

        # 2. Header Bar: Hex code & Initial vs Current comparison
        header_y = py + ph - (18.0 * scale)
        hex_str = f"#{int(curr_r * 255):02X}{int(curr_g * 255):02X}{int(curr_b * 255):02X}"
        self.draw_text(hex_str, px + (10.0 * scale), header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MAIN)

        comp_w = 32.0 * scale
        comp_h = 13.0 * scale
        comp_x = px + pw - comp_w - (24.0 * scale)
        comp_y = header_y + 1.0 * scale
        half_w = comp_w * 0.5

        # Initial color (left)
        self.draw_rect(comp_x, comp_y, half_w, comp_h, self._initial_color)
        # Current color (right)
        self.draw_rect(comp_x + half_w, comp_y, half_w, comp_h, (curr_r, curr_g, curr_b, 1.0))
        self.draw_rect_outline(comp_x, comp_y, comp_w, comp_h, BlenderTheme.BORDER_LIGHT, line_width=1.0)

        # Close button 'x'
        close_x = px + pw - (16.0 * scale)
        self.draw_text("x", close_x, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        # 3. Continuous HSV Color Wheel Disc (GPU Per-Pixel Shader)
        GpuShapes.draw_hsv_wheel(cx, cy, wheel_r, value=self.val, alpha=1.0)
        border_wheel = (1.0, 1.0, 1.0, 0.5) if self._active_target == 'WHEEL' else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_ring(cx, cy, wheel_r, border_wheel, thickness=1.0)

        # Reticle Puck (Hue & Saturation)
        angle = self.hue * 2.0 * math.pi
        puck_dist = self.sat * wheel_r
        puck_x = cx + math.cos(angle) * puck_dist
        puck_y = cy + math.sin(angle) * puck_dist
        puck_r = 4.5 * scale

        GpuShapes.draw_smooth_ring(puck_x, puck_y, puck_r + 1.0 * scale, (0.05, 0.05, 0.05, 0.9), thickness=1.2)
        GpuShapes.draw_smooth_ring(puck_x, puck_y, puck_r, (1.0, 1.0, 1.0, 1.0), thickness=1.5)
        GpuShapes.draw_smooth_circle(puck_x, puck_y, puck_r - 1.5 * scale, (curr_r, curr_g, curr_b, 1.0))

        # 4. Companion Value (Luminance) Slider
        pure_r, pure_g, pure_b = colorsys.hsv_to_rgb(self.hue, self.sat, 1.0)
        c_left = (0.0, 0.0, 0.0, 1.0)
        c_right = (pure_r, pure_g, pure_b, 1.0)

        quad_pos = ((vx, vy), (vx + vw, vy), (vx + vw, vy + vh), (vx, vy + vh))
        quad_cols = (c_left, c_right, c_right, c_left)

        shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')
        batch_val = batch_for_shader(shader_smooth, 'TRI_FAN', {"pos": quad_pos, "color": quad_cols})
        gpu.state.blend_set('ALPHA')
        batch_val.draw(shader_smooth)
        gpu.state.blend_set('NONE')

        val_border = (1.0, 1.0, 1.0, 0.5) if self._active_target == 'VAL' else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_rounded_rect_outline(vx, vy, vw, vh, radius=2.5 * scale, color=val_border, line_width=1.0)

        val_x = vx + self.val * vw
        GpuShapes.draw_smooth_line(val_x, vy - 1.0 * scale, val_x, vy + vh + 1.0 * scale, (0.05, 0.05, 0.05, 0.9), line_width=3.0 * scale)
        GpuShapes.draw_smooth_line(val_x, vy - 1.0 * scale, val_x, vy + vh + 1.0 * scale, (1.0, 1.0, 1.0, 1.0), line_width=1.5 * scale)

        val_str = f"Brightness: {int(self.val * 100)}%"
        self.draw_text(val_str, vx, vy - (11.0 * scale), font_id=0, size=8, color=BlenderTheme.TEXT_MUTED)

        # 5. Quick Preset Palette Swatches
        palette_y = py + (10.0 * scale)
        palette_h = 14.0 * scale
        num_pal = len(self.PALETTE)
        pal_spacing = 4.0 * scale
        total_pal_w = pw - (24.0 * scale)
        pal_box_w = (total_pal_w - (num_pal - 1) * pal_spacing) / num_pal

        for i, pcol in enumerate(self.PALETTE):
            bx = px + (12.0 * scale) + i * (pal_box_w + pal_spacing)
            GpuShapes.draw_smooth_rounded_box(
                bx, palette_y, pal_box_w, palette_h,
                radius=2.0 * scale,
                fill_color=pcol,
                border_color=(0.3, 0.3, 0.3, 0.8),
                border_width=1.0
            )

