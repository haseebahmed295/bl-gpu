import gpu
import math
import time
import colorsys
from gpu_extras.batch import batch_for_shader
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIColorWheel(UIElement):
    """
    Embedded Continuous HSV Color Wheel widget.
    Provides live circular color picking inside the panel layout (impossible in standard Blender UI).
    Features:
    - Real-time continuous HSV disc evaluated per-pixel via custom GPU shader.
    - Draggable Hue & Saturation reticle puck with high-contrast dual ring.
    - Companion horizontal Value (Luminance/Brightness) gradient slider.
    - Live #HEX and RGB swatch preview.
    - Shift modifier for fine adjustments, Ctrl modifier for hue angle snapping.
    - Double click wheel center to reset saturation, double click slider to reset brightness.
    """

    def __init__(
        self,
        text="Color Wheel",
        default_color=(0.25, 0.65, 1.0, 1.0),
        x=0,
        y=0,
        width=150,
        height=145,
        wheel_radius=38.0,
        on_color_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.on_color_change = on_color_change
        self.wheel_radius = float(wheel_radius)

        r, g, b = default_color[0], default_color[1], default_color[2]
        self.alpha = default_color[3] if len(default_color) > 3 else 1.0
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        self.hue = float(h)
        self.sat = float(s)
        self.val = float(v)

        self._active_target = None  # 'WHEEL', 'VAL', or None
        self._last_wheel_click_time = 0.0
        self._last_val_click_time = 0.0

    @property
    def color_rgba(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue, self.sat, self.val)
        return (r, g, b, self.alpha)

    @property
    def color_rgb(self):
        return colorsys.hsv_to_rgb(self.hue, self.sat, self.val)

    def set_color_rgb(self, r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        self.hue = float(h)
        self.sat = float(s)
        self.val = float(v)

    def _get_wheel_center(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        cx = abs_x + self.width * 0.5
        # Wheel vertically centered in top portion
        cy = abs_y + self.height - 18.0 * scale - (self.wheel_radius * scale) - 2.0 * scale
        return cx, cy

    def _get_val_slider_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        sx = abs_x + 8.0 * scale
        sy = abs_y + 16.0 * scale
        sw = max(10.0, self.width - 16.0 * scale)
        sh = 11.0 * scale
        return sx, sy, sw, sh

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx, cy = self._get_wheel_center(origin_x, origin_y)
        r = self.wheel_radius * scale

        curr_r, curr_g, curr_b = self.color_rgb

        # 1. Header (Title + Live Swatch + Hex Code)
        header_y = abs_y + self.height - 14.0 * scale
        if self.text:
            self.draw_text(self.text, abs_x + 4.0 * scale, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        hex_str = f"#{int(curr_r * 255):02X}{int(curr_g * 255):02X}{int(curr_b * 255):02X}"
        hw, _ = self.get_text_dimensions(hex_str, font_id=0, size=9)

        # Header Swatch Box on right
        swatch_w = 20.0 * scale
        swatch_h = 10.0 * scale
        swatch_x = abs_x + self.width - swatch_w - 4.0 * scale
        swatch_y = header_y + 1.0 * scale

        GpuShapes.draw_smooth_rounded_box(
            swatch_x, swatch_y, swatch_w, swatch_h,
            radius=2.0 * scale,
            fill_color=(curr_r, curr_g, curr_b, 1.0),
            border_color=BlenderTheme.BORDER_LIGHT,
            border_width=1.0
        )
        self.draw_text(hex_str, swatch_x - hw - 6.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MAIN)

        # 2. Continuous HSV Color Wheel Disc (Hardware GPU Evaluated)
        GpuShapes.draw_hsv_wheel(cx, cy, r, value=self.val, alpha=1.0)

        # Outer anti-aliased border ring
        border_col = (1.0, 1.0, 1.0, 0.4) if self._active_target == 'WHEEL' else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_ring(cx, cy, r, border_col, thickness=1.0)

        # 3. Reticle Handle / Puck (Hue & Saturation)
        angle = self.hue * 2.0 * math.pi
        puck_dist = self.sat * r
        px = cx + math.cos(angle) * puck_dist
        py = cy + math.sin(angle) * puck_dist

        puck_r = 5.0 * scale
        # Shadow / outer dark ring
        GpuShapes.draw_smooth_ring(px, py, puck_r + 1.0 * scale, (0.1, 0.1, 0.1, 0.9), thickness=1.2)
        # Bright crisp ring
        GpuShapes.draw_smooth_ring(px, py, puck_r, (1.0, 1.0, 1.0, 1.0), thickness=1.5)
        # Inner color swatch pip
        GpuShapes.draw_smooth_circle(px, py, puck_r - 2.0 * scale, (curr_r, curr_g, curr_b, 1.0))

        # 4. Companion Value (Luminance) Gradient Slider
        sx, sy, sw, sh = self._get_val_slider_rect(origin_x, origin_y)

        # Draw horizontal gradient bar from black (v=0) to full color (v=1)
        pure_r, pure_g, pure_b = colorsys.hsv_to_rgb(self.hue, self.sat, 1.0)
        c_left = (0.0, 0.0, 0.0, 1.0)
        c_right = (pure_r, pure_g, pure_b, 1.0)

        quad_pos = ((sx, sy), (sx + sw, sy), (sx + sw, sy + sh), (sx, sy + sh))
        quad_cols = (c_left, c_right, c_right, c_left)

        shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')
        batch_val = batch_for_shader(shader_smooth, 'TRI_FAN', {"pos": quad_pos, "color": quad_cols})
        gpu.state.blend_set('ALPHA')
        batch_val.draw(shader_smooth)
        gpu.state.blend_set('NONE')

        # Outer rounded border for value slider
        v_border = (1.0, 1.0, 1.0, 0.4) if self._active_target == 'VAL' else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_rounded_rect_outline(sx, sy, sw, sh, radius=3.0 * scale, color=v_border, line_width=1.0)

        # Value Slider Handle (Vertical needle bar)
        val_x = sx + self.val * sw
        GpuShapes.draw_smooth_line(
            val_x, sy - 1.0 * scale,
            val_x, sy + sh + 1.0 * scale,
            (0.1, 0.1, 0.1, 0.9),
            line_width=3.0 * scale
        )
        GpuShapes.draw_smooth_line(
            val_x, sy - 1.0 * scale,
            val_x, sy + sh + 1.0 * scale,
            (1.0, 1.0, 1.0, 1.0),
            line_width=1.5 * scale
        )

        # 5. Value Readout Label below slider
        val_pct = f"Value: {int(self.val * 100)}%"
        self.draw_text(val_pct, sx, abs_y + 2.0 * scale, font_id=0, size=9, color=BlenderTheme.TEXT_MUTED)

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        cx, cy = self._get_wheel_center(origin_x, origin_y)
        r = self.wheel_radius * scale
        dist_sq = (mx - cx) ** 2 + (my - cy) ** 2
        hit_wheel = dist_sq <= ((r + 4.0 * scale) ** 2)

        sx, sy, sw, sh = self._get_val_slider_rect(origin_x, origin_y)
        pad_val = 3.0 * scale
        hit_val = (sx - pad_val <= mx <= sx + sw + pad_val) and (sy - pad_val <= my <= sy + sh + pad_val)

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                now = time.time()
                if hit_wheel:
                    # Double click near center resets saturation
                    if now - self._last_wheel_click_time < 0.28:
                        self.sat = 0.0
                        self._trigger_change()
                        return True
                    self._last_wheel_click_time = now
                    self._active_target = 'WHEEL'
                    self._update_wheel_pos(mx, my, cx, cy, r, event)
                    return True

                elif hit_val:
                    # Double click on slider resets value to 1.0
                    if now - self._last_val_click_time < 0.28:
                        self.val = 1.0
                        self._trigger_change()
                        return True
                    self._last_val_click_time = now
                    self._active_target = 'VAL'
                    self._update_val_pos(mx, sx, sw)
                    return True

            elif event.value == 'RELEASE':
                if self._active_target:
                    self._active_target = None
                    return True

        elif event.type == 'MOUSEMOVE':
            if self._active_target == 'WHEEL':
                self._update_wheel_pos(mx, my, cx, cy, r, event)
                return True
            elif self._active_target == 'VAL':
                self._update_val_pos(mx, sx, sw)
                return True

        return False

    def _update_wheel_pos(self, mx, my, cx, cy, radius, event):
        dx = mx - cx
        dy = my - cy
        dist = math.hypot(dx, dy)
        sat = min(1.0, dist / max(1.0, radius))

        angle = math.atan2(dy, dx)
        if angle < 0.0:
            angle += 2.0 * math.pi
        hue = angle / (2.0 * math.pi)

        # Ctrl modifier: snap hue to 15-degree increments (24 color wheel steps)
        if event.ctrl:
            step = 1.0 / 24.0
            hue = round(hue / step) * step
            hue = hue % 1.0

        # Shift modifier: fine saturation precision
        if event.shift:
            sat = round(sat * 20.0) / 20.0

        self.hue = hue
        self.sat = sat
        self._trigger_change()

    def _update_val_pos(self, mx, sx, sw):
        ratio = (mx - sx) / max(1.0, sw)
        self.val = max(0.0, min(1.0, ratio))
        self._trigger_change()

    def _trigger_change(self):
        if self.on_color_change:
            self.on_color_change(self.color_rgba)
