import gpu
import math
from gpu_extras.batch import batch_for_shader
from .theme import BlenderTheme

def _dist_segment(px, py, ax, ay, bx, by):
    """Distance from point (px, py) to line segment (ax, ay)-(bx, by)."""
    pax, pay = px - ax, py - ay
    bax, bay = bx - ax, by - ay
    denom = bax * bax + bay * bay + 1e-9
    h = max(0.0, min(1.0, (pax * bax + pay * bay) / denom))
    return math.hypot(pax - bax * h, pay - bay * h)

def _generate_icon_pixels(icon_name, res=64):
    """
    Generate an anti-aliased 64x64 RGBA float buffer using Signed Distance Fields (SDF).
    Returns list of floats suitable for gpu.types.Buffer('FLOAT', ...).
    """
    buf = []
    w = 2.0 / res
    for j in range(res):
        y = (j + 0.5) / res * 2.0 - 1.0
        for i in range(res):
            x = (i + 0.5) / res * 2.0 - 1.0
            d = 1.0

            if icon_name == 'CHECK':
                d1 = _dist_segment(x, y, -0.6, -0.05, -0.15, -0.55) - 0.13
                d2 = _dist_segment(x, y, -0.15, -0.55, 0.65, 0.55) - 0.13
                d = min(d1, d2)

            elif icon_name == 'CHEVRON_DOWN':
                d1 = _dist_segment(x, y, -0.55, 0.25, 0.0, -0.3) - 0.12
                d2 = _dist_segment(x, y, 0.0, -0.3, 0.55, 0.25) - 0.12
                d = min(d1, d2)

            elif icon_name == 'CHEVRON_RIGHT':
                d1 = _dist_segment(x, y, -0.25, 0.55, 0.3, 0.0) - 0.12
                d2 = _dist_segment(x, y, 0.3, 0.0, -0.25, -0.55) - 0.12
                d = min(d1, d2)

            elif icon_name == 'PLUS':
                d1 = _dist_segment(x, y, -0.65, 0.0, 0.65, 0.0) - 0.13
                d2 = _dist_segment(x, y, 0.0, -0.65, 0.0, 0.65) - 0.13
                d = min(d1, d2)

            elif icon_name == 'CLOSE':
                d1 = _dist_segment(x, y, -0.55, -0.55, 0.55, 0.55) - 0.13
                d2 = _dist_segment(x, y, -0.55, 0.55, 0.55, -0.55) - 0.13
                d = min(d1, d2)

            elif icon_name == 'GEAR':
                r = math.hypot(x, y)
                ang = math.atan2(y, x)
                sector = math.pi / 6.0
                rel_ang = abs((ang % (2.0 * sector)) - sector)
                r_max = 0.82 if rel_ang < (sector * 0.46) else 0.60
                d_out = r - r_max
                d_hole = 0.26 - r
                d = max(d_out, d_hole)

            elif icon_name == 'EYE':
                # Upper and lower circular arcs forming almond eye
                r_top = math.hypot(x, y + 0.65) - 1.05
                r_bot = math.hypot(x, y - 0.65) - 1.05
                almond_dist = max(r_top, r_bot)
                ring_d = abs(almond_dist + 0.08) - 0.09
                pupil_d = math.hypot(x, y) - 0.28
                d = min(ring_d, pupil_d)

            elif icon_name == 'LOCK':
                # Padlock body
                dx = max(0.0, abs(x) - 0.50)
                dy = max(0.0, abs(y + 0.35) - 0.35)
                body_d = math.hypot(dx, dy) - 0.12
                # Padlock shackle arch
                r_shackle = math.hypot(x, y - 0.15)
                shackle_ring = abs(r_shackle - 0.33) - 0.11
                if y < 0.15:
                    shackle_ring = max(shackle_ring, abs(x) - 0.44)
                d = min(body_d, shackle_ring)

            elif icon_name == 'SEARCH':
                # Magnifying lens ring
                r_glass = math.hypot(x + 0.16, y - 0.16)
                ring_d = abs(r_glass - 0.40) - 0.10
                # Angled handle
                handle_d = _dist_segment(x, y, 0.18, -0.18, 0.65, -0.65) - 0.12
                d = min(ring_d, handle_d)

            # Sub-pixel smoothstep anti-aliasing
            alpha = max(0.0, min(1.0, 0.5 - d / w))
            buf.extend([1.0, 1.0, 1.0, alpha])
    return buf


class UIIcon:
    """
    Hardware-accelerated GPU icon drawer using Blender's built-in IMAGE_COLOR shader.
    Renders high-resolution (64x64) anti-aliased textures with sub-pixel bilinear filtering.
    """
    _TEXTURE_CACHE = {}
    _SHADER_IMAGE_COLOR = None

    @classmethod
    def _get_shader(cls):
        if cls._SHADER_IMAGE_COLOR is None:
            cls._SHADER_IMAGE_COLOR = gpu.shader.from_builtin('IMAGE_COLOR')
        return cls._SHADER_IMAGE_COLOR

    @classmethod
    def _get_icon_texture(cls, icon_type):
        icon_key = str(icon_type).upper()
        if icon_key not in cls._TEXTURE_CACHE:
            try:
                res = 64
                pixels = _generate_icon_pixels(icon_key, res=res)
                buf = gpu.types.Buffer('FLOAT', res * res * 4, pixels)
                tex = gpu.types.GPUTexture((res, res), format='RGBA16F', data=buf)
                tex.filter_mode(True)  # Enable linear bilinear filtering for smooth downsampling
                cls._TEXTURE_CACHE[icon_key] = tex
            except Exception as e:
                print(f"[blgpu] Failed to generate icon texture for {icon_key}: {e}")
                return None
        return cls._TEXTURE_CACHE.get(icon_key)

    @classmethod
    def draw_icon(cls, icon_type, center_x, center_y, size=12, color=(0.86, 0.86, 0.86, 1.0), stroke_width=1.0):
        """
        Draw anti-aliased icon centered at (center_x, center_y) using IMAGE_COLOR shader.
        """
        tex = cls._get_icon_texture(icon_type)
        if not tex:
            return

        scale = BlenderTheme.get_ui_scale()
        s = size * scale
        hs = s * 0.5

        x0 = center_x - hs
        x1 = center_x + hs
        y0 = center_y - hs
        y1 = center_y + hs

        shader = cls._get_shader()
        pos = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        tex_coord = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))

        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": pos, "texCoord": tex_coord})

        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_sampler("image", tex)
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_vector_icon(cls, icon_type, center_x, center_y, size=12, color=(0.86, 0.86, 0.86, 1.0), stroke_width=1.0):
        """
        Backward-compatible alias for draw_icon.
        """
        cls.draw_icon(icon_type, center_x, center_y, size=size, color=color, stroke_width=stroke_width)

