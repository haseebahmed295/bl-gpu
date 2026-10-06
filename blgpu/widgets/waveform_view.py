import gpu
import math
import time
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UIWaveformView(UIElement):
    """
    Interactive Audio Waveform & Loop Region Visualizer widget.
    Renders an anti-aliased audio peak envelope with decibel grid lines, draggable loop selection handles,
    and a real-time playback playhead (impossible in standard Blender UI).
    Features:
    - Mirrored audio peak envelope bars with dynamic active-region coloring.
    - Decibel scale reference lines (0 dB center, ±6 dB headroom).
    - Draggable Loop In / Loop Out boundary markers to define audio ranges.
    - Draggable high-visibility playhead cursor.
    - Real-time on_scrub and on_loop_change callbacks.
    """

    def __init__(
        self,
        text="Audio Track",
        duration=8.0,
        playhead_time=2.4,
        loop_in=1.5,
        loop_out=6.2,
        samples=None,
        x=0,
        y=0,
        width=150,
        height=85,
        on_scrub=None,
        on_loop_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.duration = float(duration)
        self.playhead_time = float(playhead_time)
        self.loop_in = float(loop_in)
        self.loop_out = float(loop_out)
        self.on_scrub = on_scrub
        self.on_loop_change = on_loop_change

        # Generate realistic procedural audio envelope if samples not provided
        if samples is not None:
            self.samples = list(samples)
        else:
            self.samples = self._generate_procedural_peaks(64)

        # Interaction state
        self._dragging_target = None  # 'PLAYHEAD', 'LOOP_IN', 'LOOP_OUT', or None
        self._last_click_time = 0.0

        # Colors
        self.canvas_bg = (0.13, 0.13, 0.15, 0.95)
        self.centerline_color = (0.28, 0.28, 0.32, 0.6)
        self.grid_color = (0.20, 0.20, 0.24, 0.4)
        self.active_bar_color = (0.28, 0.72, 1.0, 0.9)     # Electric cyan-blue
        self.inactive_bar_color = (0.38, 0.42, 0.46, 0.45)  # Muted slate
        self.loop_shade_color = (0.20, 0.45, 0.85, 0.15)   # Transparent loop highlight
        self.handle_color = (1.0, 1.0, 1.0, 0.95)
        self.playhead_color = (1.0, 0.85, 0.25, 1.0)       # Amber playhead

    def _generate_procedural_peaks(self, count):
        peaks = []
        for i in range(count):
            t = i / float(count)
            # Mix of musical beat transients and decaying harmonic envelope
            beat = math.exp(-((t * 8.0) % 1.0) * 3.5)
            harmonic = 0.5 * math.sin(t * 18.0) + 0.3 * math.sin(t * 43.0)
            noise = (math.sin(t * 137.5) * 43758.5453) % 1.0
            val = 0.15 + (beat * 0.55) + (abs(harmonic) * 0.22) + (noise * 0.08)
            peaks.append(max(0.05, min(0.98, val)))
        return peaks

    def _get_canvas_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx = abs_x + 6.0 * scale
        cy = abs_y + 6.0 * scale
        cw = max(20.0, self.width - 12.0 * scale)
        ch = max(20.0, self.height - 24.0 * scale)
        return cx, cy, cw, ch

    def _time_to_x(self, t, cx, cw):
        ratio = max(0.0, min(1.0, t / max(0.001, self.duration)))
        return cx + ratio * cw

    def _x_to_time(self, x, cx, cw):
        ratio = max(0.0, min(1.0, (x - cx) / max(1.0, cw)))
        return ratio * self.duration

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)

        # 1. Header (Title + Time Readout)
        header_y = abs_y + self.height - 14.0 * scale
        if self.text:
            self.draw_text(self.text, abs_x + 4.0 * scale, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        cur_m, cur_s = divmod(self.playhead_time, 60.0)
        tot_m, tot_s = divmod(self.duration, 60.0)
        time_str = f"{int(cur_m)}:{cur_s:04.1f} / {int(tot_m)}:{tot_s:04.1f}"
        tw, _ = self.get_text_dimensions(time_str, font_id=0, size=9)
        self.draw_text(time_str, abs_x + self.width - tw - 6.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MAIN)

        # 2. Canvas Background
        GpuShapes.draw_smooth_rounded_box(
            cx, cy, cw, ch,
            radius=4.0 * scale,
            fill_color=self.canvas_bg,
            border_color=BlenderTheme.BORDER_LIGHT,
            border_width=1.0
        )

        mid_y = cy + ch * 0.5

        # Decibel guide lines (±6 dB = ~0.5 of half-height)
        half_ch = ch * 0.5 - 2.0 * scale
        GpuShapes.draw_smooth_line(cx + 2.0 * scale, mid_y + half_ch * 0.5, cx + cw - 2.0 * scale, mid_y + half_ch * 0.5, self.grid_color, line_width=1.0)
        GpuShapes.draw_smooth_line(cx + 2.0 * scale, mid_y - half_ch * 0.5, cx + cw - 2.0 * scale, mid_y - half_ch * 0.5, self.grid_color, line_width=1.0)

        # Centerline (0 dB zero-crossing)
        GpuShapes.draw_smooth_line(cx + 2.0 * scale, mid_y, cx + cw - 2.0 * scale, mid_y, self.centerline_color, line_width=1.0)

        # 3. Active Loop Region Shaded Interval
        in_x = self._time_to_x(self.loop_in, cx, cw)
        out_x = self._time_to_x(self.loop_out, cx, cw)
        if out_x > in_x:
            GpuShapes.draw_smooth_rounded_box(
                in_x, cy + 1.0 * scale, out_x - in_x, ch - 2.0 * scale,
                radius=0.0,
                fill_color=self.loop_shade_color
            )

        # 4. Mirrored Peak Envelope Bars
        num_bars = len(self.samples)
        if num_bars > 0:
            bar_spacing = cw / float(num_bars)
            for i, peak in enumerate(self.samples):
                bx = cx + (i + 0.5) * bar_spacing
                b_time = (i / float(num_bars)) * self.duration
                is_active = (self.loop_in <= b_time <= self.loop_out)
                bar_col = self.active_bar_color if is_active else self.inactive_bar_color

                h = peak * half_ch
                GpuShapes.draw_smooth_line(
                    bx, mid_y - h,
                    bx, mid_y + h,
                    bar_col,
                    line_width=max(1.5, bar_spacing * 0.65)
                )

        # 5. Loop Boundary Handles (In & Out Markers)
        handle_w = 2.0 * scale
        # In Marker
        GpuShapes.draw_smooth_line(in_x, cy, in_x, cy + ch, self.handle_color, line_width=handle_w)
        GpuShapes.draw_smooth_line(in_x, cy + ch - 1.0 * scale, in_x + 5.0 * scale, cy + ch - 1.0 * scale, self.handle_color, line_width=handle_w)
        GpuShapes.draw_smooth_line(in_x, cy + 1.0 * scale, in_x + 5.0 * scale, cy + 1.0 * scale, self.handle_color, line_width=handle_w)

        # Out Marker
        GpuShapes.draw_smooth_line(out_x, cy, out_x, cy + ch, self.handle_color, line_width=handle_w)
        GpuShapes.draw_smooth_line(out_x - 5.0 * scale, cy + ch - 1.0 * scale, out_x, cy + ch - 1.0 * scale, self.handle_color, line_width=handle_w)
        GpuShapes.draw_smooth_line(out_x - 5.0 * scale, cy + 1.0 * scale, out_x, cy + 1.0 * scale, self.handle_color, line_width=handle_w)

        # 6. Playhead Cursor Needle
        px = self._time_to_x(self.playhead_time, cx, cw)
        # Glow
        GpuShapes.draw_smooth_line(px, cy, px, cy + ch, (1.0, 0.85, 0.25, 0.35), line_width=4.0 * scale)
        # Sharp needle
        GpuShapes.draw_smooth_line(px, cy, px, cy + ch, self.playhead_color, line_width=1.5 * scale)
        # Pointer top disc
        GpuShapes.draw_smooth_circle(px, cy + ch, 3.5 * scale, self.playhead_color)
        GpuShapes.draw_smooth_ring(px, cy + ch, 3.5 * scale, (1.0, 1.0, 1.0, 0.9), thickness=1.0)

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        cx, cy, cw, ch = self._get_canvas_rect(origin_x, origin_y)
        pad = 5.0 * scale
        hit = (cx - pad <= mx <= cx + cw + pad) and (cy - pad <= my <= cy + ch + pad)

        in_x = self._time_to_x(self.loop_in, cx, cw)
        out_x = self._time_to_x(self.loop_out, cx, cw)
        handle_hit_dist = 6.0 * scale

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and hit:
                now = time.time()
                # Double click to reset loop range to full
                if now - self._last_click_time < 0.28:
                    self.loop_in = 0.0
                    self.loop_out = self.duration
                    self.playhead_time = 0.0
                    self._dragging_target = None
                    if self.on_loop_change:
                        self.on_loop_change(self.loop_in, self.loop_out)
                    if self.on_scrub:
                        self.on_scrub(self.playhead_time)
                    return True

                self._last_click_time = now

                # Check if clicked near Loop In handle
                if abs(mx - in_x) <= handle_hit_dist:
                    self._dragging_target = 'LOOP_IN'
                    return True

                # Check if clicked near Loop Out handle
                elif abs(mx - out_x) <= handle_hit_dist:
                    self._dragging_target = 'LOOP_OUT'
                    return True

                # Otherwise scrub playhead
                else:
                    self._dragging_target = 'PLAYHEAD'
                    self.playhead_time = self._x_to_time(mx, cx, cw)
                    if self.on_scrub:
                        self.on_scrub(self.playhead_time)
                    return True

            elif event.value == 'RELEASE' and self._dragging_target is not None:
                self._dragging_target = None
                return True

        elif event.type == 'MOUSEMOVE' and self._dragging_target is not None:
            t = self._x_to_time(mx, cx, cw)
            if self._dragging_target == 'PLAYHEAD':
                self.playhead_time = t
                if self.on_scrub:
                    self.on_scrub(self.playhead_time)
                return True

            elif self._dragging_target == 'LOOP_IN':
                self.loop_in = max(0.0, min(self.loop_out - 0.2, t))
                if self.on_loop_change:
                    self.on_loop_change(self.loop_in, self.loop_out)
                return True

            elif self._dragging_target == 'LOOP_OUT':
                self.loop_out = max(self.loop_in + 0.2, min(self.duration, t))
                if self.on_loop_change:
                    self.on_loop_change(self.loop_in, self.loop_out)
                return True

        return False
