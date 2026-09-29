from .base import UIElement
from .theme import BlenderTheme

class UIButton(UIElement):
    """Interactive button styled to match Blender's native UI."""

    def __init__(
        self,
        text="Button",
        x=0,
        y=0,
        width=120,
        height=26,
        corner_radius=None,
        border_width=None,
        border_color=None,
        on_click=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.on_click = on_click
        
        # Color Styling via BlenderTheme
        self.color_normal = BlenderTheme.BG_BUTTON
        self.color_hover = BlenderTheme.BG_BUTTON_HOVER
        self.color_pressed = BlenderTheme.BG_BUTTON_ACTIVE
        self.color_disabled = (0.16, 0.16, 0.16, 0.5)
        
        self.text_color = BlenderTheme.TEXT_MAIN
        self.text_color_disabled = BlenderTheme.TEXT_MUTED
        self.border_color = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS
        self.font_size = 11

    def on_click_event(self):
        if self.on_click and self.enabled:
            self.on_click(self)

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        # Determine background color based on interaction state
        if not self.enabled:
            bg_color = self.color_disabled
            txt_color = self.text_color_disabled
        elif self.pressed:
            bg_color = self.color_pressed
            txt_color = self.text_color
        elif self.hovered:
            bg_color = self.color_hover
            txt_color = self.text_color
        else:
            bg_color = self.color_normal
            txt_color = self.text_color

        # 1. Draw Rounded Button Box
        self.draw_rounded_rect(abs_x, abs_y, self.width, self.height, self.corner_radius, bg_color)

        # 2. Draw Subtle Rounded Border
        self.draw_rounded_rect_outline(abs_x, abs_y, self.width, self.height, self.corner_radius, self.border_color, line_width=self.border_width)

        # 3. Calculate Centered Text Position
        available_txt_w = max(10, self.width - 10)
        tw, th = self.get_text_dimensions(self.text, font_id=0, size=self.font_size)
        tx = abs_x + max(5.0, (self.width - tw) / 2.0)
        ty = abs_y + (self.height - th) / 2.0 + 1.0

        # 4. Draw Label
        self.draw_text(self.text, tx, ty, font_id=0, size=self.font_size, color=txt_color, max_width=available_txt_w)
