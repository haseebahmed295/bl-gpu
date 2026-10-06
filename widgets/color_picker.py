from .base import UIElement
from .theme import BlenderTheme

class UIColorPicker(UIElement):
    """Color display and swatch element styled to match Blender's native color buttons."""

    PRESET_PALETTE = [
        (0.85, 0.25, 0.25, 1.0), # Red
        (0.25, 0.80, 0.35, 1.0), # Green
        (0.278, 0.447, 0.702, 1.0), # Blender Blue
        (0.95, 0.75, 0.20, 1.0), # Yellow/Gold
        (0.70, 0.35, 0.90, 1.0), # Purple
        (0.90, 0.90, 0.90, 1.0), # White
    ]

    def __init__(
        self,
        text="Color",
        default_color=(0.278, 0.447, 0.702, 1.0),
        x=0,
        y=0,
        width=180,
        height=24,
        corner_radius=None,
        border_width=None,
        border_color=None,
        border_hover_color=None,
        on_color_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.color = tuple(default_color)
        self.on_color_change = on_color_change
        
        self.font_size = 11
        self.swatch_width = 38
        self.border_color = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.border_color_hover = border_hover_color if border_hover_color is not None else BlenderTheme.BORDER_LIGHT
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS
        self._palette_idx = 2

    def on_click_event(self):
        if not self.enabled:
            return
            
        self._palette_idx = (self._palette_idx + 1) % len(self.PRESET_PALETTE)
        self.color = self.PRESET_PALETTE[self._palette_idx]
        
        if self.on_color_change:
            self.on_color_change(self, self.color)

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        scale = BlenderTheme.get_ui_scale()
        swatch_width = self.swatch_width * scale

        # 1. Label on the left
        tw, th = self.get_text_dimensions(self.text, font_id=0, size=self.font_size)
        ty = abs_y + (self.height - th) / 2.0 + (1.0 * scale)
        max_label_w = max(10.0, self.width - swatch_width - (10.0 * scale))
        self.draw_text(self.text, abs_x, ty, font_id=0, size=self.font_size, color=BlenderTheme.TEXT_MAIN, max_width=max_label_w)

        # 2. Rounded Color Swatch on the right
        swatch_x = abs_x + self.width - swatch_width
        swatch_y = abs_y + (1.0 * scale)
        swatch_h = self.height - (2.0 * scale)
        
        border_col = self.border_color_hover if self.hovered else self.border_color
        self.draw_rounded_rect(swatch_x, swatch_y, swatch_width, swatch_h, self.corner_radius, self.color)
        self.draw_rounded_rect_outline(swatch_x, swatch_y, swatch_width, swatch_h, self.corner_radius, border_col, line_width=self.border_width)
