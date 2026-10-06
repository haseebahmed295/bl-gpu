from .base import UIElement

class UILabel(UIElement):
    """Text label element for headers and descriptions."""

    def __init__(self, text="Label", x=0, y=0, width=150, height=20, font_size=12, color=(0.85, 0.85, 0.85, 1.0), align='LEFT'):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.font_size = font_size
        self.color = color
        self.align = align.upper() # 'LEFT', 'CENTER', 'RIGHT'

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        tw, th = self.get_text_dimensions(self.text, font_id=0, size=self.font_size)

        if self.align == 'CENTER':
            tx = abs_x + (self.width - tw) / 2.0
        elif self.align == 'RIGHT':
            tx = abs_x + self.width - tw
        else: # LEFT
            tx = abs_x

        ty = abs_y + (self.height - th) / 2.0 + 1.0

        self.draw_text(self.text, tx, ty, font_id=0, size=self.font_size, color=self.color, max_width=self.width)
