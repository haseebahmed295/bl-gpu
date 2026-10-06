import bpy

MODEL_TIMER_INTERVAL = 0.1

def create_event_handler_class(manager):
    """
    Dynamically creates an isolated Operator class with a unique bl_idname
    for the specified GpuManager instance.
    """
    op_idname = f"{manager.addon_id}.gpu_panel_handler"
    op_label = f"{manager.addon_id} GPU Event Handler"

    class DynamicEventHandler(bpy.types.Operator):
        bl_idname = op_idname
        bl_label = op_label
        bl_options = {'REGISTER'}

        _timer = None

        def modal(self, context, event):
            if not manager.is_modal_running:
                self.cancel(context)
                return {'CANCELLED'}

            process = manager.handle_event(context, event)
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
            if self._timer:
                wm.event_timer_remove(self._timer)
                self._timer = None

    return DynamicEventHandler


class EventHandler(bpy.types.Operator):
    """Default legacy operator for backwards compatibility"""
    bl_idname = "gpu.panel_handler"
    bl_label = "Custom GPU Event Handler"
    bl_options = {'REGISTER'}

    _timer = None

    def modal(self, context, event):
        from .manager import default_manager
        if not default_manager or not default_manager.is_modal_running:
            self.cancel(context)
            return {'CANCELLED'}

        process = default_manager.handle_event(context, event)
        if process in {'PASS_THROUGH', 'RUNNING_MODAL'}:
            return {process}
        self.cancel(context)
        return {'CANCELLED'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(MODEL_TIMER_INTERVAL, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
