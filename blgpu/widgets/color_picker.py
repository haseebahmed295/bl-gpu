import math
import colorsys
import gpu
from gpu_extras.batch import batch_for_shader
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIColorPicker(UIElement):
    """
    Interactive Color Swatch button with a Floating Native-style HSV Color Picker Popup.
    Features:
    - Compact panel row showing label and rounded live color swatch.
    - Click swatch to open floating top-level color picker popup dialog.
    - Continuous GPU-evaluated HSV circular color wheel (360° hue & radial saturation).
    - Draggable Value (Brightness/Luminance) gradient slider.
    - Live #HEX code and RGB readout.
    - Initial vs Current color comparison swatches.
    - Quick 8-color preset palette swatches.
    - Realtime live updates as you drag.
    - Click outside or click 'x' to close.
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
        text="Color",
        default_color=(0.278, 0.447, 0.702, 1.0),
        x=0,
        y=0,
        width=180,
        height=24,
        corner_radius=None,
        border_width=None,
        border_color=None,
        border_hover_color=None,
        on_color_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.on_color_change = on_color_change

        r, g, b = default_color[0], default_color[1], default_color[2]
        self.alpha = default_color[3] if len(default_color) > 3 else 1.0
        self.color = (float(r), float(g), float(b), float(self.alpha))
        self._initial_color = self.color

        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        self.hue = float(h)
        self.sat = float(s)
        self.val = float(v)

        self.font_size = 11
        self.swatch_width = 42
        self.border_color = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.border_color_hover = border_hover_color if border_hover_color is not None else BlenderTheme.BORDER_LIGHT
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS

        self.is_expanded = False
        self._active_target = None  # 'WHEEL', 'VAL', or None

    def set_color(self, r, g, b, a=1.0):
        self.alpha = float(a)
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        self.hue = float(h)
        self.sat = float(s)
        self.val = float(v)
        self._update_color_tuple()

    def _update_color_tuple(self):
        r, g, b = colorsys.hsv_to_rgb(self.hue, self.sat, self.val)
        self.color = (float(r), float(g), float(b), float(self.alpha))

    def _notify_change(self):
        self._update_color_tuple()
        if self.on_color_change:
            self.on_color_change(self, self.color)

    def _get_popup_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        pw = 175.0 * scale
        ph = 205.0 * scale

        # Position aligned with swatch on right
        px = abs_x + self.width - pw
        # Float below swatch, or above if close to bottom
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
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        swatch_w = self.swatch_width * scale
        swatch_x = abs_x + self.width - swatch_w
        swatch_y = abs_y + (1.0 * scale)
        swatch_h = self.height - (2.0 * scale)

        inside_swatch = (swatch_x <= mouse_x <= swatch_x + swatch_w) and (swatch_y <= mouse_y <= swatch_y + swatch_h)
        inside_row = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)

        # -------------------------------------------------------------
        # STATE A: Popup is OPEN
        # -------------------------------------------------------------
        if self.is_expanded:
            px, py, pw, ph = self._get_popup_rect(origin_x, origin_y)
            cx, cy, wheel_r = self._get_wheel_geometry(px, py, pw, ph, scale)
            vx, vy, vw, vh = self._get_slider_geometry(px, py, pw, ph, scale)

            inside_popup = (px <= mouse_x <= px + pw) and (py <= mouse_y <= py + ph)

            # Close button 'x' rect at top-right of popup
            close_x = px + pw - (20.0 * scale)
            close_y = py + ph - (20.0 * scale)
            inside_close = (close_x - 4 <= mouse_x <= close_x + 16) and (close_y - 4 <= mouse_y <= close_y + 16)

            # Wheel hit check
            dist_sq = (mouse_x - cx) ** 2 + (mouse_y - cy) ** 2
            hit_wheel = dist_sq <= ((wheel_r + 4.0 * scale) ** 2)

            # Value slider hit check
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
                        bx = px + (12.0 * scale) + i * (pal_box_w + pal_spacing)
                        if (bx <= mouse_x <= bx + pal_box_w) and (palette_y <= mouse_y <= palette_y + palette_h):
                            self.set_color(pcol[0], pcol[1], pcol[2], pcol[3])
                            self._notify_change()
                            return True

                    if inside_popup:
                        return True  # Swallow click inside popup backdrop

                    # Clicked outside popup
                    if inside_swatch:
                        self.is_expanded = False
                        return True

                    self.is_expanded = False
                    return False  # Allow click outside to interact with viewport or other widgets

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
        # STATE B: Popup is CLOSED
        # -------------------------------------------------------------
        if event.type == 'MOUSEMOVE':
            if inside_swatch != self.hovered:
                self.hovered = inside_swatch
                return True
            return False

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if inside_swatch or inside_row:
                self.is_expanded = True
                self._initial_color = self.color
                self._active_target = None
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
        self._notify_change()

    def _update_from_slider(self, mx, vx, vw):
        self.val = float(max(0.0, min(1.0, (mx - vx) / max(1.0, vw))))
        self._notify_change()

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        scale = BlenderTheme.get_ui_scale()
        swatch_width = self.swatch_width * scale

        # 1. Label on the left
        tw, th = self.get_text_dimensions(self.text, font_id=0, size=self.font_size)
        ty = abs_y + (self.height - th) / 2.0 + (1.0 * scale)
        max_label_w = max(10.0, self.width - swatch_width - (10.0 * scale))
        self.draw_text(self.text, abs_x, ty, font_id=0, size=self.font_size, color=BlenderTheme.TEXT_MAIN, max_width=max_label_w)

        # 2. Rounded Color Swatch Button on the right
        swatch_x = abs_x + self.width - swatch_width
        swatch_y = abs_y + (1.0 * scale)
        swatch_h = self.height - (2.0 * scale)

        border_col = BlenderTheme.BORDER_FOCUS if self.is_expanded else (self.border_color_hover if self.hovered else self.border_color)
        border_w = (self.border_width + 0.5) if self.is_expanded else self.border_width

        # Checker pattern background for transparency
        GpuShapes.draw_smooth_box(swatch_x, swatch_y, swatch_width, swatch_h, (0.2, 0.2, 0.2, 1.0))
        self.draw_rounded_rect(swatch_x, swatch_y, swatch_width, swatch_h, self.corner_radius, self.color)
        self.draw_rounded_rect_outline(swatch_x, swatch_y, swatch_width, swatch_h, self.corner_radius, border_col, line_width=border_w)

    def draw_overlay(self, origin_x, origin_y):
        """Renders the floating HSV Color Picker Dialog over all widgets."""
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

        # Comparison Swatch: Left half = Initial, Right half = Current
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
        # Wheel outer border
        border_wheel = (1.0, 1.0, 1.0, 0.5) if self._active_target == 'WHEEL' else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_ring(cx, cy, wheel_r, border_wheel, thickness=1.0)

        # Reticle Puck (Hue & Saturation)
        angle = self.hue * 2.0 * math.pi
        puck_dist = self.sat * wheel_r
        puck_x = cx + math.cos(angle) * puck_dist
        puck_y = cy + math.sin(angle) * puck_dist
        puck_r = 4.5 * scale

        # High-contrast dual ring puck
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

        # Value Slider Needle Handle
        val_x = vx + self.val * vw
        GpuShapes.draw_smooth_line(val_x, vy - 1.0 * scale, val_x, vy + vh + 1.0 * scale, (0.05, 0.05, 0.05, 0.9), line_width=3.0 * scale)
        GpuShapes.draw_smooth_line(val_x, vy - 1.0 * scale, val_x, vy + vh + 1.0 * scale, (1.0, 1.0, 1.0, 1.0), line_width=1.5 * scale)

        # Value percentage text below slider
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

