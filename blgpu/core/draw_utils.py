import bpy
from .engine_bridge import HAS_ENGINE, my_engine

class GpuDrawManager:
    """Helper utilities for Blender 3D Viewport regions, panels, and redraws."""

    @staticmethod
    def get_3d_view_ui_region():
        if not bpy.context.window_manager:
            return None
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'UI':
                            return region
        return None

    @staticmethod
    def tag_redraw_all_3d_views():
        if not bpy.context.window_manager:
            return
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

    @staticmethod
    def get_panel_dimensions():
        if not HAS_ENGINE or not my_engine:
            return []
        ui_region = GpuDrawManager.get_3d_view_ui_region()
        if not ui_region:
            return []
        panels = my_engine.get_region_panels(ui_region.as_pointer())
        scroll = my_engine.get_region_scroll(ui_region.as_pointer())
        scroll_ymax = scroll.get('cur_ymax', 0) if scroll else 0

        panel_data = []
        for p in panels:
            x = p['offset_x']
            y = ui_region.height + p['offset_y'] - scroll_ymax
            w = p['size_x']
            h = p['size_y']
            panel_data.append((x, y, w, h, p['label'], p['is_open']))
        return panel_data

    @staticmethod
    def is_panel_active(target_category: str = "My Engine"):
        if not HAS_ENGINE or not my_engine:
            return False
        ui_region = GpuDrawManager.get_3d_view_ui_region()
        if not ui_region or ui_region.width <= 1:
            return False
        active_tab = my_engine.get_active_category(ui_region.as_pointer())
        return active_tab == target_category
