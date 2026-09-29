import bpy

MODEL_TIMER_INTERVAL = 0.1

class EventHandler(bpy.types.Operator):
    """Event Handler for the Custom GPU Panel Engine"""
    bl_idname = "gpu.panel_handler"
    bl_label = "Custom GPU Event Handler"
    bl_options = {'REGISTER'}

    _timer = None

    def modal(self, context, event):
        if context.scene.gpu_event_handler_state == False:
            self.cancel(context)
            # self.report({'INFO'}, "Modal Killed")
            return {'CANCELLED'}

        process = self.handle_timer_event(context, event)
        if process == 'PASS_THROUGH':
            return {'PASS_THROUGH'}
        elif process == 'RUNNING_MODAL':
            return {'RUNNING_MODAL'}
        elif process in ('CANCELLED', 'FINISHED'):
            self.cancel(context)
            return {process}
        else:
            return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(MODEL_TIMER_INTERVAL, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

    def handle_timer_event(self, context, event):
        from . import gpu_core
        
        # Only process when panel widgets are present and panel is active
        if not gpu_core.panel_widgets or not gpu_core.GpuDrawManager.is_panel_active():
            return "PASS_THROUGH"

        # 1. First, check if any widget is focused for keyboard input
        if event.value in {'PRESS', 'RELEASE'} and event.type not in {'TIMER', 'MOUSEMOVE', 'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            def route_key(widget):
                if getattr(widget, 'is_focused', False) and hasattr(widget, 'handle_keyboard_event'):
                    return widget.handle_keyboard_event(event)
                if hasattr(widget, 'children'):
                    for c in widget.children:
                        res = route_key(c)
                        if res: return True
                return False

            for w in gpu_core.panel_widgets:
                if route_key(w):
                    gpu_core.GpuDrawManager.tag_redraw_all_3d_views()
                    return "RUNNING_MODAL"

        ui_region = gpu_core.GpuDrawManager.get_3d_view_ui_region()
        if not ui_region:
            return "PASS_THROUGH"

        # Check if mouse is within the UI region bounds (window-space)
        mx = event.mouse_x
        my = event.mouse_y
        
        # Region relative coordinates
        rx = mx - ui_region.x
        ry = my - ui_region.y

        # Check if any widget holds active drag capture
        any_dragging = False
        for w in gpu_core.panel_widgets:
            if getattr(w, 'is_dragging', False):
                any_dragging = True
                break
            if hasattr(w, 'children'):
                for c in w.children:
                    if getattr(c, 'is_dragging', False):
                        any_dragging = True
                        break

        # If mouse is outside the sidebar region and NOT dragging, clear hover on widgets
        if not any_dragging and not (0 <= rx <= ui_region.width and 0 <= ry <= ui_region.height):
            cleared = False
            for w in gpu_core.panel_widgets:
                if w.hovered or w.pressed:
                    w.hovered = False
                    w.pressed = False
                    cleared = True
                if hasattr(w, 'children'):
                    for c in w.children:
                        if c.hovered or c.pressed:
                            c.hovered = False
                            c.pressed = False
                            cleared = True
            if cleared:
                gpu_core.GpuDrawManager.tag_redraw_all_3d_views()
            return "PASS_THROUGH"

        # Mouse is inside UI region; find the target panel's origin
        panels = gpu_core.GpuDrawManager.get_panel_dimensions()
        for panel in panels:
            px, py, pw, ph, label, is_open = panel
            if label == "Custom GPU Engine" and is_open:
                needs_redraw = False
                for widget in gpu_core.panel_widgets:
                    consumed = widget.handle_event(
                        event=event,
                        mouse_x=rx,
                        mouse_y=ry,
                        origin_x=px,
                        origin_y=py
                    )
                    if consumed:
                        needs_redraw = True

                if needs_redraw:
                    gpu_core.GpuDrawManager.tag_redraw_all_3d_views()
                break

        return "PASS_THROUGH"