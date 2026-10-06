from .base import UIElement
from .theme import BlenderTheme
from .shapes import GpuShapes

class UICheckbox(UIElement):
    """Interactive toggle checkbox element styled to match Blender's native checkboxes."""

    def __init__(
        self,
        text="Checkbox",
        default_value=False,
        x=0,
        y=0,
        width=150,
        height=22,
        corner_radius=None,
        border_width=None,
        border_color=None,
        border_hover_color=None,
        check_style="BOX",
        on_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.value = bool(default_value)
        self.check_style = check_style
        self.on_change = on_change

        # Styling
        self.box_size = 15
        self.color_box_bg = BlenderTheme.BG_INSET
        self.color_box_border = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.color_box_border_hover = border_hover_color if border_hover_color is not None else BlenderTheme.BORDER_LIGHT
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.color_check = BlenderTheme.PRIMARY_BLUE
        self.text_color = BlenderTheme.TEXT_MAIN
        self.corner_radius = corner_radius if corner_radius is not None else 3.0
        self.font_size = 11

    def on_click_event(self):
        if not self.enabled:
            return
        self.value = not self.value
        if self.on_change:
            self.on_change(self, self.value)

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        scale = BlenderTheme.get_ui_scale()
        box_size = self.box_size * scale
        box_y = abs_y + (self.height - box_size) / 2.0
        border_col = self.color_box_border_hover if self.hovered else self.color_box_border

        # 1. Outer Box (Anti-aliased custom SDF rounded box with crisp border in single pass)
        scaled_radius = self.corner_radius * scale
        scaled_border = max(1.0, self.border_width * scale)
        GpuShapes.draw_smooth_rounded_box(
            abs_x, box_y, box_size, box_size,
            radius=scaled_radius,
            fill_color=self.color_box_bg,
            border_color=border_col,
            border_width=scaled_border
        )

        # 2. Check Indicator (Anti-aliased custom SDF fill or vector check)
        if self.value:
            margin = 2.5 * scale
            check_size = box_size - (margin * 2.0)
            if self.check_style == "CHECK":
                p1 = (abs_x + margin + check_size * 0.18, box_y + margin + check_size * 0.45)
                p2 = (abs_x + margin + check_size * 0.42, box_y + margin + check_size * 0.20)
                p3 = (abs_x + margin + check_size * 0.82, box_y + margin + check_size * 0.75)
                GpuShapes.draw_smooth_polyline([p1, p2, p3], self.color_check, line_width=2.0 * scale)
            else:
                check_radius = max(1.0, 2.0 * scale)
                GpuShapes.draw_smooth_rounded_box(
                    abs_x + margin, box_y + margin, check_size, check_size,
                    radius=check_radius,
                    fill_color=self.color_check
                )

        # 3. Label text beside the box
        label_x = abs_x + box_size + (8.0 * scale)
        tw, th = self.get_text_dimensions(self.text, font_id=0, size=self.font_size)
        label_y = abs_y + (self.height - th) / 2.0 + (1.0 * scale)
        max_label_w = max(10.0, self.width - (box_size + 12.0 * scale))
        self.draw_text(self.text, label_x, label_y, font_id=0, size=self.font_size, color=self.text_color, max_width=max_label_w)
