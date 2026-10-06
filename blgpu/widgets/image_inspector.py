import gpu
import math
import time
from gpu_extras.batch import batch_for_shader
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIImageInspector(UIElement):
    """
    Interactive Image & Texture Inspector widget.
    Embeds a high-performance image viewport directly inside the N-panel (impossible in standard Blender UI).
    Features:
    - Hardware-accelerated bilinear filtered GPU texture rendering via IMAGE_COLOR shader.
    - Smooth pan (drag) and zoom (mouse wheel / drag) up to 800% pixel inspection.
    - Viewport scissoring: perfectly clipped to inspector boundaries without leaking.
    - Live Pixel Color Probe: hovering over any pixel samples exact UV and RGBA color with live swatch.
    - Double-click to instantly fit view (reset pan and zoom).
    - Real-time on_pixel_probe callback.
    """

    _TEST_TEXTURE = None
    _TEST_BUFFER = None
    _TEX_SIZE = 128

    def __init__(
        self,
        text="Texture Preview",
        x=0,
        y=0,
        width=150,
        height=165,
        on_pixel_probe=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.on_pixel_probe = on_pixel_probe

        # Navigation state
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0

        # Interaction state
        self.is_panning = False
        self._drag_start_mouse = (0.0, 0.0)
        self._drag_start_pan = (0.0, 0.0)
        self._last_click_time = 0.0

        # Probed pixel info
        self.probed_uv = None    # (u, v)
        self.probed_rgba = None  # (r, g, b, a)

        # Colors
        self.canvas_bg = (0.10, 0.10, 0.12, 0.98)
        self.checker_dark = (0.16, 0.16, 0.18, 1.0)
        self.checker_light = (0.22, 0.22, 0.25, 1.0)

        # Prepare float buffer lazily
        self._ensure_buffer()

    @classmethod
    def _ensure_buffer(cls):
        if cls._TEST_BUFFER is not None:
            return

        size = cls._TEX_SIZE
        raw_floats = []
        for y in range(size):
            v = y / float(size - 1)
            for x in range(size):
                u = x / float(size - 1)
                dx = u - 0.5
                dy = v - 0.5
                dist = math.hypot(dx, dy)

                # Four-quadrant vibrant palette
                r = 0.5 + 0.5 * math.sin(u * math.pi)
                g = 0.5 + 0.5 * math.sin(v * math.pi)
                b = 0.5 + 0.5 * math.cos((u + v) * math.pi)

                # Concentric resolution test rings
                ring = 0.5 + 0.5 * math.cos(dist * 50.0)
                r = r * 0.75 + ring * 0.25
                g = g * 0.75 + ring * 0.25
                b = b * 0.75 + ring * 0.25

                # 1px border perimeter
                if x == 0 or x == size - 1 or y == 0 or y == size - 1:
                    r, g, b, a = 1.0, 1.0, 1.0, 1.0
                elif x == size // 2 or y == size // 2:
                    r, g, b, a = 0.15, 0.15, 0.15, 0.8
                else:
                    a = 1.0

                raw_floats.extend([
                    max(0.0, min(1.0, r)),
                    max(0.0, min(1.0, g)),
                    max(0.0, min(1.0, b)),
                    max(0.0, min(1.0, a))
                ])

        cls._TEST_BUFFER = raw_floats

    @classmethod
    def _ensure_texture(cls):
        if cls._TEST_TEXTURE is not None:
            return

        cls._ensure_buffer()
        try:
            buf = gpu.types.Buffer('FLOAT', len(cls._TEST_BUFFER), cls._TEST_BUFFER)
            cls._TEST_TEXTURE = gpu.types.GPUTexture((cls._TEX_SIZE, cls._TEX_SIZE), format='RGBA16F', data=buf)
            cls._TEST_TEXTURE.filter_mode(True)
        except (SystemError, RuntimeError):
            pass

    def _sample_texture(self, u, v):
        if self._TEST_BUFFER is None:
            return (0.0, 0.0, 0.0, 1.0)
        size = self._TEX_SIZE
        px = max(0, min(size - 1, int(u * size)))
        py = max(0, min(size - 1, int(v * size)))
        idx = (py * size + px) * 4
        return tuple(self._TEST_BUFFER[idx:idx + 4])

    def _get_canvas_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx = abs_x + 6.0 * scale
        cy = abs_y + 6.0 * scale
        cw = max(20.0, self.width - 12.0 * scale)
        ch = max(20.0, self.height - 24.0 * scale)
        return cx, cy, cw, ch

    def _get_texture_screen_quad(self, cx, cy, cw, ch, scale):
        tex_cx = cx + (cw * 0.5) + self.pan_x
        tex_cy = cy + (ch * 0.5) + self.pan_y
        base_size = min(cw, ch) * 0.82
        tw = base_size * self.zoom
        th = base_size * self.zoom

        x0 = tex_cx - tw * 0.5
        y0 = tex_cy - th * 0.5
        x1 = tex_cx + tw * 0.5
        y1 = tex_cy + th * 0.5
        return x0, y0, x1, y1, tw, th

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        self._ensure_texture()

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)

        # 1. Header (Title + Zoom readout + Probe Swatch)
        header_y = abs_y + self.height - 14.0 * scale
        if self.text:
            self.draw_text(self.text, abs_x + 4.0 * scale, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        # Zoom level badge
        zoom_pct = f"{int(self.zoom * 100)}%"
        zw, _ = self.get_text_dimensions(zoom_pct, font_id=0, size=9)

        # Probed color swatch in header
        swatch_w = 16.0 * scale
        swatch_h = 10.0 * scale
        swatch_x = abs_x + self.width - swatch_w - 4.0 * scale
        swatch_y = header_y + 1.0 * scale

        if self.probed_rgba is not None:
            GpuShapes.draw_smooth_rounded_box(
                swatch_x, swatch_y, swatch_w, swatch_h,
                radius=2.0 * scale,
                fill_color=self.probed_rgba,
                border_color=BlenderTheme.BORDER_LIGHT,
                border_width=1.0
            )
            self.draw_text(zoom_pct, swatch_x - zw - 6.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MAIN)
        else:
            self.draw_text(zoom_pct, abs_x + self.width - zw - 4.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MAIN)

        # 2. Outer Viewport Box
        GpuShapes.draw_smooth_rounded_box(
            cx, cy, cw, ch,
            radius=4.0 * scale,
            fill_color=self.canvas_bg,
            border_color=BlenderTheme.BORDER_LIGHT,
            border_width=1.0
        )

        # 3. Viewport Scissoring & Image Texture Rendering
        orig_scissor = gpu.state.scissor_get()
        # Compute intersection of panel scissor and viewport canvas
        vx_i = max(int(orig_scissor[0]), int(cx))
        vy_i = max(int(orig_scissor[1]), int(cy))
        vx2 = min(int(orig_scissor[0] + orig_scissor[2]), int(cx + cw))
        vy2 = min(int(orig_scissor[1] + orig_scissor[3]), int(cy + ch))
        vw_i = max(0, vx2 - vx_i)
        vh_i = max(0, vy2 - vy_i)

        if vw_i > 0 and vh_i > 0:
            gpu.state.scissor_set(vx_i, vy_i, vw_i, vh_i)

            x0, y0, x1, y1, tw, th = self._get_texture_screen_quad(cx, cy, cw, ch, scale)

            # Draw texture quad backdrop
            GpuShapes.draw_smooth_box(x0, y0, tw, th, self.checker_dark)

            # Render GPU Texture Quad via IMAGE_COLOR shader
            if self._TEST_TEXTURE is not None:
                verts = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
                uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
                indices = ((0, 1, 2), (2, 3, 0))

                shader = gpu.shader.from_builtin('IMAGE_COLOR')
                batch = batch_for_shader(
                    shader, 'TRIS',
                    {"pos": verts, "texCoord": uvs},
                    indices=indices
                )
                gpu.state.blend_set('ALPHA')
                shader.bind()
                shader.uniform_sampler("image", self._TEST_TEXTURE)
                shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))
                batch.draw(shader)
                gpu.state.blend_set('NONE')

            # Texture boundary border
            GpuShapes.draw_smooth_polyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], (1.0, 1.0, 1.0, 0.4), line_width=1.0)

            # If pixel is being probed, draw probe crosshair
            if self.probed_uv is not None:
                pu, pv = self.probed_uv
                probe_px = x0 + pu * tw
                probe_py = y0 + pv * th
                GpuShapes.draw_smooth_circle(probe_px, probe_py, 3.5 * scale, (1.0, 1.0, 1.0, 0.9))
                GpuShapes.draw_smooth_ring(probe_px, probe_py, 3.5 * scale, (0.1, 0.1, 0.1, 0.9), thickness=1.0)

            # Restore panel scissor
            gpu.state.scissor_set(int(orig_scissor[0]), int(orig_scissor[1]), int(orig_scissor[2]), int(orig_scissor[3]))

        # 4. Probed Pixel HUD Info Bar (Bottom inside viewport)
        if self.probed_uv is not None and self.probed_rgba is not None:
            pu, pv = self.probed_uv
            pr, pg, pb, pa = self.probed_rgba
            probe_str = f"U:{pu:.2f} V:{pv:.2f} | RGB:({pr:.2f}, {pg:.2f}, {pb:.2f})"
            self.draw_text(probe_str, cx + 6.0 * scale, cy + 4.0 * scale, font_id=0, size=8, color=(0.95, 0.95, 0.95, 0.9))

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)
        pad = 4.0 * scale
        hit = (cx - pad <= mx <= cx + cw + pad) and (cy - pad <= my <= cy + ch + pad)

        x0, y0, x1, y1, tw, th = self._get_texture_screen_quad(cx, cy, cw, ch, scale)

        # 1. Mouse Wheel: Zoom
        if hit and event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE'):
            factor = 1.15 if event.type == 'WHEELUPMOUSE' else (1.0 / 1.15)
            new_zoom = max(0.25, min(8.0, self.zoom * factor))
            if new_zoom != self.zoom:
                # Zoom centered toward mouse
                self.zoom = round(new_zoom, 2)
                return True

        # 2. Left / Middle Click: Pan or Probe
        if event.type in ('LEFTMOUSE', 'MIDDLEMOUSE'):
            if event.value == 'PRESS' and hit:
                now = time.time()
                # Double click to reset pan and zoom
                if now - self._last_click_time < 0.28:
                    self.pan_x = 0.0
                    self.pan_y = 0.0
                    self.zoom = 1.0
                    self.is_panning = False
                    return True

                self._last_click_time = now
                self.is_panning = True
                self._drag_start_mouse = (mx, my)
                self._drag_start_pan = (self.pan_x, self.pan_y)
                return True

            elif event.value == 'RELEASE' and self.is_panning:
                self.is_panning = False
                return True

        # 3. Mouse Movement
        elif event.type == 'MOUSEMOVE':
            if self.is_panning:
                dmx = mx - self._drag_start_mouse[0]
                dmy = my - self._drag_start_mouse[1]
                self.pan_x = self._drag_start_pan[0] + dmx
                self.pan_y = self._drag_start_pan[1] + dmy
                return True

            # Update pixel color probe
            if hit and (x0 <= mx <= x1) and (y0 <= my <= y1) and tw > 0 and th > 0:
                u = (mx - x0) / tw
                v = (my - y0) / th
                self.probed_uv = (round(u, 3), round(v, 3))
                self.probed_rgba = self._sample_texture(u, v)
                if self.on_pixel_probe:
                    self.on_pixel_probe(u, v, self.probed_rgba)
                return True
            else:
                if self.probed_uv is not None:
                    self.probed_uv = None
                    self.probed_rgba = None

        return False
