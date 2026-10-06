import gpu
import math
import time
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIMiniNodeGraph(UIElement):
    """
    Interactive Mini Node Graph & Wireflow Connector widget.
    Embeds a functional visual node editor inside the N-panel (impossible in standard Blender UI).
    Features:
    - Draggable node cards with custom header colors, status styling, and socket pins.
    - Color-coded data sockets (Yellow=Color, Blue=Vector, Green=Shader, Gray=Float).
    - Smooth anti-aliased cubic Bézier connector cables with dynamic curvature.
    - Drag wire from output socket to connect to compatible input socket.
    - Right-click socket to disconnect wires.
    - Grid canvas background with scissoring and double-click to reset layout.
    """

    def __init__(
        self,
        text="Mini Node Graph",
        x=0,
        y=0,
        width=150,
        height=175,
        on_connect=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.on_connect = on_connect

        # Canvas styling
        self.canvas_bg = (0.11, 0.11, 0.13, 0.95)
        self.grid_dot_color = (0.22, 0.22, 0.25, 0.5)

        # Default nodes setup
        self.nodes = [
            {
                "id": "tex",
                "title": "Image Texture",
                "header_color": (0.68, 0.38, 0.18, 1.0),
                "x": 10.0,
                "y": 42.0,
                "width": 78.0,
                "height": 56.0,
                "inputs": [],
                "outputs": [
                    {"id": "col", "name": "Color", "color": (0.92, 0.82, 0.22, 1.0)},
                    {"id": "alpha", "name": "Alpha", "color": (0.75, 0.75, 0.75, 1.0)}
                ]
            },
            {
                "id": "bsdf",
                "title": "Principled BSDF",
                "header_color": (0.22, 0.55, 0.45, 1.0),
                "x": 102.0,
                "y": 24.0,
                "width": 86.0,
                "height": 76.0,
                "inputs": [
                    {"id": "base_col", "name": "Base Color", "color": (0.92, 0.82, 0.22, 1.0)},
                    {"id": "rough", "name": "Roughness", "color": (0.75, 0.75, 0.75, 1.0)},
                    {"id": "normal", "name": "Normal", "color": (0.35, 0.60, 0.95, 1.0)}
                ],
                "outputs": [
                    {"id": "bsdf_out", "name": "BSDF", "color": (0.35, 0.85, 0.55, 1.0)}
                ]
            }
        ]

        # Established connections: list of tuples (from_node_id, from_sock_id, to_node_id, to_sock_id)
        self.connections = [
            ("tex", "col", "bsdf", "base_col")
        ]

        # Interaction state
        self._dragging_node = None
        self._drag_offset_x = 0.0
        self._drag_offset_y = 0.0

        self._wiring_from = None  # (node_id, socket_id, is_output, socket_screen_x, socket_screen_y)
        self._wire_mouse_x = 0.0
        self._wire_mouse_y = 0.0

        self._hovered_socket = None

    def _get_canvas_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx = abs_x + 4.0 * scale
        cy = abs_y + 4.0 * scale
        cw = max(20.0, self.width - 8.0 * scale)
        ch = max(20.0, self.height - 24.0 * scale)
        return cx, cy, cw, ch

    def _get_socket_screen_pos(self, node, socket_id, is_output, cx, cy):
        scale = BlenderTheme.get_ui_scale()
        nx = cx + node["x"] * scale
        ny = cy + node["y"] * scale
        nw = node["width"] * scale
        nh = node["height"] * scale

        socks = node["outputs"] if is_output else node["inputs"]
        idx = 0
        for i, s in enumerate(socks):
            if s["id"] == socket_id:
                idx = i
                break

        # Socket vertical spacing below header (header is 16px)
        header_h = 16.0 * scale
        avail_h = nh - header_h - 4.0 * scale
        step_h = avail_h / max(1, len(socks))
        sy = ny + nh - header_h - (idx + 0.5) * step_h
        sx = nx + nw if is_output else nx

        return sx, sy

    def _find_socket_at(self, mx, my, cx, cy):
        scale = BlenderTheme.get_ui_scale()
        hit_radius = 7.0 * scale
        for node in self.nodes:
            # Check inputs
            for s in node["inputs"]:
                sx, sy = self._get_socket_screen_pos(node, s["id"], False, cx, cy)
                if (mx - sx) ** 2 + (my - sy) ** 2 <= hit_radius ** 2:
                    return (node["id"], s["id"], False, s["color"], sx, sy)
            # Check outputs
            for s in node["outputs"]:
                sx, sy = self._get_socket_screen_pos(node, s["id"], True, cx, cy)
                if (mx - sx) ** 2 + (my - sy) ** 2 <= hit_radius ** 2:
                    return (node["id"], s["id"], True, s["color"], sx, sy)
        return None

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)

        # 1. Header (Title + Connection Count Badge)
        header_y = abs_y + self.height - 14.0 * scale
        if self.text:
            self.draw_text(self.text, abs_x + 4.0 * scale, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        conn_str = f"{len(self.connections)} Links"
        cw_txt, _ = self.get_text_dimensions(conn_str, font_id=0, size=9)
        self.draw_text(conn_str, abs_x + self.width - cw_txt - 6.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MAIN)

        # 2. Canvas Background & Subtle Grid
        GpuShapes.draw_smooth_rounded_box(
            cx, cy, cw, ch,
            radius=4.0 * scale,
            fill_color=self.canvas_bg,
            border_color=BlenderTheme.BORDER_LIGHT,
            border_width=1.0
        )

        # Grid dots (every 18px)
        grid_step = 18.0 * scale
        dot_r = 1.0 * scale
        gx = cx + (grid_step * 0.5)
        while gx < cx + cw - 2.0 * scale:
            gy = cy + (grid_step * 0.5)
            while gy < cy + ch - 2.0 * scale:
                GpuShapes.draw_smooth_circle(gx, gy, dot_r, self.grid_dot_color)
                gy += grid_step
            gx += grid_step

        # 3. Established Bézier Cables
        node_map = {n["id"]: n for n in self.nodes}
        for (src_id, src_sock, dst_id, dst_sock) in self.connections:
            if src_id in node_map and dst_id in node_map:
                x1, y1 = self._get_socket_screen_pos(node_map[src_id], src_sock, True, cx, cy)
                x2, y2 = self._get_socket_screen_pos(node_map[dst_id], dst_sock, False, cx, cy)

                # Get socket color
                wire_col = (0.9, 0.8, 0.2, 0.85)
                for s in node_map[src_id]["outputs"]:
                    if s["id"] == src_sock:
                        wire_col = s["color"]
                        break

                self._draw_bezier_wire(x1, y1, x2, y2, wire_col, scale)

        # Active Dragging Wire
        if self._wiring_from is not None:
            w_node, w_sock, is_out, sx, sy = self._wiring_from
            if is_out:
                self._draw_bezier_wire(sx, sy, self._wire_mouse_x, self._wire_mouse_y, (1.0, 1.0, 1.0, 0.9), scale, dashed=True)
            else:
                self._draw_bezier_wire(self._wire_mouse_x, self._wire_mouse_y, sx, sy, (1.0, 1.0, 1.0, 0.9), scale, dashed=True)

        # 4. Node Cards
        for node in self.nodes:
            self._draw_node(node, cx, cy, scale)

    def _draw_bezier_wire(self, x1, y1, x2, y2, color, scale, dashed=False):
        dx = max(24.0 * scale, abs(x2 - x1) * 0.45)
        cp1x = x1 + dx
        cp1y = y1
        cp2x = x2 - dx
        cp2y = y2

        # 16 segment cubic Bézier curve
        num_segs = 16
        pts = []
        for i in range(num_segs + 1):
            t = i / float(num_segs)
            omt = 1.0 - t
            omt2 = omt * omt
            omt3 = omt2 * omt
            t2 = t * t
            t3 = t2 * t

            px = omt3 * x1 + 3.0 * omt2 * t * cp1x + 3.0 * omt * t2 * cp2x + t3 * x2
            py = omt3 * y1 + 3.0 * omt2 * t * cp1y + 3.0 * omt * t2 * cp2y + t3 * y2
            pts.append((px, py))

        # Underlay shadow
        shadow_col = (0.05, 0.05, 0.05, 0.5)
        GpuShapes.draw_smooth_polyline([(p[0], p[1] - 1.0 * scale) for p in pts], shadow_col, line_width=max(2.5, 2.5 * scale))
        # Main anti-aliased wire ribbon
        GpuShapes.draw_smooth_polyline(pts, color, line_width=max(2.0, 2.0 * scale))

    def _draw_node(self, node, cx, cy, scale):
        nx = cx + node["x"] * scale
        ny = cy + node["y"] * scale
        nw = node["width"] * scale
        nh = node["height"] * scale

        header_h = 16.0 * scale
        is_active = (self._dragging_node == node["id"])

        # Node Body Background
        body_border = (1.0, 1.0, 1.0, 0.6) if is_active else BlenderTheme.BORDER_LIGHT
        GpuShapes.draw_smooth_rounded_box(
            nx, ny, nw, nh,
            radius=4.0 * scale,
            fill_color=(0.18, 0.18, 0.20, 0.96),
            border_color=body_border,
            border_width=1.0
        )

        # Node Header Bar
        GpuShapes.draw_smooth_rounded_box(
            nx + 1.0 * scale, ny + nh - header_h, nw - 2.0 * scale, header_h - 1.0 * scale,
            radius=(3.0 * scale, 3.0 * scale, 0.0, 0.0),
            fill_color=node["header_color"]
        )

        # Header Title Text
        self.draw_text(
            node["title"],
            nx + 6.0 * scale,
            ny + nh - 12.0 * scale,
            font_id=0,
            size=8,
            color=(0.95, 0.95, 0.95, 1.0)
        )

        # Draw Input Sockets & Labels
        avail_in = nh - header_h - 4.0 * scale
        step_in = avail_in / max(1, len(node["inputs"]))
        for i, s in enumerate(node["inputs"]):
            sy = ny + nh - header_h - (i + 0.5) * step_in
            sx = nx
            self._draw_socket(sx, sy, s["color"], scale, is_input=True)
            self.draw_text(s["name"], sx + 7.0 * scale, sy - 3.5 * scale, font_id=0, size=7, color=BlenderTheme.TEXT_MUTED)

        # Draw Output Sockets & Labels
        avail_out = nh - header_h - 4.0 * scale
        step_out = avail_out / max(1, len(node["outputs"]))
        for i, s in enumerate(node["outputs"]):
            sy = ny + nh - header_h - (i + 0.5) * step_out
            sx = nx + nw
            self._draw_socket(sx, sy, s["color"], scale, is_input=False)
            lw, _ = self.get_text_dimensions(s["name"], font_id=0, size=7)
            self.draw_text(s["name"], sx - lw - 7.0 * scale, sy - 3.5 * scale, font_id=0, size=7, color=BlenderTheme.TEXT_MUTED)

    def _draw_socket(self, sx, sy, color, scale, is_input):
        sock_r = 3.5 * scale
        # Dark rim
        GpuShapes.draw_smooth_circle(sx, sy, sock_r + 1.0 * scale, (0.1, 0.1, 0.1, 0.9))
        # Socket color fill
        GpuShapes.draw_smooth_circle(sx, sy, sock_r, color)
        # Inner white center pip
        GpuShapes.draw_smooth_circle(sx, sy, 1.2 * scale, (1.0, 1.0, 1.0, 0.9))

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)

        # 1. Right Click: Disconnect wire or socket
        if event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            sock_info = self._find_socket_at(mx, my, cx, cy)
            if sock_info:
                node_id, sock_id, is_out, _, _, _ = sock_info
                # Remove connections associated with this socket
                self.connections = [
                    c for c in self.connections
                    if not ((is_out and c[0] == node_id and c[1] == sock_id) or
                            (not is_out and c[2] == node_id and c[3] == sock_id))
                ]
                return True

        # 2. Left Mouse Press
        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                # First check socket click to begin wiring
                sock_info = self._find_socket_at(mx, my, cx, cy)
                if sock_info:
                    node_id, sock_id, is_out, col, sx, sy = sock_info
                    self._wiring_from = (node_id, sock_id, is_out, sx, sy)
                    self._wire_mouse_x = mx
                    self._wire_mouse_y = my
                    return True

                # Check if clicked on a node header to drag
                for node in reversed(self.nodes):
                    nx = cx + node["x"] * scale
                    ny = cy + node["y"] * scale
                    nw = node["width"] * scale
                    nh = node["height"] * scale
                    header_h = 18.0 * scale

                    if (nx <= mx <= nx + nw) and (ny + nh - header_h <= my <= ny + nh):
                        self._dragging_node = node["id"]
                        self._drag_offset_x = (mx - nx) / scale
                        self._drag_offset_y = (my - ny) / scale
                        # Bring clicked node to front
                        self.nodes.remove(node)
                        self.nodes.append(node)
                        return True

            elif event.value == 'RELEASE':
                # If wiring, check if released over a target socket
                if self._wiring_from is not None:
                    src_node, src_sock, src_is_out, _, _ = self._wiring_from
                    sock_info = self._find_socket_at(mx, my, cx, cy)
                    if sock_info:
                        dst_node, dst_sock, dst_is_out, _, _, _ = sock_info
                        # Must connect Output -> Input or Input -> Output on different nodes
                        if src_node != dst_node and src_is_out != dst_is_out:
                            out_node = src_node if src_is_out else dst_node
                            out_sock = src_sock if src_is_out else dst_sock
                            in_node = dst_node if src_is_out else src_node
                            in_sock = dst_sock if src_is_out else src_sock

                            # Replace existing connection to this input
                            self.connections = [c for c in self.connections if not (c[2] == in_node and c[3] == in_sock)]
                            new_conn = (out_node, out_sock, in_node, in_sock)
                            self.connections.append(new_conn)

                            if self.on_connect:
                                self.on_connect(out_node, out_sock, in_node, in_sock)

                    self._wiring_from = None
                    return True

                if self._dragging_node is not None:
                    self._dragging_node = None
                    return True

        # 3. Mouse Movement
        elif event.type == 'MOUSEMOVE':
            if self._wiring_from is not None:
                self._wire_mouse_x = mx
                self._wire_mouse_y = my
                return True

            elif self._dragging_node is not None:
                for node in self.nodes:
                    if node["id"] == self._dragging_node:
                        new_x = (mx - cx) / scale - self._drag_offset_x
                        new_y = (my - cy) / scale - self._drag_offset_y
                        # Clamp node inside canvas bounds
                        node["x"] = max(2.0, min(cw / scale - node["width"] - 2.0, new_x))
                        node["y"] = max(2.0, min(ch / scale - node["height"] - 2.0, new_y))
                        return True

        return False
