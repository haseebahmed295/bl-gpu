class GpuCanvas:
    """
    Represents an isolated GPU canvas dynamically bound to a specific Blender N-Panel.
    """
    def __init__(self, category: str, panel_label: str, panel_idname: str = None, min_height: float = 100.0):
        self.category = str(category)
        self.panel_label = str(panel_label)
        self.panel_idname = str(panel_idname) if panel_idname else ""
        self.min_height = float(min_height)
        self.widgets = []

        # Runtime cached state
        self.current_rect = None  # (x, y, w, h)
        self.is_visible = False

    def add(self, widget):
        self.widgets.append(widget)
        return widget

    def add_widget(self, widget):
        """Convenience alias for add(widget)."""
        return self.add(widget)


    def clear(self):
        self.widgets.clear()

    def get_content_height(self) -> float:
        """Calculates total vertical height needed for the panel placeholder."""
        total_h = 0.0
        for w in self.widgets:
            if hasattr(w, "get_total_height"):
                total_h += w.get_total_height()
            elif hasattr(w, "total_height"):
                total_h += w.total_height
            elif hasattr(w, "height"):
                total_h += w.height
        return max(self.min_height, total_h)

    def draw_placeholder(self, layout, scale_factor: float = None):
        """
        Draws the vertical spacer inside the Panel's draw(context) method to reserve
        space for the custom GPU elements.
        """
        col = layout.column()
        if scale_factor is not None:
            col.scale_y = float(scale_factor)
        else:
            # 1.0 scale_y corresponds to roughly 20px of standard row height in Blender UI
            h = self.get_content_height()
            col.scale_y = max(1.0, h / 20.0)
        col.label(text="")
