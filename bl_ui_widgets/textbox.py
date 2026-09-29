import time
from .base import UIElement
from .theme import BlenderTheme

class UITextBox(UIElement):
    """
    Interactive single-line text input field styled like Blender's native string fields.
    """

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

        # Visual styling via BlenderTheme
        self.color_bg = BlenderTheme.BG_INSET
        self.color_border = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.color_border_focus = border_focus_color if border_focus_color is not None else BlenderTheme.BORDER_FOCUS
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.text_color = BlenderTheme.TEXT_MAIN
        self.placeholder_color = BlenderTheme.TEXT_MUTED
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS
        self.font_size = 11

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        inside = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)

        if event.type == 'MOUSEMOVE':
            if inside != self.hovered:
                self.hovered = inside
                return True
            return False

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                was_focused = self.is_focused
                self.is_focused = inside
                if was_focused != self.is_focused:
                    return True
                return inside

        return False

    def handle_keyboard_event(self, event) -> bool:
        if not self.is_focused or not self.visible or not self.enabled:
            return False

        if event.value != 'PRESS':
            return False

        # 1. Backspace: remove last character
        if event.type == 'BACK_SPACE':
            if len(self.text) > 0:
                self.text = self.text[:-1]
                return True
            return False

        # 2. Enter / Return: commit and lose focus
        elif event.type in {'RET', 'NUMPAD_ENTER'}:
            self.is_focused = False
            if self.on_commit:
                self.on_commit(self, self.text)
            return True

        # 3. Escape: cancel focus without commit
        elif event.type == 'ESC':
            self.is_focused = False
            return True

        # 4. Standard character typing via event.ascii
        elif event.ascii and event.ascii.isprintable():
            self.text += event.ascii
            return True

        return False

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        # 1. Rounded Inset Box
        self.draw_rounded_rect(abs_x, abs_y, self.width, self.height, self.corner_radius, self.color_bg)

        # 2. Rounded Border Outline (Focus highlight or native dark border)
        border_col = self.color_border_focus if self.is_focused else self.color_border
        border_w = (self.border_width + 0.5) if self.is_focused else self.border_width
        self.draw_rounded_rect_outline(abs_x, abs_y, self.width, self.height, self.corner_radius, border_col, line_width=border_w)

        scale = BlenderTheme.get_ui_scale()
        pad_x = 8.0 * scale
        available_w = max(10.0, self.width - (pad_x * 2.0))
        
        disp_text = self.text if self.text else (self.placeholder if not self.is_focused else "")
        text_col = self.text_color if self.text else self.placeholder_color

        tw, th = self.get_text_dimensions(disp_text, font_id=0, size=self.font_size)
        ty = abs_y + (self.height - th) / 2.0 + (1.0 * scale)

        if disp_text:
            self.draw_text(disp_text, abs_x + pad_x, ty, font_id=0, size=self.font_size, color=text_col, max_width=available_w)

        # 4. Blinking Cursor when focused
        if self.is_focused:
            if int(time.time() * 2) % 2 == 0:
                cursor_x = abs_x + pad_x + min(tw, available_w) + (2.0 * scale)
                cursor_h = self.height - (8.0 * scale)
                cursor_y = abs_y + (4.0 * scale)
                self.draw_rect(cursor_x, cursor_y, max(1.5, 1.5 * scale), cursor_h, BlenderTheme.TEXT_MAIN)
