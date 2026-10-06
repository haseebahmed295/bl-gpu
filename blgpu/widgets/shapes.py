import gpu
import math
from gpu_extras.batch import batch_for_shader

class GpuShapes:
    """
    Hardware-accelerated sub-pixel anti-aliased vector rendering using custom GPU shaders.
    Replaces deprecated/aliased GL_LINES with silky-smooth quad ribbons, SDF rings, and discs.
    """
    _SHADER_POLYLINE = None
    _SHADER_RING = None
    _SHADER_CIRCLE = None
    _SHADER_ROUNDED_BOX = None
    _SHADER_HSV_WHEEL = None
    _SHADER_ORBIT_SPHERE = None

    @classmethod
    def get_polyline_shader(cls):
        if cls._SHADER_POLYLINE is None:
            info = gpu.types.GPUShaderCreateInfo()
            info.push_constant('MAT4', 'ModelViewProjectionMatrix')
            info.push_constant('VEC4', 'color')
            info.push_constant('FLOAT', 'halfWidth')

            info.vertex_in(0, 'VEC2', 'pos')
            info.vertex_in(1, 'FLOAT', 'lateralDist')

            stage = gpu.types.GPUStageInterfaceInfo('smooth_polyline_iface')
            stage.smooth('FLOAT', 'vDist')
            info.vertex_out(stage)

            info.vertex_source('''
            void main() {
                vDist = lateralDist;
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            }
            ''')

            info.fragment_out(0, 'VEC4', 'FragColor')
            info.fragment_source('''
            void main() {
                float dist = abs(vDist);
                float alpha = clamp(halfWidth + 0.5 - dist, 0.0, 1.0);
                FragColor = vec4(color.rgb, color.a * alpha);
            }
            ''')
            cls._SHADER_POLYLINE = gpu.shader.create_from_info(info)
        return cls._SHADER_POLYLINE

    @classmethod
    def get_ring_shader(cls):
        if cls._SHADER_RING is None:
            info = gpu.types.GPUShaderCreateInfo()
            info.push_constant('MAT4', 'ModelViewProjectionMatrix')
            info.push_constant('VEC4', 'color')
            info.push_constant('FLOAT', 'radius')
            info.push_constant('FLOAT', 'halfThickness')

            info.vertex_in(0, 'VEC2', 'pos')
            info.vertex_in(1, 'VEC2', 'localCoord')

            stage = gpu.types.GPUStageInterfaceInfo('smooth_ring_iface')
            stage.smooth('VEC2', 'uv')
            info.vertex_out(stage)

            info.vertex_source('''
            void main() {
                uv = localCoord;
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            }
            ''')

            info.fragment_out(0, 'VEC4', 'FragColor')
            info.fragment_source('''
            void main() {
                float dist = abs(length(uv) - radius);
                float alpha = clamp(halfThickness + 0.5 - dist, 0.0, 1.0);
                FragColor = vec4(color.rgb, color.a * alpha);
            }
            ''')
            cls._SHADER_RING = gpu.shader.create_from_info(info)
        return cls._SHADER_RING

    @classmethod
    def get_circle_shader(cls):
        if cls._SHADER_CIRCLE is None:
            info = gpu.types.GPUShaderCreateInfo()
            info.push_constant('MAT4', 'ModelViewProjectionMatrix')
            info.push_constant('VEC4', 'color')
            info.push_constant('FLOAT', 'radius')

            info.vertex_in(0, 'VEC2', 'pos')
            info.vertex_in(1, 'VEC2', 'localCoord')

            stage = gpu.types.GPUStageInterfaceInfo('smooth_circle_iface')
            stage.smooth('VEC2', 'uv')
            info.vertex_out(stage)

            info.vertex_source('''
            void main() {
                uv = localCoord;
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            }
            ''')

            info.fragment_out(0, 'VEC4', 'FragColor')
            info.fragment_source('''
            void main() {
                float dist = length(uv);
                float alpha = clamp(radius + 0.5 - dist, 0.0, 1.0);
                FragColor = vec4(color.rgb, color.a * alpha);
            }
            ''')
            cls._SHADER_CIRCLE = gpu.shader.create_from_info(info)
        return cls._SHADER_CIRCLE

    @classmethod
    def get_rounded_box_shader(cls):
        if cls._SHADER_ROUNDED_BOX is None:
            info = gpu.types.GPUShaderCreateInfo()
            info.push_constant('MAT4', 'ModelViewProjectionMatrix')
            info.push_constant('VEC4', 'fillColor')
            info.push_constant('VEC4', 'borderColor')
            info.push_constant('VEC4', 'radii')
            info.push_constant('VEC4', 'rectParams')

            info.vertex_in(0, 'VEC2', 'pos')
            info.vertex_in(1, 'VEC2', 'localCoord')

            stage = gpu.types.GPUStageInterfaceInfo('smooth_rounded_box_iface')
            stage.smooth('VEC2', 'uv')
            info.vertex_out(stage)

            info.vertex_source('''
            void main() {
                uv = localCoord;
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            }
            ''')

            info.fragment_out(0, 'VEC4', 'FragColor')
            info.fragment_source('''
            void main() {
                vec2 halfSize = rectParams.xy * 0.5;
                float borderWidth = rectParams.z;
                float r = (uv.x >= 0.0) ?
                    ((uv.y >= 0.0) ? radii.x : radii.y) :
                    ((uv.y >= 0.0) ? radii.w : radii.z);
                r = min(r, min(halfSize.x, halfSize.y));
                vec2 dVec = abs(uv) - halfSize + vec2(r);
                float dist = length(max(dVec, 0.0)) + min(max(dVec.x, dVec.y), 0.0) - r;

                float outerAlpha = clamp(0.5 - dist, 0.0, 1.0);
                if (outerAlpha <= 0.0) {
                    discard;
                }

                if (borderWidth > 0.0 && borderColor.a > 0.0) {
                    float distInner = dist + borderWidth;
                    float borderFactor = clamp(distInner + 0.5, 0.0, 1.0);
                    vec4 col = mix(fillColor, borderColor, borderFactor);
                    FragColor = vec4(col.rgb, col.a * outerAlpha);
                } else {
                    FragColor = vec4(fillColor.rgb, fillColor.a * outerAlpha);
                }
            }
            ''')
            cls._SHADER_ROUNDED_BOX = gpu.shader.create_from_info(info)
        return cls._SHADER_ROUNDED_BOX

    @classmethod
    def draw_smooth_line(cls, x1, y1, x2, y2, color, line_width=1.0):
        """Draw a single anti-aliased line segment with sub-pixel feathering."""
        cls.draw_smooth_lines([(x1, y1), (x2, y2)], color, line_width=line_width)

    @classmethod
    def draw_smooth_lines(cls, line_pairs, color, line_width=1.0):
        """
        Draw multiple anti-aliased line segments.
        line_pairs: [(p1_x, p1_y), (p2_x, p2_y), (p3_x, p3_y), (p4_x, p4_y), ...]
        """
        if len(line_pairs) < 2:
            return

        half_w = max(0.4, line_width * 0.5)
        pad = 1.0  # 1px anti-aliasing feathering
        R = half_w + pad

        verts = []
        dists = []
        indices = []

        shader = cls.get_polyline_shader()

        for i in range(0, len(line_pairs) - 1, 2):
            x1, y1 = line_pairs[i]
            x2, y2 = line_pairs[i + 1]
            dx = x2 - x1
            dy = y2 - y1
            L = math.hypot(dx, dy)
            if L < 1e-4:
                continue

            nx = (-dy / L) * R
            ny = (dx / L) * R

            b = len(verts)
            verts.extend([
                (x1 - nx, y1 - ny),
                (x2 - nx, y2 - ny),
                (x2 + nx, y2 + ny),
                (x1 + nx, y1 + ny)
            ])
            dists.extend([-R, -R, R, R])
            indices.extend([(b, b + 1, b + 2), (b, b + 2, b + 3)])

        if not verts:
            return

        batch = batch_for_shader(shader, 'TRIS', {"pos": verts, "lateralDist": dists}, indices=indices)
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("halfWidth", half_w)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_smooth_polyline(cls, points, color, line_width=2.0):
        """
        Draw a continuous anti-aliased polyline / spline curve with smooth joint connections.
        points: list of (x, y) coordinates
        """
        if len(points) < 2:
            return

        half_w = max(0.4, line_width * 0.5)
        pad = 1.0
        R = half_w + pad

        verts = []
        dists = []
        indices = []

        shader = cls.get_polyline_shader()

        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            dx = x2 - x1
            dy = y2 - y1
            L = math.hypot(dx, dy)
            if L < 1e-4:
                continue

            nx = (-dy / L) * R
            ny = (dx / L) * R

            b = len(verts)
            verts.extend([
                (x1 - nx, y1 - ny),
                (x2 - nx, y2 - ny),
                (x2 + nx, y2 + ny),
                (x1 + nx, y1 + ny)
            ])
            dists.extend([-R, -R, R, R])
            indices.extend([(b, b + 1, b + 2), (b, b + 2, b + 3)])

        if not verts:
            return

        batch = batch_for_shader(shader, 'TRIS', {"pos": verts, "lateralDist": dists}, indices=indices)
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("halfWidth", half_w)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

        # Draw small round joint discs to bridge sharp corners
        for px, py in points[1:-1]:
            cls.draw_smooth_circle(px, py, half_w, color)

    @classmethod
    def draw_smooth_ring(cls, cx, cy, radius, color, thickness=1.0):
        """
        Draw a mathematically perfect circular ring with anti-aliasing on a single quad.
        """
        half_thick = max(0.4, thickness * 0.5)
        pad = 1.5
        outer_extent = radius + half_thick + pad

        x0 = cx - outer_extent
        y0 = cy - outer_extent
        x1 = cx + outer_extent
        y1 = cy + outer_extent

        pos = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        coords = (
            (-outer_extent, -outer_extent),
            (outer_extent, -outer_extent),
            (outer_extent, outer_extent),
            (-outer_extent, outer_extent)
        )

        shader = cls.get_ring_shader()
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": pos, "localCoord": coords})

        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("radius", float(radius))
        shader.uniform_float("halfThickness", half_thick)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_smooth_circle(cls, cx, cy, radius, color):
        """
        Draw a mathematically perfect filled circular disc with sub-pixel anti-aliased edge.
        """
        pad = 1.5
        outer_extent = radius + pad

        x0 = cx - outer_extent
        y0 = cy - outer_extent
        x1 = cx + outer_extent
        y1 = cy + outer_extent

        pos = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        coords = (
            (-outer_extent, -outer_extent),
            (outer_extent, -outer_extent),
            (outer_extent, outer_extent),
            (-outer_extent, outer_extent)
        )

        shader = cls.get_circle_shader()
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": pos, "localCoord": coords})

        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("color", color)
        shader.uniform_float("radius", float(radius))
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_smooth_rounded_box(
        cls, x, y, width, height, radius=0.0,
        fill_color=(0.0, 0.0, 0.0, 0.0),
        border_color=(0.0, 0.0, 0.0, 0.0),
        border_width=0.0
    ):
        """
        Draw a hardware-accelerated anti-aliased rounded rectangle (box) using an analytical SDF shader.
        Supports fill, border, or both simultaneously on a single quad with sub-pixel feathering.
        radius can be a float or a tuple/list of 4 floats: (top_right, top_left, bottom_left, bottom_right).
        """
        if width <= 0 or height <= 0:
            return

        if isinstance(radius, (int, float)):
            r_tr = r_tl = r_bl = r_br = float(radius)
        else:
            radii = list(radius)
            if len(radii) == 4:
                r_tr, r_tl, r_bl, r_br = [float(v) for v in radii]
            elif len(radii) == 2:
                r_tr = r_tl = float(radii[0])
                r_br = r_bl = float(radii[1])
            else:
                r_tr = r_tl = r_bl = r_br = float(radii[0]) if radii else 0.0

        pad = 1.5
        x0 = x - pad
        y0 = y - pad
        x1 = x + width + pad
        y1 = y + height + pad

        hw = width * 0.5
        hh = height * 0.5

        pos = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
        coords = (
            (-hw - pad, -hh - pad),
            ( hw + pad, -hh - pad),
            ( hw + pad,  hh + pad),
            (-hw - pad,  hh + pad)
        )

        shader = cls.get_rounded_box_shader()
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": pos, "localCoord": coords})

        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("fillColor", fill_color)
        shader.uniform_float("borderColor", border_color)
        shader.uniform_float("radii", (r_tr, r_br, r_bl, r_tl))
        shader.uniform_float("rectParams", (float(width), float(height), float(border_width), 0.0))
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def draw_smooth_rounded_rect(cls, x, y, width, height, radius, color):
        """Draw a filled anti-aliased rounded rectangle."""
        cls.draw_smooth_rounded_box(x, y, width, height, radius=radius, fill_color=color)

    @classmethod
    def draw_smooth_rounded_rect_outline(cls, x, y, width, height, radius, color, line_width=1.0):
        """Draw an anti-aliased rounded rectangle border outline."""
        cls.draw_smooth_rounded_box(x, y, width, height, radius=radius, border_color=color, border_width=line_width)

    @classmethod
    def draw_smooth_box(cls, x, y, width, height, color):
        """Draw an anti-aliased rectangle."""
        cls.draw_smooth_rounded_box(x, y, width, height, radius=0.0, fill_color=color)

    @classmethod
    def draw_smooth_rect(cls, x, y, width, height, color):
        """Draw an anti-aliased rectangle."""
        cls.draw_smooth_rounded_box(x, y, width, height, radius=0.0, fill_color=color)

    @classmethod
    def get_hsv_wheel_shader(cls):
        if cls._SHADER_HSV_WHEEL is None:
            info = gpu.types.GPUShaderCreateInfo()
            info.push_constant('MAT4', 'ModelViewProjectionMatrix')
            info.push_constant('FLOAT', 'radius')
            info.push_constant('FLOAT', 'valMultiplier')
            info.push_constant('FLOAT', 'alpha')

            info.vertex_in(0, 'VEC2', 'pos')
            info.vertex_in(1, 'VEC2', 'localCoord')

            stage = gpu.types.GPUStageInterfaceInfo('smooth_hsv_wheel_iface')
            stage.smooth('VEC2', 'uv')
            info.vertex_out(stage)

            info.vertex_source('''
            void main() {
                uv = localCoord;
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            }
            ''')

            info.fragment_out(0, 'VEC4', 'FragColor')
            info.fragment_source('''
            vec3 hsv2rgb(vec3 c) {
                vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
                vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
                return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
            }

            void main() {
                float dist = length(uv);
                float edgeAlpha = clamp(radius + 0.5 - dist, 0.0, 1.0);
                if (edgeAlpha <= 0.0) {
                    discard;
                }
                float angle = atan(uv.y, uv.x);
                float hue = fract(angle / 6.283185307179586 + 1.0);
                float sat = clamp(dist / radius, 0.0, 1.0);
                vec3 rgb = hsv2rgb(vec3(hue, sat, valMultiplier));
                FragColor = vec4(rgb, alpha * edgeAlpha);
            }
            ''')
            cls._SHADER_HSV_WHEEL = gpu.shader.create_from_info(info)
        return cls._SHADER_HSV_WHEEL

    @classmethod
    def draw_hsv_wheel(cls, cx, cy, radius, value=1.0, alpha=1.0):
        """Draw an anti-aliased continuous HSV color wheel disc."""
        r = float(radius)
        pad = 1.5
        pr = r + pad
        pos = (
            (cx - pr, cy - pr),
            (cx + pr, cy - pr),
            (cx + pr, cy + pr),
            (cx - pr, cy + pr),
        )
        coords = (
            (-pr, -pr),
            ( pr, -pr),
            ( pr,  pr),
            (-pr,  pr),
        )
        shader = cls.get_hsv_wheel_shader()
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": pos, "localCoord": coords})

        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("radius", r)
        shader.uniform_float("valMultiplier", float(value))
        shader.uniform_float("alpha", float(alpha))
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    @classmethod
    def get_orbit_sphere_shader(cls):
        if cls._SHADER_ORBIT_SPHERE is None:
            info = gpu.types.GPUShaderCreateInfo()
            info.push_constant('MAT4', 'ModelViewProjectionMatrix')
            info.push_constant('FLOAT', 'radius')
            info.push_constant('VEC4', 'quat')
            info.push_constant('VEC3', 'baseColor')
            info.push_constant('FLOAT', 'alpha')

            info.vertex_in(0, 'VEC2', 'pos')
            info.vertex_in(1, 'VEC2', 'localCoord')

            stage = gpu.types.GPUStageInterfaceInfo('smooth_orbit_sphere_iface')
            stage.smooth('VEC2', 'uv')
            info.vertex_out(stage)

            info.vertex_source('''
            void main() {
                uv = localCoord;
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
            }
            ''')

            info.fragment_out(0, 'VEC4', 'FragColor')
            info.fragment_source('''
            vec3 rotateByQuat(vec4 q, vec3 v) {
                return v + 2.0 * cross(q.xyz, cross(q.xyz, v) + q.w * v);
            }

            void main() {
                float dist = length(uv);
                float edgeAlpha = clamp(radius + 0.5 - dist, 0.0, 1.0);
                if (edgeAlpha <= 0.0) {
                    discard;
                }

                float normDistSq = (dist * dist) / (radius * radius);
                if (normDistSq > 1.0) {
                    discard;
                }

                // View-space surface normal
                vec2 n_xy = uv / radius;
                float n_z = sqrt(max(0.0, 1.0 - normDistSq));
                vec3 N_view = vec3(n_xy, n_z);

                // Local-space coordinates via inverse quaternion
                vec3 N_local = rotateByQuat(vec4(-quat.xyz, quat.w), N_view);

                // Wireframe equator and meridian rings on sphere
                float eq = smoothstep(0.04, 0.015, abs(N_local.y));
                float mer = smoothstep(0.04, 0.015, abs(N_local.x));
                float rings = max(eq, mer);

                // Active direction pole dot (at local +Z)
                float poleDot = max(0.0, dot(N_local, vec3(0.0, 0.0, 1.0)));
                float targetPip = smoothstep(0.965, 0.992, poleDot);

                // Studio directional lighting
                vec3 L = normalize(vec3(0.45, 0.60, 0.70));
                float diff = max(dot(N_view, L), 0.0);
                float ambient = 0.22;

                vec3 H = normalize(L + vec3(0.0, 0.0, 1.0));
                float spec = pow(max(dot(N_view, H), 0.0), 22.0) * 0.38;
                float fresnel = pow(1.0 - n_z, 2.5) * 0.28;

                vec3 matCol = mix(baseColor, vec3(0.48, 0.55, 0.62), rings * 0.45);
                matCol = mix(matCol, vec3(0.25, 0.65, 1.0), targetPip * 0.95);

                vec3 finalRgb = (matCol * (ambient + diff * 0.78)) + vec3(spec) + (vec3(0.85, 0.90, 0.95) * fresnel);

                FragColor = vec4(finalRgb, alpha * edgeAlpha);
            }
            ''')
            cls._SHADER_ORBIT_SPHERE = gpu.shader.create_from_info(info)
        return cls._SHADER_ORBIT_SPHERE

    @classmethod
    def draw_orbit_sphere(cls, cx, cy, radius, quat=(0.0, 0.0, 0.0, 1.0), base_color=(0.28, 0.32, 0.36), alpha=1.0):
        """Draw an anti-aliased lit 3D orbit sphere with surface coordinate rings."""
        r = float(radius)
        pad = 1.5
        pr = r + pad
        pos = (
            (cx - pr, cy - pr),
            (cx + pr, cy - pr),
            (cx + pr, cy + pr),
            (cx - pr, cy + pr),
        )
        coords = (
            (-pr, -pr),
            ( pr, -pr),
            ( pr,  pr),
            (-pr,  pr),
        )
        shader = cls.get_orbit_sphere_shader()
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": pos, "localCoord": coords})

        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("radius", r)
        shader.uniform_float("quat", quat)
        shader.uniform_float("baseColor", base_color)
        shader.uniform_float("alpha", float(alpha))
        batch.draw(shader)
        gpu.state.blend_set('NONE')


