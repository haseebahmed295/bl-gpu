from .base import UIElement

class UIRow(UIElement):
    """
    Horizontal layout container.
    Arranges multiple elements side-by-side inside an available width.
    Can be placed inside a UIColumn.
    """

    def __init__(self, spacing=6, height=28):
        super().__init__(x=0, y=0, width=100, height=height)
        self.spacing = spacing
        self.children = []

    def add(self, element: UIElement):
        """Add a child widget to this row."""
        self.children.append(element)
        return element

    def update_layout(self, width=None, height=None):
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height

        visible_children = [c for c in self.children if c.visible]
        if not visible_children:
            return

        from .theme import BlenderTheme
        scale = BlenderTheme.get_ui_scale()
        scaled_spacing = self.spacing * scale

        total_spacing = scaled_spacing * (len(visible_children) - 1)
        item_width = max(10.0, (self.width - total_spacing) / len(visible_children))

        # Children offsets relative to UIRow itself
        current_rel_x = 0
        for child in visible_children:
            child.x = current_rel_x
            child.y = 0
            child.width = item_width
            child.height = self.height
            current_rel_x += (item_width + scaled_spacing)

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        # Nested origin for row children
        row_origin_x = origin_x + self.x
        row_origin_y = origin_y + self.y

        # First check active dragging
        for child in self.children:
            if getattr(child, 'is_dragging', False):
                return child.handle_event(event, mouse_x, mouse_y, row_origin_x, row_origin_y)

        consumed = False
        for child in self.children:
            if child.handle_event(event, mouse_x, mouse_y, row_origin_x, row_origin_y):
                consumed = True
                break

        return consumed

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        row_origin_x = origin_x + self.x
        row_origin_y = origin_y + self.y

        for child in self.children:
            if child.visible:
                child.draw(row_origin_x, row_origin_y)
