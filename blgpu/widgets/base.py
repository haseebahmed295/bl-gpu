import gpu
import blf
from gpu_extras.batch import batch_for_shader

class UIElement:
    """Base class for custom GPU UI elements."""
    
    def __init__(self, x=0, y=0, width=100, height=25):
        from .theme import BlenderTheme
        # Relative coordinates to the panel canvas (or layout container)
        self.x = x
        self.y = y
        self.base_width = width
        self.base_height = height
        self.width = width
        self.height = height
        
        # State flags
        self.hovered = False
        self.pressed = False
        self.is_dragging = False
        self.is_focused = False
        self.visible = True
        self.enabled = True
        
        # Shader reference (cached)
        self._shader_2d = None

    @property
    def shader_2d(self):
        if self._shader_2d is None:
            self._shader_2d = gpu.shader.from_builtin('UNIFORM_COLOR')
        return self._shader_2d

    def get_absolute_rect(self, origin_x, origin_y):
        """Returns (x, y, width, height) in region pixel space."""
        return (origin_x + self.x, origin_y + self.y, self.width, self.height)

    def is_point_inside(self, px, py, origin_x, origin_y):
        """Check whether point (px, py) in region space is inside this element."""
        if not self.visible:
            return False
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        return (abs_x <= px <= abs_x + self.width) and (abs_y <= py <= abs_y + self.height)

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        """
        Handle input events.
        mouse_x, mouse_y: mouse coordinates in UI region space.
        origin_x, origin_y: panel origin in UI region space.
        Returns True if the event was consumed / caused a state change.
        """
        if not self.visible or not self.enabled:
            return False

        inside = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)
        state_changed = False

        if event.type == 'MOUSEMOVE':
            if inside != self.hovered:
                self.hovered = inside
                state_changed = True
            return state_changed

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and inside:
                self.pressed = True
                return True
            elif event.value == 'RELEASE':
                was_pressed = self.pressed
                self.pressed = False
                self.is_dragging = False
                if was_pressed and inside:
                    self.on_click_event()
                    return True
                if was_pressed:
                    return True

        return False

    def on_click_event(self):
        """Override in subclasses to trigger click actions."""
        pass

    def handle_keyboard_event(self, event) -> bool:
        """Override in editable widgets (like UITextBox) to receive keystrokes."""
        return False

    def draw_rect(self, x, y, w, h, color):
        """Utility to draw a filled 2D rectangle."""
        vertices = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
        indices = ((0, 1, 2), (2, 3, 0))
        batch = batch_for_shader(self.shader_2d, 'TRIS', {"pos": vertices}, indices=indices)
        
        self.shader_2d.uniform_float("color", color)
        batch.draw(self.shader_2d)

    def draw_rect_outline(self, x, y, w, h, color, line_width=1.0):
        """Utility to draw a rectangle border outline."""
        vertices = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
        indices = ((0, 1), (1, 2), (2, 3), (3, 0))
        batch = batch_for_shader(self.shader_2d, 'LINES', {"pos": vertices}, indices=indices)
        
        gpu.state.line_width_set(line_width)
        self.shader_2d.uniform_float("color", color)
        batch.draw(self.shader_2d)
        gpu.state.line_width_set(1.0)

    @property
    def shader_smooth_2d(self):
        if not hasattr(self, "_shader_smooth_2d") or self._shader_smooth_2d is None:
            self._shader_smooth_2d = gpu.shader.from_builtin('SMOOTH_COLOR')
        return self._shader_smooth_2d

    def draw_rounded_rect(self, x, y, w, h, radius, color):
        """
        Draw a filled 2D rectangle with smooth sub-pixel anti-aliased rounded corners.
        Automatically scales corner radii with Blender's resolution scale.
        """
        from .theme import BlenderTheme
        scale = BlenderTheme.get_ui_scale()

        if isinstance(radius, (int, float)):
            scaled_radius = float(radius) * scale
        else:
            scaled_radius = [float(val) * scale for val in radius]

        try:
            from .shapes import GpuShapes
            GpuShapes.draw_smooth_rounded_rect(x, y, w, h, scaled_radius, color)
        except Exception:
            self._draw_rounded_rect_polygonal(x, y, w, h, scaled_radius, color)

    def _draw_rounded_rect_polygonal(self, x, y, w, h, radius, color):
        if isinstance(radius, (int, float)):
            r_tr = r_tl = r_bl = r_br = float(radius)
        else:
            r_tr, r_tl, r_bl, r_br = [float(val) for val in radius]

        max_r = min(w / 2.0, h / 2.0)
        r_tr = min(r_tr, max_r)
        r_tl = min(r_tl, max_r)
        r_bl = min(r_bl, max_r)
        r_br = min(r_br, max_r)

        import math
        segments = 16

        inner_pts = []
        corner_defs = [
            (x + w - r_tr, y + h - r_tr, r_tr, 0.0, 0.5 * math.pi),
            (x + r_tl,     y + h - r_tl, r_tl, 0.5 * math.pi, math.pi),
            (x + r_bl,     y + r_bl,     r_bl, math.pi, 1.5 * math.pi),
            (x + w - r_br, y + r_br,     r_br, 1.5 * math.pi, 2.0 * math.pi),
        ]

        for cx, cy, r_c, a_start, a_end in corner_defs:
            if r_c <= 0.1:
                inner_pts.append((cx, cy))
            else:
                for s in range(segments + 1):
                    theta = a_start + (a_end - a_start) * (s / segments)
                    cos_t = math.cos(theta)
                    sin_t = math.sin(theta)
                    inner_pts.append((cx + r_c * cos_t, cy + r_c * sin_t))

        center = (x + w / 2.0, y + h / 2.0)
        core_verts = [center] + inner_pts
        core_indices = []
        for i in range(1, len(inner_pts)):
            core_indices.append((0, i, i + 1))
        core_indices.append((0, len(inner_pts), 1))

        batch_core = batch_for_shader(self.shader_2d, 'TRIS', {"pos": core_verts}, indices=core_indices)
        self.shader_2d.uniform_float("color", color)
        batch_core.draw(self.shader_2d)

    def draw_rounded_rect_outline(self, x, y, w, h, radius, color, line_width=1.0):
        """
        Draw a crisp border outline ribbon for a rounded rectangle.
        Aligns along the exact perimeter without transparent gaps or artifacts.
        Automatically scales with Blender's resolution scale.
        """
        from .theme import BlenderTheme
        scale = BlenderTheme.get_ui_scale()

        if isinstance(radius, (int, float)):
            scaled_radius = float(radius) * scale
        else:
            scaled_radius = [float(val) * scale for val in radius]

        scaled_line_width = max(1.0, line_width * scale)

        try:
            from .shapes import GpuShapes
            GpuShapes.draw_smooth_rounded_rect_outline(x, y, w, h, scaled_radius, color, line_width=scaled_line_width)
        except Exception:
            self._draw_rounded_rect_outline_polygonal(x, y, w, h, scaled_radius, color, scaled_line_width)

    def _draw_rounded_rect_outline_polygonal(self, x, y, w, h, scaled_radius, color, scaled_line_width):
        r = min(scaled_radius if isinstance(scaled_radius, (int, float)) else min(scaled_radius), w / 2.0, h / 2.0)
        if r <= 0.5:
            self.draw_rect_outline(x, y, w, h, color, line_width=scaled_line_width)
            return

        import math
        segments = 16
        r_outer = r
        r_inner = max(0.0, r - scaled_line_width)

        corners = [
            (x + w - r, y + h - r, 0.0, 0.5 * math.pi),
            (x + r,     y + h - r, 0.5 * math.pi, math.pi),
            (x + r,     y + r,     math.pi, 1.5 * math.pi),
            (x + w - r, y + r,     1.5 * math.pi, 2.0 * math.pi),
        ]

        outer_pts = []
        inner_pts = []

        for cx, cy, a_start, a_end in corners:
            for s in range(segments + 1):
                theta = a_start + (a_end - a_start) * (s / segments)
                ct = math.cos(theta)
                st = math.sin(theta)
                outer_pts.append((cx + r_outer * ct, cy + r_outer * st))
                inner_pts.append((cx + r_inner * ct, cy + r_inner * st))

        n = len(outer_pts)
        verts = []
        indices = []

        for i in range(n):
            next_i = (i + 1) % n
            base_idx = len(verts)
            verts.extend([inner_pts[i], outer_pts[i], outer_pts[next_i], inner_pts[next_i]])
            indices.extend([
                (base_idx, base_idx + 1, base_idx + 2),
                (base_idx, base_idx + 2, base_idx + 3)
            ])

        batch = batch_for_shader(
            self.shader_2d,
            'TRIS',
            {"pos": verts},
            indices=indices
        )
        self.shader_2d.uniform_float("color", color)
        batch.draw(self.shader_2d)

    def draw_text(self, text, x, y, font_id=0, size=11, color=(1.0, 1.0, 1.0, 1.0), max_width=None):
        """Utility to draw text with Blender blf, with automatic UI resolution scaling and width clipping."""
        from .theme import BlenderTheme
        scaled_size = max(6, int(round(size * BlenderTheme.get_ui_scale())))
        
        try:
            blf.size(font_id, scaled_size)
        except TypeError:
            blf.size(font_id, scaled_size, 72)

        disp_text = str(text)
        if max_width and max_width > 10:
            tw, _ = blf.dimensions(font_id, disp_text)
            if tw > max_width:
                # Truncate and add ellipsis
                while len(disp_text) > 3 and tw > max_width:
                    disp_text = disp_text[:-1]
                    tw, _ = blf.dimensions(font_id, disp_text + "..")
                disp_text = disp_text + ".."
            
        blf.color(font_id, *color)
        blf.position(font_id, x, y, 0)
        blf.draw(font_id, disp_text)

    def get_text_dimensions(self, text, font_id=0, size=11):
        """Returns (width, height) of given text, respecting UI resolution scale."""
        from .theme import BlenderTheme
        scaled_size = max(6, int(round(size * BlenderTheme.get_ui_scale())))
        
        try:
            blf.size(font_id, scaled_size)
        except TypeError:
            blf.size(font_id, scaled_size, 72)
        return blf.dimensions(font_id, str(text))

    def draw(self, origin_x, origin_y):
        """Render method to be overridden by child classes."""
        pass
