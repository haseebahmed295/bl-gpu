"""
Blender native UI color palette and dimension standards.
Matches Blender's default theme (Theme.default) values.
"""

class BlenderTheme:
    # Widget Backgrounds
    BG_BUTTON = (0.212, 0.212, 0.212, 1.0)        # #363636
    BG_BUTTON_HOVER = (0.278, 0.278, 0.278, 1.0)  # #474747
    BG_BUTTON_ACTIVE = (0.15, 0.15, 0.15, 1.0)    # #262626
    
    # Inset fields (Text inputs, Number fields, Slider tracks)
    BG_INSET = (0.125, 0.125, 0.125, 1.0)         # #202020
    BG_INSET_HOVER = (0.165, 0.165, 0.165, 1.0)   # #2a2a2a

    # Blender Signature Primary Blue (Selection / Slider Progress / Active Check)
    PRIMARY_BLUE = (0.278, 0.447, 0.702, 1.0)     # #4772b3
    PRIMARY_BLUE_HOVER = (0.33, 0.52, 0.80, 1.0)
    PRIMARY_BLUE_ACTIVE = (0.22, 0.38, 0.62, 1.0)

    # Panel / Window Background (Matches N-Panel sidebar)
    BG_PANEL = (0.18, 0.18, 0.18, 1.0)            # #2e2e2e

    # Borders & Outlines
    BORDER_DARK = (0.09, 0.09, 0.09, 1.0)         # #171717
    BORDER_LIGHT = (0.32, 0.32, 0.32, 1.0)        # #525252
    BORDER_FOCUS = (0.278, 0.447, 0.702, 1.0)     # Focus outline

    # Typography
    TEXT_MAIN = (0.86, 0.86, 0.86, 1.0)           # #dcdcdc
    TEXT_MUTED = (0.55, 0.55, 0.55, 1.0)          # #8c8c8c
    TEXT_HEADER = (0.68, 0.68, 0.68, 1.0)

    # Geometry (Base pixels before UI resolution scaling)
    CORNER_RADIUS = 3.5
    LINE_WIDTH = 1.0

    @staticmethod
    def get_ui_scale():
        """Retrieve Blender's current UI resolution scale (Preferences -> Interface -> Resolution Scale)."""
        try:
            import bpy
            return float(bpy.context.preferences.view.ui_scale)
        except Exception:
            return 1.0

    @classmethod
    def scale(cls, val):
        """Scales a pixel value according to Blender's active UI resolution scale."""
        return val * cls.get_ui_scale()
