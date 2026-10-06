from .base import UIElement

class UIColumn(UIElement):
    """
    Vertical layout container.
    Automatically stacks child elements from top of the panel downwards,
    and scales their width to fit the panel bounds with customizable margins.
    """

    def __init__(self, padding_x=12, padding_top=10, spacing=8):
        super().__init__(x=0, y=0, width=100, height=100)
        self.padding_x = padding_x
        self.padding_top = padding_top
        self.spacing = spacing
        self.children = []

    def add(self, element: UIElement):
        """Add a child widget to this column."""
        self.children.append(element)
        return element

    def clear(self):
        """Remove all children."""
        self.children.clear()

    def get_total_height(self) -> float:
        """Returns the total vertical height of all contained elements including margins."""
        from .theme import BlenderTheme
        scale = BlenderTheme.get_ui_scale()
        pad_top = self.padding_top * scale
        spacing = self.spacing * scale
        total = pad_top
        for child in self.children:
            if getattr(child, "visible", True):
                if hasattr(child, "get_total_height"):
                    h = child.get_total_height()
                else:
                    base_h = getattr(child, "base_height", getattr(child, "height", 24.0))
                    h = base_h * scale
                total += h + spacing
        return total

    def update_layout(self, panel_w, panel_h):
        """
        Recalculates child positions from top-down relative to panel (0, 0),
        scaling margins, item heights, and spacing with Blender's resolution scale.
        """
        from .theme import BlenderTheme
        scale = BlenderTheme.get_ui_scale()

        pad_x = self.padding_x * scale
        pad_top = self.padding_top * scale
        spacing = self.spacing * scale

        available_width = max(20.0, panel_w - (pad_x * 2.0))
        current_top_y = panel_h - pad_top

        for child in self.children:
            if not child.visible:
                continue
            
            # Scale height according to resolution scale
            base_h = getattr(child, "base_height", child.height)
            child.height = base_h * scale
            child.width = available_width
            
            # Position relative to panel bottom-left
            child.x = pad_x
            child.y = current_top_y - child.height
            
            # If child is a sub-container (e.g. UIRow), notify it to arrange children
            if hasattr(child, "update_layout"):
                child.update_layout(width=child.width, height=child.height)

            # Advance downward
            current_top_y -= (child.height + spacing)

    def handle_event(self, event, mouse_x, mouse_y, origin_x, origin_y) -> bool:
        if not self.visible or not self.enabled:
            return False

        # 1. If a child has active drag capture, route directly to it first
        for child in self.children:
            if getattr(child, 'is_dragging', False):
                return child.handle_event(event, mouse_x, mouse_y, origin_x, origin_y)

        # 2. If a dropdown is expanded, route events to it first with top priority
        for child in self.children:
            if getattr(child, 'is_expanded', False):
                return child.handle_event(event, mouse_x, mouse_y, origin_x, origin_y)

        # Standard top-to-bottom event pass
        consumed = False
        for child in self.children:
            if child.handle_event(event, mouse_x, mouse_y, origin_x, origin_y):
                consumed = True
                break

        return consumed

    def draw(self, origin_x, origin_y):
        if not self.visible:
            return

        # 1. Base widget draw pass
        for child in self.children:
            if child.visible:
                child.draw(origin_x, origin_y)

        # 2. Top-level overlay pass (for popup menus / tooltips)
        for child in self.children:
            if child.visible and hasattr(child, "draw_overlay"):
                child.draw_overlay(origin_x, origin_y)
