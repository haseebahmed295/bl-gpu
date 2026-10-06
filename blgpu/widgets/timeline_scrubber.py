import gpu
import math
import time
from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UITimelineScrubber(UIElement):
    """
    Interactive Animation Timeline & Keyframe Mini-Scrubber widget.
    Embeds a playable, scrubbable animation ruler directly inside the N-panel (impossible in standard Blender UI).
    Features:
    - Time ruler with frame graduation tick marks and frame number labels.
    - Active playback range highlight between start_frame and end_frame.
    - Clickable gold keyframe diamond markers that snap the playhead directly to keys.
    - High-visibility playhead cursor needle with pointer flag.
    - Shift modifier for fine sub-frame scrubbing, double-click to snap to start frame.
    - Real-time on_frame_change callback.
    """

    def __init__(
        self,
        text="Timeline",
        start_frame=1,
        end_frame=120,
        current_frame=24,
        keyframes=None,
        x=0,
        y=0,
        width=150,
        height=68,
        on_frame_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.start_frame = int(start_frame)
        self.end_frame = int(end_frame)
        self.current_frame = float(current_frame)
        self.keyframes = sorted(list(keyframes if keyframes is not None else [1, 24, 48, 72, 96, 120]))
        self.on_frame_change = on_frame_change

        self.is_dragging = False
        self.is_hovered = False
        self._last_click_time = 0.0

        # Colors
        self.track_bg = (0.16, 0.16, 0.16, 0.95)
        self.range_bg = (0.22, 0.24, 0.28, 0.9)
        self.tick_color = (0.40, 0.40, 0.40, 0.8)
        self.subtick_color = (0.28, 0.28, 0.28, 0.6)
        self.key_color = (0.95, 0.75, 0.20, 1.0)        # Blender gold keyframe
        self.key_hover = (1.0, 0.90, 0.40, 1.0)
        self.playhead_color = BlenderTheme.PRIMARY_BLUE  # Blender blue playhead
        self.playhead_glow = (0.35, 0.70, 1.0, 0.4)

    def _get_track_rect(self, origin_x, origin_y):
        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        tx = abs_x + 6.0 * scale
        ty = abs_y + 6.0 * scale
        tw = max(10.0, self.width - 12.0 * scale)
        th = 38.0 * scale
        return tx, ty, tw, th

    def _frame_to_x(self, frame, tx, tw):
        span = max(1, self.end_frame - self.start_frame)
        ratio = (frame - self.start_frame) / span
        return tx + ratio * tw

    def _x_to_frame(self, x, tx, tw):
        ratio = max(0.0, min(1.0, (x - tx) / max(1.0, tw)))
        span = self.end_frame - self.start_frame
        return self.start_frame + ratio * span

    def draw(self, origin_x=0, origin_y=0):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        tx, ty, tw, th = self._get_track_rect(origin_x, origin_y)

        # 1. Header (Title + Current Frame readout badge)
        header_y = abs_y + self.height - 14.0 * scale
        if self.text:
            self.draw_text(self.text, abs_x + 4.0 * scale, header_y, font_id=0, size=10, color=BlenderTheme.TEXT_MUTED)

        # Frame badge string
        cur_int = int(round(self.current_frame))
        badge_str = f"Frame: {cur_int} / {self.end_frame}"
        bw, _ = self.get_text_dimensions(badge_str, font_id=0, size=9)
        self.draw_text(badge_str, abs_x + self.width - bw - 6.0 * scale, header_y, font_id=0, size=9, color=BlenderTheme.TEXT_MAIN)

        # 2. Timeline Track Background
        GpuShapes.draw_smooth_rounded_box(
            tx, ty, tw, th,
            radius=4.0 * scale,
            fill_color=self.track_bg,
            border_color=BlenderTheme.BORDER_LIGHT,
            border_width=1.0
        )

        # Active Playback Range Sub-fill
        GpuShapes.draw_smooth_rounded_box(
            tx + 1.0 * scale, ty + 1.0 * scale, tw - 2.0 * scale, th - 2.0 * scale,
            radius=3.0 * scale,
            fill_color=self.range_bg
        )

        # 3. Ruler Tick Marks & Frame Number Labels
        # Determine tick step based on width and frame span
        span = max(1, self.end_frame - self.start_frame)
        target_ticks = max(3, int(tw / (32.0 * scale)))
        rough_step = span / target_ticks
        # Pick standard step (5, 10, 20, 25, 50, 100)
        candidates = [5, 10, 20, 25, 50, 100]
        step = candidates[0]
        for c in candidates:
            if c >= rough_step:
                step = c
                break

        ruler_bottom = ty + 14.0 * scale
        ruler_top = ty + th

        # Major & Minor Ticks
        sub_step = max(1, step // 5) if step >= 5 else 1
        first_minor = (self.start_frame // sub_step) * sub_step
        last_minor = ((self.end_frame + sub_step) // sub_step) * sub_step

        for f in range(first_minor, last_minor + 1, sub_step):
            if f < self.start_frame or f > self.end_frame:
                continue
            fx = self._frame_to_x(f, tx, tw)
            is_major = (f % step == 0)
            t_height = 8.0 * scale if is_major else 4.0 * scale
            col = self.tick_color if is_major else self.subtick_color

            GpuShapes.draw_smooth_line(
                fx, ruler_top - t_height,
                fx, ruler_top - 1.0 * scale,
                col,
                line_width=1.0
            )

            # Major frame numbers
            if is_major and (fx - tx > 12.0 * scale) and (tx + tw - fx > 12.0 * scale):
                lbl = str(f)
                lw, _ = self.get_text_dimensions(lbl, font_id=0, size=8)
                self.draw_text(lbl, fx - lw * 0.5, ruler_top - 18.0 * scale, font_id=0, size=8, color=BlenderTheme.TEXT_MUTED)

        # In & Out Boundary Bracket Lines
        GpuShapes.draw_smooth_line(tx, ty, tx, ty + th, (0.7, 0.7, 0.7, 0.8), line_width=2.0 * scale)
        GpuShapes.draw_smooth_line(tx + tw, ty, tx + tw, ty + th, (0.7, 0.7, 0.7, 0.8), line_width=2.0 * scale)

        # 4. Keyframe Markers (Gold Diamonds on bottom half of track)
        key_y = ty + 7.0 * scale
        key_r = 3.5 * scale
        for kf in self.keyframes:
            if self.start_frame <= kf <= self.end_frame:
                kx = self._frame_to_x(kf, tx, tw)
                # Outer diamond glow / border
                GpuShapes.draw_smooth_circle(kx, key_y, key_r + 1.0 * scale, (0.1, 0.1, 0.1, 0.8))
                # Inner gold key pip
                GpuShapes.draw_smooth_circle(kx, key_y, key_r, self.key_color)
                GpuShapes.draw_smooth_ring(kx, key_y, key_r, (1.0, 1.0, 1.0, 0.9), thickness=1.0)

        # 5. Playhead Needle (Cursor + Cap Flag)
        px = self._frame_to_x(self.current_frame, tx, tw)

        # Needle vertical glow halo
        GpuShapes.draw_smooth_line(
            px, ty,
            px, ty + th + 4.0 * scale,
            self.playhead_glow,
            line_width=4.0 * scale
        )
        # Needle vertical line
        GpuShapes.draw_smooth_line(
            px, ty,
            px, ty + th + 4.0 * scale,
            self.playhead_color,
            line_width=1.5 * scale
        )

        # Playhead top triangle / cap flag
        cap_w = 4.5 * scale
        cap_h = 6.0 * scale
        cap_top = ty + th + 4.0 * scale
        GpuShapes.draw_smooth_circle(px, cap_top, cap_w, self.playhead_color)
        GpuShapes.draw_smooth_ring(px, cap_top, cap_w, (1.0, 1.0, 1.0, 0.9), thickness=1.0)

    def handle_event(self, event, mouse_x=None, mouse_y=None, origin_x=0, origin_y=0, *args, **kwargs) -> bool:
        if not self.visible or not self.enabled:
            return False

        scale = BlenderTheme.get_ui_scale()
        mx = mouse_x if mouse_x is not None else getattr(event, 'mouse_region_x', 0)
        my = mouse_y if mouse_y is not None else getattr(event, 'mouse_region_y', 0)

        tx, ty, tw, th = self._get_track_rect(origin_x, origin_y)
        pad = 4.0 * scale
        hit = (tx - pad <= mx <= tx + tw + pad) and (ty - pad <= my <= ty + th + 8.0 * scale)

        self.is_hovered = hit or self.is_dragging

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and hit:
                now = time.time()
                # Double click to reset to start frame
                if now - self._last_click_time < 0.28:
                    self.current_frame = float(self.start_frame)
                    self.is_dragging = False
                    self._trigger_change()
                    return True

                self._last_click_time = now

                # Check if clicked near an existing keyframe to snap to it
                key_y = ty + 7.0 * scale
                snap_radius = 6.0 * scale
                for kf in self.keyframes:
                    kx = self._frame_to_x(kf, tx, tw)
                    if abs(mx - kx) <= snap_radius and abs(my - key_y) <= snap_radius + 4.0 * scale:
                        self.current_frame = float(kf)
                        self.is_dragging = True
                        self._trigger_change()
                        return True

                self.is_dragging = True
                self._update_frame(mx, tx, tw, event)
                return True

            elif event.value == 'RELEASE' and self.is_dragging:
                self.is_dragging = False
                return True

        elif event.type == 'MOUSEMOVE' and self.is_dragging:
            self._update_frame(mx, tx, tw, event)
            return True

        return False

    def _update_frame(self, mx, tx, tw, event):
        raw_frame = self._x_to_frame(mx, tx, tw)
        # Shift: fine sub-frame scrub with 0.1 precision
        if event.shift:
            new_frame = round(raw_frame, 1)
        else:
            new_frame = float(round(raw_frame))

        new_frame = max(float(self.start_frame), min(float(self.end_frame), new_frame))
        if new_frame != self.current_frame:
            self.current_frame = new_frame
            self._trigger_change()

    def _trigger_change(self):
        if self.on_frame_change:
            self.on_frame_change(self.current_frame)
