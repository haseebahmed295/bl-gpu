import time
import bpy
import gpu
from .base import UIElement
from .theme import BlenderTheme

class UITextBox(UIElement):
    """
    Interactive single-line text input field styled like Blender's native string fields.
    Supports full mouse drag text selection, double-click word selection, Shift+Arrow navigation,
    Ctrl+A (select all), Ctrl+C/V/X (clipboard), Ctrl+Z (undo), cursor navigation, and backspace/delete.
    """
    _clipboard = ""

    def __init__(
        self,
        placeholder="Enter text...",
        default_text="",
        x=0,
        y=0,
        width=180,
        height=24,
        corner_radius=None,
        border_width=None,
        border_color=None,
        border_focus_color=None,
        on_commit=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.placeholder = placeholder
        self.text = str(default_text)
        self.on_commit = on_commit

        self.cursor_pos = len(self.text)
        self.selection_start = -1
        self.selection_end = -1
        self.is_focused = False
        self.is_dragging = False
        self.scroll_offset_x = 0.0

        self._last_click_time = 0.0
        self._last_click_x = 0.0
        self._undo_stack = []

        # Visual styling via BlenderTheme
        self.color_bg = BlenderTheme.BG_INSET
        self.color_border = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.color_border_focus = border_focus_color if border_focus_color is not None else BlenderTheme.BORDER_FOCUS
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.text_color = BlenderTheme.TEXT_MAIN
        self.placeholder_color = BlenderTheme.TEXT_MUTED
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS
        self.font_size = 11

    def _record_undo(self):
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._undo_stack.append((self.text, self.cursor_pos))

    def _get_selection_bounds(self):
        if self.selection_start >= 0 and self.selection_end >= 0 and self.selection_start != self.selection_end:
            return min(self.selection_start, self.selection_end), max(self.selection_start, self.selection_end)
        return None, None

    def _delete_selection(self):
        sel_min, sel_max = self._get_selection_bounds()
        if sel_min is not None:
            self._record_undo()
            self.text = self.text[:sel_min] + self.text[sel_max:]
            self.cursor_pos = sel_min
            self.selection_start = self.selection_end = -1
            return True
        return False

    def _insert_text(self, new_chars):
        self._record_undo()
        sel_min, sel_max = self._get_selection_bounds()
        if sel_min is not None:
            self.text = self.text[:sel_min] + str(new_chars) + self.text[sel_max:]
            self.cursor_pos = sel_min + len(str(new_chars))
        else:
            self.cursor_pos = max(0, min(len(self.text), self.cursor_pos))
            self.text = self.text[:self.cursor_pos] + str(new_chars) + self.text[self.cursor_pos:]
            self.cursor_pos += len(str(new_chars))
        self.selection_start = self.selection_end = -1

    def _find_word_boundary_left(self, pos):
        if pos <= 0:
            return 0
        i = pos - 1
        while i > 0 and self.text[i] in ' _-./\\':
            i -= 1
        while i > 0 and self.text[i - 1] not in ' _-./\\':
            i -= 1
        return i

    def _find_word_boundary_right(self, pos):
        n = len(self.text)
        if pos >= n:
            return n
        i = pos
        while i < n and self.text[i] not in ' _-./\\':
            i += 1
        while i < n and self.text[i] in ' _-./\\':
            i += 1
        return i

    def _get_char_index_at(self, mouse_x, origin_x):
        scale = BlenderTheme.get_ui_scale()
        pad_x = 8.0 * scale
        text_x = origin_x + self.x + pad_x - self.scroll_offset_x
        local_x = mouse_x - text_x

        if local_x <= 0 or not self.text:
            return 0

        prev_w = 0.0
        for i in range(len(self.text)):
            curr_w, _ = self.get_text_dimensions(self.text[:i + 1], font_id=0, size=self.font_size)
            mid = (prev_w + curr_w) / 2.0
            if local_x < mid:
                return i
            prev_w = curr_w

        return len(self.text)

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        inside = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)

        if event.type == 'MOUSEMOVE':
            if self.is_dragging:
                idx = self._get_char_index_at(mouse_x, origin_x)
                if idx != self.cursor_pos:
                    self.cursor_pos = idx
                    self.selection_end = idx
                    return True
                return False
            if inside != self.hovered:
                self.hovered = inside
                return True
            return False

        elif event.type == 'LEFTMOUSE':
            if event.value in {'PRESS', 'DOUBLE_CLICK', 'CLICK'}:
                if inside:
                    now = time.time()
                    is_double = (event.value == 'DOUBLE_CLICK') or (
                        (now - self._last_click_time < 0.35) and abs(mouse_x - self._last_click_x) < 6
                    )
                    self._last_click_time = now
                    self._last_click_x = mouse_x

                    self.is_focused = True
                    idx = self._get_char_index_at(mouse_x, origin_x)

                    if is_double:
                        # Double click selects word, or select all if small / single token
                        w_left = self._find_word_boundary_left(idx + 1 if idx < len(self.text) else idx)
                        w_right = self._find_word_boundary_right(idx)
                        if (w_left == 0 and w_right == len(self.text)) or (w_right - w_left <= 0):
                            self.selection_start = 0
                            self.selection_end = len(self.text)
                            self.cursor_pos = len(self.text)
                        else:
                            self.selection_start = w_left
                            self.selection_end = w_right
                            self.cursor_pos = w_right
                        self.is_dragging = False
                    else:
                        self.cursor_pos = idx
                        self.selection_start = idx
                        self.selection_end = idx
                        self.is_dragging = True
                    return True
                else:
                    if self.is_focused:
                        self.is_focused = False
                        self.is_dragging = False
                        self.selection_start = self.selection_end = -1
                        if self.on_commit:
                            self.on_commit(self, self.text)
                        return False
                    return False

            elif event.value == 'RELEASE':
                if self.is_dragging:
                    self.is_dragging = False
                    if self.selection_start == self.selection_end:
                        self.selection_start = self.selection_end = -1
                    return True

        return False

    def handle_keyboard_event(self, event) -> bool:
        if not self.is_focused or not self.visible or not self.enabled:
            return False

        is_press = event.value in {'PRESS', 'REPEAT', 'NOTHING'}
        if not is_press:
            return False

        is_ctrl = getattr(event, 'ctrl', False)
        is_shift = getattr(event, 'shift', False)
        is_alt = getattr(event, 'alt', False)
        ev_type = event.type

        # 1. Enter / Return: commit and lose focus
        if ev_type in {'RET', 'NUMPAD_ENTER'}:
            self.is_focused = False
            self.selection_start = self.selection_end = -1
            if self.on_commit:
                self.on_commit(self, self.text)
            return True

        # 2. Escape: cancel focus without commit
        elif ev_type == 'ESC':
            self.is_focused = False
            self.selection_start = self.selection_end = -1
            return True

        # 3. Ctrl + A: Select All
        elif is_ctrl and ev_type == 'A':
            self.selection_start = 0
            self.selection_end = len(self.text)
            self.cursor_pos = len(self.text)
            return True

        # 4. Ctrl + C: Copy
        elif is_ctrl and ev_type == 'C':
            sel_min, sel_max = self._get_selection_bounds()
            if sel_min is not None:
                UITextBox._clipboard = self.text[sel_min:sel_max]
                try:
                    bpy.context.window_manager.clipboard = UITextBox._clipboard
                except Exception:
                    pass
            return True

        # 5. Ctrl + X: Cut
        elif is_ctrl and ev_type == 'X':
            sel_min, sel_max = self._get_selection_bounds()
            if sel_min is not None:
                UITextBox._clipboard = self.text[sel_min:sel_max]
                try:
                    bpy.context.window_manager.clipboard = UITextBox._clipboard
                except Exception:
                    pass
                self._delete_selection()
            return True

        # 6. Ctrl + V: Paste
        elif is_ctrl and ev_type == 'V':
            clip = ""
            try:
                clip = bpy.context.window_manager.clipboard
            except Exception:
                clip = ""
            if not clip:
                clip = UITextBox._clipboard
            if clip:
                clean_clip = clip.replace("\r", "").replace("\n", " ")
                self._insert_text(clean_clip)
            return True

        # 7. Ctrl + Z: Undo
        elif is_ctrl and ev_type == 'Z':
            if self._undo_stack:
                prev_text, prev_cur = self._undo_stack.pop()
                self.text = prev_text
                self.cursor_pos = min(len(self.text), prev_cur)
                self.selection_start = self.selection_end = -1
            return True

        # 8. Backspace
        elif ev_type == 'BACK_SPACE':
            sel_min, sel_max = self._get_selection_bounds()
            if sel_min is not None:
                self._delete_selection()
            elif self.cursor_pos > 0:
                self._record_undo()
                if is_ctrl:
                    new_pos = self._find_word_boundary_left(self.cursor_pos)
                    self.text = self.text[:new_pos] + self.text[self.cursor_pos:]
                    self.cursor_pos = new_pos
                else:
                    self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            return True

        # 9. Delete
        elif ev_type in {'DEL', 'DELETE'}:
            sel_min, sel_max = self._get_selection_bounds()
            if sel_min is not None:
                self._delete_selection()
            elif self.cursor_pos < len(self.text):
                self._record_undo()
                if is_ctrl:
                    new_pos = self._find_word_boundary_right(self.cursor_pos)
                    self.text = self.text[:self.cursor_pos] + self.text[new_pos:]
                else:
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
            return True

        # 10. Left Arrow
        elif ev_type == 'LEFT_ARROW':
            if is_shift:
                if self.selection_start < 0:
                    self.selection_start = self.cursor_pos
                new_pos = max(0, self.cursor_pos - 1) if not is_ctrl else self._find_word_boundary_left(self.cursor_pos)
                self.cursor_pos = new_pos
                self.selection_end = self.cursor_pos
            else:
                sel_min, sel_max = self._get_selection_bounds()
                if sel_min is not None:
                    self.cursor_pos = sel_min
                    self.selection_start = self.selection_end = -1
                else:
                    self.cursor_pos = max(0, self.cursor_pos - 1) if not is_ctrl else self._find_word_boundary_left(self.cursor_pos)
            return True

        # 11. Right Arrow
        elif ev_type == 'RIGHT_ARROW':
            if is_shift:
                if self.selection_start < 0:
                    self.selection_start = self.cursor_pos
                new_pos = min(len(self.text), self.cursor_pos + 1) if not is_ctrl else self._find_word_boundary_right(self.cursor_pos)
                self.cursor_pos = new_pos
                self.selection_end = self.cursor_pos
            else:
                sel_min, sel_max = self._get_selection_bounds()
                if sel_min is not None:
                    self.cursor_pos = sel_max
                    self.selection_start = self.selection_end = -1
                else:
                    self.cursor_pos = min(len(self.text), self.cursor_pos + 1) if not is_ctrl else self._find_word_boundary_right(self.cursor_pos)
            return True

        # 12. Home
        elif ev_type == 'HOME':
            if is_shift:
                if self.selection_start < 0:
                    self.selection_start = self.cursor_pos
                self.cursor_pos = 0
                self.selection_end = 0
            else:
                self.cursor_pos = 0
                self.selection_start = self.selection_end = -1
            return True

        # 13. End
        elif ev_type == 'END':
            if is_shift:
                if self.selection_start < 0:
                    self.selection_start = self.cursor_pos
                self.cursor_pos = len(self.text)
                self.selection_end = len(self.text)
            else:
                self.cursor_pos = len(self.text)
                self.selection_start = self.selection_end = -1
            return True

        # 14. Character typing
        char = None
        unicode_val = getattr(event, 'unicode', '')
        ascii_val = getattr(event, 'ascii', '')

        if unicode_val and unicode_val.isprintable() and not is_ctrl and not is_alt:
            char = unicode_val
        elif ascii_val and ascii_val.isprintable() and not is_ctrl and not is_alt:
            char = ascii_val
        elif not is_ctrl and not is_alt:
            if ev_type == 'SPACE':
                char = ' '
            elif len(ev_type) == 1 and ev_type.isalnum():
                char = ev_type if is_shift else ev_type.lower()

        if char:
            self._insert_text(char)
            return True

        # Consume any other keyboard input while focused to prevent leaking shortcuts to 3D Viewport
        return True

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y
        scale = BlenderTheme.get_ui_scale()

        # 1. Rounded Inset Box
        self.draw_rounded_rect(abs_x, abs_y, self.width, self.height, self.corner_radius, self.color_bg)

        # 2. Outline Border (Focus highlight or native dark border)
        border_col = self.color_border_focus if self.is_focused else self.color_border
        border_w = (self.border_width + 0.5) if self.is_focused else self.border_width
        self.draw_rounded_rect_outline(abs_x, abs_y, self.width, self.height, self.corner_radius, border_col, line_width=border_w)

        pad_x = 8.0 * scale
        available_w = max(10.0, self.width - (pad_x * 2.0))

        # Clamp cursor
        self.cursor_pos = max(0, min(len(self.text), self.cursor_pos))

        # Update horizontal scroll offset to keep cursor visible within available width
        cur_offset, _ = self.get_text_dimensions(self.text[:self.cursor_pos], font_id=0, size=self.font_size)
        if self.is_focused:
            if cur_offset - self.scroll_offset_x > available_w - (4.0 * scale):
                self.scroll_offset_x = cur_offset - (available_w - (4.0 * scale))
            elif cur_offset - self.scroll_offset_x < 0:
                self.scroll_offset_x = cur_offset
        else:
            self.scroll_offset_x = 0.0

        disp_text = self.text if self.text else (self.placeholder if not self.is_focused else "")
        text_col = self.text_color if self.text else self.placeholder_color

        tw, th = self.get_text_dimensions(disp_text, font_id=0, size=self.font_size)
        ty = abs_y + (self.height - th) / 2.0 + (1.0 * scale)

        # Scissor clip to input inner bounds so scrolled text/selection never exceeds the box
        orig_scissor = gpu.state.scissor_get()
        inner_x = int(abs_x + pad_x)
        inner_y = int(abs_y + 2.0 * scale)
        inner_w = int(max(0.0, available_w))
        inner_h = int(max(0.0, self.height - 4.0 * scale))

        clip_x0 = max(int(orig_scissor[0]), inner_x)
        clip_y0 = max(int(orig_scissor[1]), inner_y)
        clip_x1 = min(int(orig_scissor[0] + orig_scissor[2]), inner_x + inner_w)
        clip_y1 = min(int(orig_scissor[1] + orig_scissor[3]), inner_y + inner_h)

        if clip_x1 > clip_x0 and clip_y1 > clip_y0:
            gpu.state.scissor_set(clip_x0, clip_y0, clip_x1 - clip_x0, clip_y1 - clip_y0)

            # 3. Draw Selection Highlight Box (behind text)
            if self.is_focused and self.text:
                sel_min, sel_max = self._get_selection_bounds()
                if sel_min is not None:
                    w_start, _ = self.get_text_dimensions(self.text[:sel_min], font_id=0, size=self.font_size)
                    w_end, _ = self.get_text_dimensions(self.text[:sel_max], font_id=0, size=self.font_size)
                    sel_x = abs_x + pad_x - self.scroll_offset_x + w_start
                    sel_w = max(2.0, w_end - w_start)
                    sel_y = abs_y + (3.0 * scale)
                    sel_h = self.height - (6.0 * scale)
                    self.draw_rounded_rect(sel_x, sel_y, sel_w, sel_h, 2.0, BlenderTheme.PRIMARY_BLUE)

            # 4. Draw Text
            if disp_text:
                self.draw_text(
                    disp_text,
                    abs_x + pad_x - self.scroll_offset_x,
                    ty,
                    font_id=0,
                    size=self.font_size,
                    color=text_col
                )

            # 5. Draw Blinking Cursor
            if self.is_focused:
                sel_min, _ = self._get_selection_bounds()
                if sel_min is None or (int(time.time() * 2) % 2 == 0):
                    cursor_x = abs_x + pad_x - self.scroll_offset_x + cur_offset
                    cursor_h = self.height - (8.0 * scale)
                    cursor_y = abs_y + (4.0 * scale)
                    self.draw_rect(cursor_x, cursor_y, max(1.5, 1.5 * scale), cursor_h, BlenderTheme.TEXT_MAIN)

            # Restore original panel scissor
            gpu.state.scissor_set(int(orig_scissor[0]), int(orig_scissor[1]), int(orig_scissor[2]), int(orig_scissor[3]))

