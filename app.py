"""
SpeedDialApp — the controller.

Wires SlotRegistry, WindowManager, and MenuBar together.
Receives callbacks from HotkeyListener and delegates to the right operations.
All dependencies are injected; this class has no macOS API calls of its own.
"""
from slot_registry import SlotRegistry
from window_manager import WindowManager
from menu_bar import MenuBar


class SpeedDialApp:
    def __init__(
        self,
        registry: SlotRegistry,
        window_manager: WindowManager,
        menu_bar: MenuBar,
    ):
        self._registry = registry
        self._wm = window_manager
        self._menu_bar = menu_bar

    def handle_assign(self, slot: int) -> None:
        """Assign the currently focused window to slot."""
        window = self._wm.get_focused_window()
        if window is None:
            return
        self._registry.assign(slot, window)
        self._menu_bar.refresh()

    def handle_jump(self, slot: int) -> None:
        """Raise the window assigned to slot. Clear the slot if the window is gone."""
        window = self._registry.get(slot)
        if window is None:
            return
        success = self._wm.raise_window(window)
        if not success:
            self._registry.clear(slot)
            self._menu_bar.refresh()
