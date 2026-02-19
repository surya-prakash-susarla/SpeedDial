"""
WindowManager — get the focused window, raise a window, check if a window is alive.

All macOS API calls are delegated to a platform object so the manager itself
is fully testable without touching real system APIs.

In production, pass MacOSPlatform(). In tests, pass a mock.
"""
from typing import Optional
from window_info import WindowInfo


class WindowManager:
    def __init__(self, platform=None):
        if platform is None:
            from macos_platform import MacOSPlatform
            platform = MacOSPlatform()
        self._platform = platform

    def get_focused_window(self) -> Optional[WindowInfo]:
        """Return the currently focused window, or None if nothing is focused."""
        pid = self._platform.get_frontmost_pid()
        if pid is None:
            return None
        title = self._platform.get_focused_window_title(pid)
        window_id = self._platform.get_focused_window_id(pid)
        if title is None or window_id is None:
            return None
        return WindowInfo(pid=pid, window_id=window_id, title=title)

    def raise_window(self, window: WindowInfo) -> bool:
        """Activate the owning app and raise the specific window. Returns True on success."""
        if not self._platform.activate_app(window.pid):
            return False
        return self._platform.raise_window(window.pid, window.window_id)

    def is_window_alive(self, window: WindowInfo) -> bool:
        """Return True if the app is still running and the window still exists."""
        if window.pid not in self._platform.get_running_pids():
            return False
        return window.window_id in self._platform.get_window_ids_for_pid(window.pid)
