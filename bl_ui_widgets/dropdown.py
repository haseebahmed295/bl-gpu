from .base import UIElement
from .theme import BlenderTheme

class UIDropdown(UIElement):
    """
    Dropdown / Enum combobox element styled to match Blender's native menus.
    """

    def __init__(
        self,
        items=None,
        default_index=0,
        x=0,
        y=0,
        width=180,
        height=24,
        corner_radius=None,
        border_width=None,
        border_color=None,
        on_select=None
    ):
        super().__init__(x=x, y=y, width=width, height=height)
        self.items = list(items) if items else ["Option 1", "Option 2"]
        self.selected_index = max(0, min(len(self.items) - 1, default_index))
        self.on_select = on_select

        self.is_expanded = False
        self.hovered_item_index = -1
        
        # Native Styling
        self.color_bg = BlenderTheme.BG_BUTTON
        self.color_bg_hover = BlenderTheme.BG_BUTTON_HOVER
        self.color_menu_bg = (0.15, 0.15, 0.15, 0.98)
        self.color_item_hover = BlenderTheme.PRIMARY_BLUE
        self.border_color = border_color if border_color is not None else BlenderTheme.BORDER_DARK
        self.border_width = border_width if border_width is not None else BlenderTheme.LINE_WIDTH
        self.text_color = BlenderTheme.TEXT_MAIN
        self.corner_radius = corner_radius if corner_radius is not None else BlenderTheme.CORNER_RADIUS
        self.font_size = 11
        self.item_height = 22

    @property
    def selected_text(self):
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return ""

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        inside_header = self.is_point_inside(mouse_x, mouse_y, origin_x, origin_y)

        # 1. When expanded, test popup menu bounds
        scale = BlenderTheme.get_ui_scale()
        item_h = self.item_height * scale

        if self.is_expanded:
            menu_h = len(self.items) * item_h
            menu_y = abs_y - menu_h
            inside_menu = (abs_x <= mouse_x <= abs_x + self.width) and (menu_y <= mouse_y <= abs_y)

            if event.type == 'MOUSEMOVE':
                if inside_menu:
                    offset_from_top = abs_y - mouse_y
                    idx = int(offset_from_top // item_h)
                    idx = max(0, min(len(self.items) - 1, idx))
                    if idx != self.hovered_item_index:
                        self.hovered_item_index = idx
                        return True
                else:
                    if self.hovered_item_index != -1:
                        self.hovered_item_index = -1
                        return True
                return False

            elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                if inside_menu and 0 <= self.hovered_item_index < len(self.items):
                    self.selected_index = self.hovered_item_index
                    self.is_expanded = False
                    self.hovered_item_index = -1
                    if self.on_select:
                        self.on_select(self, self.selected_index, self.items[self.selected_index])
                    return True
                else:
                    self.is_expanded = False
                    self.hovered_item_index = -1
                    return True

        # 2. Closed Header handling
        if event.type == 'MOUSEMOVE':
            if inside_header != self.hovered:
                self.hovered = inside_header
                return True
            return False

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if inside_header:
                self.is_expanded = not self.is_expanded
                self.hovered_item_index = -1
                return True

        return False

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        # 1. Rounded Header Box
        bg_col = self.color_bg_hover if self.hovered else self.color_bg
        self.draw_rounded_rect(abs_x, abs_y, self.width, self.height, self.corner_radius, bg_col)
        self.draw_rounded_rect_outline(abs_x, abs_y, self.width, self.height, self.corner_radius, self.border_color, line_width=self.border_width)

        # 2. Selected Text & Dropdown Arrow
        tw, th = self.get_text_dimensions(self.selected_text, font_id=0, size=self.font_size)
        ty = abs_y + (self.height - th) / 2.0 + (1.0 * scale)
        max_label_w = max(10.0, self.width - (24.0 * scale))
        self.draw_text(self.selected_text, abs_x + (8.0 * scale), ty, font_id=0, size=self.font_size, color=self.text_color, max_width=max_label_w)

        # Downward indicator arrow 'v'
        self.draw_text("v", abs_x + self.width - (14.0 * scale), ty, font_id=0, size=9, color=BlenderTheme.TEXT_MUTED)

    def draw_overlay(self, origin_x, origin_y):
        """Draw the floating popup menu OVER all other widgets."""
        if not self.visible or not self.is_expanded:
            return

        scale = BlenderTheme.get_ui_scale()
        abs_x = origin_x + self.x
        abs_y = origin_y + self.y

        item_h = self.item_height * scale
        menu_h = len(self.items) * item_h
        menu_y = abs_y - menu_h

        # Rounded background menu quad with drop outline
        self.draw_rounded_rect(abs_x, menu_y, self.width, menu_h, 3.0, self.color_menu_bg)
        self.draw_rounded_rect_outline(abs_x, menu_y, self.width, menu_h, 3.0, (0.35, 0.35, 0.35, 1.0), line_width=1.0)

        # Draw items from top to bottom
        for i, item_str in enumerate(self.items):
            item_y = abs_y - ((i + 1) * item_h)
            
            # Highlight hovered or active item
            if i == self.hovered_item_index:
                self.draw_rounded_rect(abs_x + (2.0 * scale), item_y + (1.0 * scale), self.width - (4.0 * scale), item_h - (2.0 * scale), 2.0, self.color_item_hover)
            elif i == self.selected_index:
                self.draw_rounded_rect(abs_x + (2.0 * scale), item_y + (1.0 * scale), self.width - (4.0 * scale), item_h - (2.0 * scale), 2.0, (0.22, 0.22, 0.22, 1.0))

            itw, ith = self.get_text_dimensions(item_str, font_id=0, size=self.font_size)
            ity = item_y + (item_h - ith) / 2.0 + (1.0 * scale)
            self.draw_text(item_str, abs_x + (10.0 * scale), ity, font_id=0, size=self.font_size, color=self.text_color, max_width=self.width - (20.0 * scale))
