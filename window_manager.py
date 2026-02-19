"""
WindowManager — get the focused window, raise a window, check if a window is alive.

All macOS API calls are delegated to a platform object so the manager itself
is fully testable without touching real system APIs.

In production, pass MacOSPlatform(). In tests, pass a mock.
"""
import logging
from typing import Optional
from window_info import WindowInfo

log = logging.getLogger(__name__)


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
        if title is None:
            return None
        # window_id is best-effort; use 0 if CGWindowID matching fails
        window_id = self._platform.get_focused_window_id(pid) or 0
        log.debug("get_focused_window: pid=%d title=%r window_id=%d", pid, title, window_id)
        return WindowInfo(pid=pid, window_id=window_id, title=title)

    def raise_window(self, window: WindowInfo) -> bool:
        """Activate the owning app and raise the specific window. Returns True on success."""
        log.debug("raise_window: %r", window)
        if not self._platform.activate_app(window.pid):
            log.warning("raise_window: activate_app failed for pid=%d", window.pid)
            return False
        return self._platform.raise_window(window.pid, window.window_id, window.title)

    def is_window_alive(self, window: WindowInfo) -> bool:
        """Return True if the app is still running and the window still exists."""
        if window.pid not in self._platform.get_running_pids():
            return False
        return window.window_id in self._platform.get_window_ids_for_pid(window.pid)
