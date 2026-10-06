import gpu
import math
import time
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

def _quat_mult(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return (
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    )

def _quat_normalize(q):
    l = math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3])
    if l < 1e-6:
        return (0.0, 0.0, 0.0, 1.0)
    return (q[0]/l, q[1]/l, q[2]/l, q[3]/l)

def _quat_rotate(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    return (
        vx + qw * tx + (qy * tz - qz * ty),
        vy + qw * ty + (qz * tx - qx * tz),
        vz + qw * tz + (qx * ty - qy * tx)
    )

class UIOrbitSphere(UIElement):
    """
    Interactive 3D Viewport Sphere / Arcball Trackball widget.
    Renders an anti-aliased lit 3D sphere with realtime lighting, equator/meridian guide rings,
    and virtual arcball trackball rotation (impossible in Blender's default Python UI).
    Outputs:
    - 3D direction vector (X, Y, Z) for lights, normals, forces, or camera angles.
    - Spherical Azimuth and Elevation angles.
    """

    def __init__(
        self,
        text="3D Direction",
        default_vector=(0.0, 0.0, 1.0),
        x=0,
        y=0,
        width=150,
        height=135,
        radius=38.0,
        on_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.radius = float(radius)
        self.on_change = on_change

        self.quat = (0.0, 0.0, 0.0, 1.0)
        self.normal = (0.0, 0.0, 1.0)
        self.is_dragging = False
        self.is_hovered = False
        self._last_v = None
        self._last_click_time = 0.0

        self.base_color = (0.24, 0.28, 0.32)

    def _get_sphere_center(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        cx = abs_x + self.width * 0.5
        cy = abs_y + self.height - 18.0 * scale - (self.radius * scale) - 2.0 * scale
        return cx, cy

    def _project_to_sphere(self, mx, my, cx, cy, radius):
        dx = (mx - cx) / max(1.0, radius)
        dy = (my - cy) / max(1.0, radius)
        d2 = dx * dx + dy * dy
        if d2 <= 1.0:
            dz = math.sqrt(1.0 - d2)
        else:
            inv = 1.0 / math.sqrt(d2)
            dx *= inv
            dy *= inv
            dz = 0.0
        return (dx, dy, dz)

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx, cy = self._get_sphere_center(origin_x, origin_y)
        r = self.radius * scale

        # 1. Header (Title + Spherical Coordinates HUD)
        header_y = abs_y + self.height - 14.0 * scale
        if self.text:
            self.draw_text(self.text, abs_x + 4.0 * scale, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        # Azimuth & Elevation
        nx, ny, nz = self.normal
        azimuth_deg = math.degrees(math.atan2(nx, nz)) % 360.0
        elevation_deg = math.degrees(math.asin(max(-1.0, min(1.0, ny))))
        angle_str = f"Az:{int(azimuth_deg):03d}° El:{int(elevation_deg):+03d}°"
        aw, _ = self.get_text_dimensions(angle_str, font_id=0, size=9)
        self.draw_text(angle_str, abs_x + self.width - aw - 4.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MUTED)

        # 2. Lit 3D Orbit Sphere (Analytic Ray-Traced Sphere Shader on GPU)
        col = (0.28, 0.33, 0.38) if (self.is_dragging or self.is_hovered) else self.base_color
        GpuShapes.draw_orbit_sphere(cx, cy, r, quat=self.quat, base_color=col, alpha=1.0)

        # Outer anti-aliased rim ring
        rim_col = (1.0, 1.0, 1.0, 0.5) if self.is_dragging else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_ring(cx, cy, r, rim_col, thickness=1.0)

        # 3. Vector Readout HUD (Bottom centered: X, Y, Z)
        vec_str = f"X: {nx:+.2f}   Y: {ny:+.2f}   Z: {nz:+.2f}"
        vw, _ = self.get_text_dimensions(vec_str, font_id=0, size=9)
        val_col = BlenderTheme.PRIMARY_BLUE if self.is_dragging else BlenderTheme.TEXT_MAIN
        self.draw_text(vec_str, cx - vw * 0.5, abs_y + 4.0 * scale, font_id=0, size=9, color=val_col)

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        cx, cy = self._get_sphere_center(origin_x, origin_y)
        r = self.radius * scale
        dist_sq = (mx - cx) ** 2 + (my - cy) ** 2
        hit = dist_sq <= ((r + 6.0 * scale) ** 2)

        self.is_hovered = hit or self.is_dragging

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and hit:
                now = time.time()
                # Double click to reset to front facing
                if now - self._last_click_time < 0.28:
                    self.quat = (0.0, 0.0, 0.0, 1.0)
                    self.normal = (0.0, 0.0, 1.0)
                    self.is_dragging = False
                    if self.on_change:
                        self.on_change(self.normal)
                    return True

                self._last_click_time = now
                self.is_dragging = True
                self._last_v = self._project_to_sphere(mx, my, cx, cy, r)
                return True

            elif event.value == 'RELEASE' and self.is_dragging:
                self.is_dragging = False
                self._last_v = None
                return True

        elif event.type == 'MOUSEMOVE' and self.is_dragging:
            curr_v = self._project_to_sphere(mx, my, cx, cy, r)
            if self._last_v is not None:
                v0 = self._last_v
                v1 = curr_v
                # Cross product axis
                ax = v0[1] * v1[2] - v0[2] * v1[1]
                ay = v0[2] * v1[0] - v0[0] * v1[2]
                az = v0[0] * v1[1] - v0[1] * v1[0]
                alen = math.sqrt(ax * ax + ay * ay + az * az)

                if alen > 1e-5:
                    axis = (ax / alen, ay / alen, az / alen)
                    dot_val = max(-1.0, min(1.0, v0[0]*v1[0] + v0[1]*v1[1] + v0[2]*v1[2]))
                    angle = math.acos(dot_val)

                    # Shift for fine rotation
                    if event.shift:
                        angle *= 0.25

                    half_a = angle * 0.5
                    sin_a = math.sin(half_a)
                    dq = (axis[0] * sin_a, axis[1] * sin_a, axis[2] * sin_a, math.cos(half_a))
                    self.quat = _quat_normalize(_quat_mult(dq, self.quat))

                    # Update transformed normal (+Z transformed by quaternion)
                    self.normal = _quat_rotate(self.quat, (0.0, 0.0, 1.0))

                    if self.on_change:
                        self.on_change(self.normal)

                self._last_v = curr_v
            return True

        return False
