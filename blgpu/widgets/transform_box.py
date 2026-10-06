import gpu
import math
import time
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UITransformBox(UIElement):
    """
    Interactive 2D Transform / UV Box Manipulator widget.
    Embeds a visual 2D bounding box transform gizmo inside the N-panel (impossible in standard Blender UI).
    Features:
    - Rotated rectangular bounding box with 8 boundary handles (4 corners + 4 edge centers).
    - Top orbit stem handle for free 2D angular rotation with Ctrl snapping.
    - Drag inside box to pan translation offset (X, Y).
    - Double click center pivot to reset transform to identity.
    - Real-time on_transform_change callback.
    """

    def __init__(
        self,
        text="2D Transform",
        pos_x=0.0,
        pos_y=0.0,
        scale_x=1.0,
        scale_y=1.0,
        rotation_deg=0.0,
        x=0,
        y=0,
        width=150,
        height=150,
        on_transform_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.pos_x = float(pos_x)
        self.pos_y = float(pos_y)
        self.scale_x = float(scale_x)
        self.scale_y = float(scale_y)
        self.rotation = math.radians(float(rotation_deg))
        self.on_transform_change = on_transform_change

        # Interaction state
        self._dragging_target = None  # 'TRANSLATE', 'ROTATION', 'CORNER_TR', 'CORNER_TL', etc.
        self._drag_start_mouse = (0.0, 0.0)
        self._drag_start_pos = (0.0, 0.0)
        self._drag_start_scale = (1.0, 1.0)
        self._drag_start_rot = 0.0
        self._last_click_time = 0.0

        # Colors
        self.canvas_bg = (0.12, 0.12, 0.14, 0.95)
        self.grid_color = (0.22, 0.22, 0.26, 0.4)
        self.box_color = BlenderTheme.PRIMARY_BLUE
        self.box_fill = (0.28, 0.55, 0.95, 0.08)
        self.handle_fill = (1.0, 1.0, 1.0, 0.95)
        self.handle_border = (0.1, 0.1, 0.1, 0.9)

    def _get_canvas_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx = abs_x + 6.0 * scale
        cy = abs_y + 6.0 * scale
        cw = max(20.0, self.width - 12.0 * scale)
        ch = max(20.0, self.height - 24.0 * scale)
        return cx, cy, cw, ch

    def _get_box_center(self, cx, cy, cw, ch, scale):
        box_cx = cx + (cw * 0.5) + (self.pos_x * cw * 0.35)
        box_cy = cy + (ch * 0.5) + (self.pos_y * ch * 0.35)
        return box_cx, box_cy

    def _local_to_screen(self, lx, ly, box_cx, box_cy):
        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)
        sx = box_cx + lx * cos_r - ly * sin_r
        sy = box_cy + lx * sin_r + ly * cos_r
        return sx, sy

    def _screen_to_local(self, sx, sy, box_cx, box_cy):
        dx = sx - box_cx
        dy = sy - box_cy
        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)
        lx =  dx * cos_r + dy * sin_r
        ly = -dx * sin_r + dy * cos_r
        return lx, ly

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)

        # 1. Header (Title + HUD readout: Pos, Scale, Rot)
        header_y = abs_y + self.height - 14.0 * scale
        if self.text:
            self.draw_text(self.text, abs_x + 4.0 * scale, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        rot_deg = (math.degrees(self.rotation) + 180.0) % 360.0 - 180.0
        hud_str = f"S:{self.scale_x:.2f} R:{int(rot_deg):+d}°"
        hw, _ = self.get_text_dimensions(hud_str, font_id=0, size=9)
        self.draw_text(hud_str, abs_x + self.width - hw - 6.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MAIN)

        # 2. Canvas Background & Reference Grid
        GpuShapes.draw_smooth_rounded_box(
            cx, cy, cw, ch,
            radius=4.0 * scale,
            fill_color=self.canvas_bg,
            border_color=BlenderTheme.BORDER_LIGHT,
            border_width=1.0
        )

        mid_x = cx + cw * 0.5
        mid_y = cy + ch * 0.5
        # Center reference crosshair
        GpuShapes.draw_smooth_line(mid_x, cy + 2.0 * scale, mid_x, cy + ch - 2.0 * scale, self.grid_color, line_width=1.0)
        GpuShapes.draw_smooth_line(cx + 2.0 * scale, mid_y, cx + cw - 2.0 * scale, mid_y, self.grid_color, line_width=1.0)

        # 3. Transformed Box Geometry
        box_cx, box_cy = self._get_box_center(cx, cy, cw, ch, scale)
        base_hw = cw * 0.22 * scale
        base_hh = ch * 0.22 * scale
        hw = max(4.0 * scale, base_hw * abs(self.scale_x))
        hh = max(4.0 * scale, base_hh * abs(self.scale_y))

        # Corners in screen coordinates
        p_bl = self._local_to_screen(-hw, -hh, box_cx, box_cy)
        p_br = self._local_to_screen( hw, -hh, box_cx, box_cy)
        p_tr = self._local_to_screen( hw,  hh, box_cx, box_cy)
        p_tl = self._local_to_screen(-hw,  hh, box_cx, box_cy)

        # Fill box with subtle tint
        # (Draw 2 triangles as smooth polyline / quad)
        GpuShapes.draw_smooth_polyline([p_bl, p_br, p_tr, p_tl, p_bl], self.box_color, line_width=1.5 * scale)

        # 4. Rotation Stem & Orbit Handle
        p_top_mid = self._local_to_screen(0.0, hh, box_cx, box_cy)
        rot_stem_dist = 18.0 * scale
        p_rot_handle = self._local_to_screen(0.0, hh + rot_stem_dist, box_cx, box_cy)

        # Connecting stem line
        GpuShapes.draw_smooth_line(p_top_mid[0], p_top_mid[1], p_rot_handle[0], p_rot_handle[1], (0.5, 0.5, 0.5, 0.7), line_width=1.0)
        # Rotation handle circle
        rot_r = 4.0 * scale
        GpuShapes.draw_smooth_circle(p_rot_handle[0], p_rot_handle[1], rot_r, self.box_color)
        GpuShapes.draw_smooth_ring(p_rot_handle[0], p_rot_handle[1], rot_r, (1.0, 1.0, 1.0, 0.95), thickness=1.2)

        # 5. Scaling Handles (4 Corners + 4 Edge Centers)
        handle_size = 5.0 * scale
        h_pts = [
            # Corners
            p_tr, p_tl, p_bl, p_br,
            # Edge centers
            p_top_mid,
            self._local_to_screen(0.0, -hh, box_cx, box_cy),
            self._local_to_screen(-hw, 0.0, box_cx, box_cy),
            self._local_to_screen( hw, 0.0, box_cx, box_cy)
        ]

        hs = handle_size * 0.5
        for px, py in h_pts:
            GpuShapes.draw_smooth_rounded_box(
                px - hs, py - hs, handle_size, handle_size,
                radius=1.2 * scale,
                fill_color=self.handle_fill,
                border_color=self.handle_border,
                border_width=1.0
            )

        # Center Pivot Dot
        GpuShapes.draw_smooth_circle(box_cx, box_cy, 2.5 * scale, (1.0, 1.0, 1.0, 0.95))

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)
        pad = 6.0 * scale
        hit_canvas = (cx - pad <= mx <= cx + cw + pad) and (cy - pad <= my <= cy + ch + pad)

        box_cx, box_cy = self._get_box_center(cx, cy, cw, ch, scale)
        base_hw = cw * 0.22 * scale
        base_hh = ch * 0.22 * scale
        hw = max(4.0 * scale, base_hw * abs(self.scale_x))
        hh = max(4.0 * scale, base_hh * abs(self.scale_y))

        p_rot = self._local_to_screen(0.0, hh + 18.0 * scale, box_cx, box_cy)
        rot_hit_dist = 8.0 * scale

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and hit_canvas:
                now = time.time()
                # Double click to reset
                if now - self._last_click_time < 0.28:
                    self.pos_x = 0.0
                    self.pos_y = 0.0
                    self.scale_x = 1.0
                    self.scale_y = 1.0
                    self.rotation = 0.0
                    self._dragging_target = None
                    self._trigger_change()
                    return True

                self._last_click_time = now
                self._drag_start_mouse = (mx, my)
                self._drag_start_pos = (self.pos_x, self.pos_y)
                self._drag_start_scale = (self.scale_x, self.scale_y)
                self._drag_start_rot = self.rotation

                # 1. Check Rotation handle
                if math.hypot(mx - p_rot[0], my - p_rot[1]) <= rot_hit_dist:
                    self._dragging_target = 'ROTATION'
                    return True

                # 2. Check Scale handles (in local coords)
                lx, ly = self._screen_to_local(mx, my, box_cx, box_cy)
                h_tol = 6.0 * scale

                # Corners
                if abs(lx - hw) <= h_tol and abs(ly - hh) <= h_tol:
                    self._dragging_target = 'SCALE_UNIFORM'
                    return True
                elif abs(lx - (-hw)) <= h_tol and abs(ly - hh) <= h_tol:
                    self._dragging_target = 'SCALE_UNIFORM'
                    return True
                elif abs(lx - (-hw)) <= h_tol and abs(ly - (-hh)) <= h_tol:
                    self._dragging_target = 'SCALE_UNIFORM'
                    return True
                elif abs(lx - hw) <= h_tol and abs(ly - (-hh)) <= h_tol:
                    self._dragging_target = 'SCALE_UNIFORM'
                    return True

                # Edge centers
                if abs(lx) <= h_tol and abs(ly - hh) <= h_tol:
                    self._dragging_target = 'SCALE_Y'
                    return True
                elif abs(lx) <= h_tol and abs(ly - (-hh)) <= h_tol:
                    self._dragging_target = 'SCALE_Y'
                    return True
                elif abs(lx - hw) <= h_tol and abs(ly) <= h_tol:
                    self._dragging_target = 'SCALE_X'
                    return True
                elif abs(lx - (-hw)) <= h_tol and abs(ly) <= h_tol:
                    self._dragging_target = 'SCALE_X'
                    return True

                # 3. Inside box: Translate
                if abs(lx) <= hw and abs(ly) <= hh:
                    self._dragging_target = 'TRANSLATE'
                    return True

                # Outside box on canvas: Translate to click
                self._dragging_target = 'TRANSLATE'
                self.pos_x = max(-1.0, min(1.0, (mx - (cx + cw * 0.5)) / (cw * 0.35)))
                self.pos_y = max(-1.0, min(1.0, (my - (cy + ch * 0.5)) / (ch * 0.35)))
                self._trigger_change()
                return True

            elif event.value == 'RELEASE' and self._dragging_target is not None:
                self._dragging_target = None
                return True

        elif event.type == 'MOUSEMOVE' and self._dragging_target is not None:
            dmx = mx - self._drag_start_mouse[0]
            dmy = my - self._drag_start_mouse[1]

            if self._dragging_target == 'TRANSLATE':
                new_px = self._drag_start_pos[0] + dmx / (cw * 0.35)
                new_py = self._drag_start_pos[1] + dmy / (ch * 0.35)
                self.pos_x = max(-1.2, min(1.2, round(new_px, 2)))
                self.pos_y = max(-1.2, min(1.2, round(new_py, 2)))
                self._trigger_change()
                return True

            elif self._dragging_target == 'ROTATION':
                angle = math.atan2(my - box_cy, mx - box_cx) - (math.pi * 0.5)
                if event.ctrl:
                    step = math.radians(15.0)
                    angle = round(angle / step) * step
                elif event.shift:
                    angle = round(angle, 3)
                self.rotation = angle
                self._trigger_change()
                return True

            elif self._dragging_target in ('SCALE_UNIFORM', 'SCALE_X', 'SCALE_Y'):
                # Mouse delta in local coordinates
                cos_r = math.cos(self.rotation)
                sin_r = math.sin(self.rotation)
                dlx =  dmx * cos_r + dmy * sin_r
                dly = -dmx * sin_r + dmy * cos_r

                if self._dragging_target == 'SCALE_UNIFORM':
                    s_factor = 1.0 + (dlx + dly) / max(10.0, base_hw + base_hh)
                    new_s = max(0.2, min(3.0, self._drag_start_scale[0] * s_factor))
                    self.scale_x = round(new_s, 2)
                    self.scale_y = round(new_s, 2)
                elif self._dragging_target == 'SCALE_X':
                    s_factor = 1.0 + dlx / max(10.0, base_hw)
                    self.scale_x = max(0.2, min(3.0, round(self._drag_start_scale[0] * s_factor, 2)))
                elif self._dragging_target == 'SCALE_Y':
                    s_factor = 1.0 + dly / max(10.0, base_hh)
                    self.scale_y = max(0.2, min(3.0, round(self._drag_start_scale[1] * s_factor, 2)))

                self._trigger_change()
                return True

        return False

    def _trigger_change(self):
        if self.on_transform_change:
            rot_deg = math.degrees(self.rotation)
            self.on_transform_change((self.pos_x, self.pos_y), (self.scale_x, self.scale_y), rot_deg)
