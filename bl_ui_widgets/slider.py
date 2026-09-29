from .base import UIElement
from .theme import BlenderTheme

class UISlider(UIElement):
    """Interactive horizontal slider widget styled like Blender's native numeric sliders."""

    def __init__(
        self,
        text="Value",
        min_value=0.0,
        max_value=1.0,
        default_value=0.5,
        step=0.01,
        precision=2,
        x=0,
        y=0,
        width=180,
        height=24,
        corner_radius=None,
        border_width=None,
        border_color=None,
        on_change=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.text = text
        self.min_value = float(min_value)
        self.max_value = float(max_value)
        self.step = float(step)
        self.precision = precision
        self.on_change = on_change
        
        # Clamp initial value
        self._value = max(self.min_value, min(self.max_value, float(default_value)))
        
        # Native Theme Styling
        self.color_bg = BlenderTheme.BG_INSET
        self.color_fill = BlenderTheme.PRIMARY_BLUE
        self.color_fill_hover = BlenderTheme.PRIMARY_BLUE_HOVER
        self.color_fill_drag = BlenderTheme.PRIMARY_BLUE_ACTIVE
        self.border_color = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.text_color = BlenderTheme.TEXT_MAIN
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS
        self.font_size = 11

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_val):
        clamped = max(self.min_value, min(self.max_value, float(new_val)))
        if self.step > 0:
            clamped = round(clamped / self.step) * self.step
        clamped = round(clamped, self.precision)
        
        if clamped != self._value:
            self._value = clamped
            if self.on_change:
                self.on_change(self, self._value)

    def _value_from_mouse_x(self, mouse_x, abs_x):
        ratio = (mouse_x - abs_x) / max(1.0, float(self.width))
        ratio = max(0.0, min(1.0, ratio))
        return self.min_value + ratio * (self.max_value - self.min_value)

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        abs_x = origin_x + self.x
        inside = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)

        if self.is_dragging:
            if event.type == 'MOUSEMOVE':
                self.value = self._value_from_mouse_x(mouse_x, abs_x)
                return True
            elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self.is_dragging = False
                self.pressed = False
                return True
            return False

        if event.type == 'MOUSEMOVE':
            if inside != self.hovered:
                self.hovered = inside
                return True
            return False

        elif event.type == 'LEFTMOUSE':
            if event.value == 'PRESS' and inside:
                self.pressed = True
                self.is_dragging = True
                self.value = self._value_from_mouse_x(mouse_x, abs_x)
                return True
            elif event.value == 'RELEASE':
                if self.pressed:
                    self.pressed = False
                    self.is_dragging = False
                    return True

        return False

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        # Compute fill width
        range_span = max(1e-5, self.max_value - self.min_value)
        ratio = (self._value - self.min_value) / range_span
        ratio = max(0.0, min(1.0, ratio))
        fill_width = self.width * ratio

        # Choose fill color
        if self.is_dragging:
            fill_col = self.color_fill_drag
        elif self.hovered:
            fill_col = self.color_fill_hover
        else:
            fill_col = self.color_fill

        # 1. Background Track (Rounded)
        self.draw_rounded_rect(abs_x, abs_y, self.width, self.height, self.corner_radius, self.color_bg)

        # 2. Filled progress bar
        if fill_width > 2:
            r_left = min(self.corner_radius, fill_width / 2.0)
            # If fill doesn't reach the end, keep right edge straight like native Blender sliders
            r_right = r_left if (fill_width >= self.width - 1.0) else 0.0
            fill_radii = (r_right, r_left, r_left, r_right) # (top_right, top_left, bottom_left, bottom_right)
            self.draw_rounded_rect(abs_x, abs_y, fill_width, self.height, fill_radii, fill_col)

        # 3. Rounded Border Outline
        self.draw_rounded_rect_outline(abs_x, abs_y, self.width, self.height, self.corner_radius, self.border_color, line_width=self.border_width)

        # 4. Formatted Display Text: "Label: 0.50"
        val_str = f"{self._value:.{self.precision}f}"
        display_str = f"{self.text}: {val_str}" if self.text else val_str
        
        available_txt_w = max(10, self.width - 14)
        tw, th = self.get_text_dimensions(display_str, font_id=0, size=self.font_size)
        tx = abs_x + max(6.0, (self.width - tw) / 2.0)
        ty = abs_y + (self.height - th) / 2.0 + 1.0

        self.draw_text(display_str, tx, ty, font_id=0, size=self.font_size, color=self.text_color, max_width=available_txt_w)
