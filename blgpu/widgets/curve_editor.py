import time
import gpu
import math
from gpu_extras.batch import batch_for_shader
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UICurveEditor(UIElement):
    """
    Interactive 2D Bézier / Spline Falloff Curve Editor.
    Features:
    - 2D grid background with reference lines
    - Configurable default points and maximum/minimum points
    - Strict neighbor clamping preventing points from moving past adjacent points in X
    - Realtime GPU spline curve evaluation and rendering
    - Hover value readout badge
    - Double-click on background to reset to default points
    - Right-click control point to delete
    """

    def __init__(
        self,
        points=None,
        default_points=None,
        max_points=8,
        min_points=2,
        lock_endpoints_x=True,
        min_distance=0.015,
        min_x=0.0,
        max_x=1.0,
        min_y=0.0,
        max_y=1.0,
        x=0,
        y=0,
        width=200,
        height=100,
        corner_radius=None,
        on_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)

        # Configurable constraints
        self.max_points = max(2, int(max_points))
        self.min_points = max(2, min(self.max_points, int(min_points)))
        self.lock_endpoints_x = bool(lock_endpoints_x)
        self.min_distance = float(min_distance)
        self.min_x = float(min_x)
        self.max_x = float(max_x)
        self.min_y = float(min_y)
        self.max_y = float(max_y)

        # Default points
        if default_points is not None:
            self.default_points = [tuple(p) for p in default_points]
        elif points is not None:
            self.default_points = [tuple(p) for p in points]
        else:
            self.default_points = [(0.0, 0.0), (0.25, 0.75), (0.75, 0.25), (1.0, 1.0)]

        # Initial active points
        init_pts = points if points is not None else self.default_points
        self.points = [tuple(p) for p in init_pts]
        self.points.sort(key=lambda p: p[0])

        self.on_change = on_change
        self.active_point_idx = -1
        self.hovered_point_idx = -1
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS

        self.color_bg = BlenderTheme.BG_INSET
        self.color_grid = (0.19, 0.19, 0.19, 1.0)
        self.color_curve = BlenderTheme.PRIMARY_BLUE
        self.color_handle = (0.9, 0.9, 0.9, 1.0)
        self.color_handle_active = (1.0, 0.6, 0.1, 1.0)
        self.border_color = BlenderTheme.BORDER_DARK
        self.pad = 8.0

        self._last_click_time = 0.0
        self._last_click_x = 0.0

    def reset_to_default(self):
        """Resets the curve points back to default_points."""
        self.points = [tuple(p) for p in self.default_points]
        self.points.sort(key=lambda p: p[0])
        self.active_point_idx = -1
        self.hovered_point_idx = -1
        if self.on_change:
            self.on_change(self, self.points)

    def _to_screen(self, norm_x, norm_y, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        pad = self.pad * scale
        inner_w = self.width - (pad * 2.0)
        inner_h = self.height - (pad * 2.0)
        sx = origin_x + self.x + pad + norm_x * inner_w
        sy = origin_y + self.y + pad + norm_y * inner_h
        return sx, sy

    def _to_norm(self, screen_x, screen_y, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        pad = self.pad * scale
        inner_w = max(1.0, self.width - (pad * 2.0))
        inner_h = max(1.0, self.height - (pad * 2.0))
        nx = (screen_x - (origin_x + self.x + pad)) / inner_w
        ny = (screen_y - (origin_y + self.y + pad)) / inner_h
        return max(self.min_x, min(self.max_x, nx)), max(self.min_y, min(self.max_y, ny))

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        handle_rad = 7.0 * scale
        inside = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)

        # 1. Check hover over existing points
        hover_idx = -1
        for i, (nx, ny) in enumerate(self.points):
            sx, sy = self._to_screen(nx, ny, origin_x, origin_y)
            dist_sq = (mouse_x - sx)**2 + (mouse_y - sy)**2
            if dist_sq <= (handle_rad + 2)**2:
                hover_idx = i
                break

        if event.type == 'MOUSEMOVE':
            if self.is_dragging and 0 <= self.active_point_idx < len(self.points):
                nx, ny = self._to_norm(mouse_x, mouse_y, origin_x, origin_y)
                ny = max(self.min_y, min(self.max_y, ny))

                # Strict neighbor clamping: point CANNOT move beyond adjacent points in X
                if self.lock_endpoints_x and self.active_point_idx == 0:
                    nx = self.min_x
                elif self.lock_endpoints_x and self.active_point_idx == len(self.points) - 1:
                    nx = self.max_x
                else:
                    min_allowed_x = self.min_x
                    max_allowed_x = self.max_x

                    if self.active_point_idx > 0:
                        min_allowed_x = self.points[self.active_point_idx - 1][0] + self.min_distance
                    if self.active_point_idx < len(self.points) - 1:
                        max_allowed_x = self.points[self.active_point_idx + 1][0] - self.min_distance

                    # Clamp strictly to neighbor interval
                    if min_allowed_x <= max_allowed_x:
                        nx = max(min_allowed_x, min(max_allowed_x, nx))
                    else:
                        nx = (min_allowed_x + max_allowed_x) / 2.0

                self.points[self.active_point_idx] = (round(nx, 4), round(ny, 4))
                if self.on_change:
                    self.on_change(self, self.points)
                return True

            if hover_idx != self.hovered_point_idx:
                self.hovered_point_idx = hover_idx
                return True

        elif event.type == 'LEFTMOUSE':
            if event.value in {'PRESS', 'DOUBLE_CLICK'}:
                if hover_idx >= 0:
                    self.active_point_idx = hover_idx
                    self.is_dragging = True
                    return True
                elif inside:
                    # Add new point if under max_points limit
                    if len(self.points) < self.max_points:
                        nx, ny = self._to_norm(mouse_x, mouse_y, origin_x, origin_y)
                        ny = max(self.min_y, min(self.max_y, ny))

                        # Check that new point is not right on top of an existing point in X
                        too_close = any(abs(p[0] - nx) < self.min_distance for p in self.points)
                        if not too_close:
                            self.points.append((round(nx, 4), round(ny, 4)))
                            self.points.sort(key=lambda p: p[0])
                            # Find index of the newly inserted point
                            for i, p in enumerate(self.points):
                                if abs(p[0] - round(nx, 4)) < 0.0001:
                                    self.active_point_idx = i
                                    break
                            self.is_dragging = True
                            if self.on_change:
                                self.on_change(self, self.points)
                            return True
                    else:
                        # At max_points limit: benign no-op, do NOT reset points
                        return True

            elif event.value == 'RELEASE':
                if self.is_dragging:
                    self.is_dragging = False
                    self.active_point_idx = -1
                    return True

        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            # Right-click to delete internal control points (preserving min_points and endpoints)
            if len(self.points) > self.min_points and 0 < hover_idx < len(self.points) - 1:
                self.points.pop(hover_idx)
                self.hovered_point_idx = -1
                self.active_point_idx = -1
                if self.on_change:
                    self.on_change(self, self.points)
                return True

        return False

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        scale = BlenderTheme.get_ui_scale()

        # 1. Background Box & Outline
        self.draw_rounded_rect(abs_x, abs_y, self.width, self.height, self.corner_radius, self.color_bg)
        self.draw_rounded_rect_outline(abs_x, abs_y, self.width, self.height, self.corner_radius, self.border_color, line_width=1.0)

        # 2. Grid lines
        pad = self.pad * scale
        inner_w = self.width - (pad * 2.0)
        inner_h = self.height - (pad * 2.0)
        ix = abs_x + pad
        iy = abs_y + pad

        grid_lines = [
            # Horizontal 25%, 50%, 75%
            (ix, iy + inner_h * 0.25), (ix + inner_w, iy + inner_h * 0.25),
            (ix, iy + inner_h * 0.50), (ix + inner_w, iy + inner_h * 0.50),
            (ix, iy + inner_h * 0.75), (ix + inner_w, iy + inner_h * 0.75),
            # Vertical 25%, 50%, 75%
            (ix + inner_w * 0.25, iy), (ix + inner_w * 0.25, iy + inner_h),
            (ix + inner_w * 0.50, iy), (ix + inner_w * 0.50, iy + inner_h),
            (ix + inner_w * 0.75, iy), (ix + inner_w * 0.75, iy + inner_h),
            # Diagonal identity reference line
            (ix, iy), (ix + inner_w, iy + inner_h),
        ]
        GpuShapes.draw_smooth_lines(grid_lines, self.color_grid, line_width=1.0)

        # Scissor clip to inner graph boundaries
        orig_scissor = gpu.state.scissor_get()
        clip_x0 = max(int(orig_scissor[0]), int(ix))
        clip_y0 = max(int(orig_scissor[1]), int(iy))
        clip_x1 = min(int(orig_scissor[0] + orig_scissor[2]), int(ix + inner_w))
        clip_y1 = min(int(orig_scissor[1] + orig_scissor[3]), int(iy + inner_h))

        if clip_x1 > clip_x0 and clip_y1 > clip_y0:
            gpu.state.scissor_set(clip_x0, clip_y0, clip_x1 - clip_x0, clip_y1 - clip_y0)

            # 3. Interpolated Monotone Cubic Curve
            curve_pts = []
            samples = 80
            pts = self.points
            if len(pts) >= 2:
                for s in range(samples + 1):
                    t = s / samples
                    for seg in range(len(pts) - 1):
                        x0, y0 = pts[seg]
                        x1, y1 = pts[seg + 1]
                        if (x0 <= t <= x1) or (seg == len(pts) - 2 and t >= x1) or (seg == 0 and t <= x0):
                            seg_span = max(0.0001, x1 - x0)
                            lt = max(0.0, min(1.0, (t - x0) / seg_span))
                            st = lt * lt * (3.0 - 2.0 * lt)
                            yt = y0 + (y1 - y0) * st
                            curve_pts.append(self._to_screen(t, yt, origin_x, origin_y))
                            break

                if len(curve_pts) >= 2:
                    GpuShapes.draw_smooth_polyline(curve_pts, self.color_curve, line_width=max(2.0, 2.0 * scale))

            # Restore original panel scissor
            gpu.state.scissor_set(int(orig_scissor[0]), int(orig_scissor[1]), int(orig_scissor[2]), int(orig_scissor[3]))

        # 4. Control Point Handles
        h_rad = 5.0 * scale
        for i, (nx, ny) in enumerate(self.points):
            sx, sy = self._to_screen(nx, ny, origin_x, origin_y)
            is_active = (i == self.active_point_idx)
            is_hover = (i == self.hovered_point_idx)
            col = self.color_handle_active if (is_active or is_hover) else self.color_handle
            r = h_rad * (1.3 if (is_active or is_hover) else 1.0)
            GpuShapes.draw_smooth_circle(sx, sy, r, col)
            GpuShapes.draw_smooth_ring(sx, sy, r, (0.05, 0.05, 0.05, 1.0), thickness=1.0)

        # 5. Hover Value Readout
        if 0 <= self.hovered_point_idx < len(self.points):
            hx, hy = self.points[self.hovered_point_idx]
            info_str = f"X: {hx:.2f}  Y: {hy:.2f}"
            sx, sy = self._to_screen(hx, hy, origin_x, origin_y)
            tx = sx + 8.0 * scale
            ty = min(abs_y + self.height - 12.0 * scale, max(abs_y + 4.0 * scale, sy + 4.0 * scale))
            self.draw_text(info_str, tx, ty, font_id=0, size=9, color=(0.95, 0.95, 0.95, 0.9))

