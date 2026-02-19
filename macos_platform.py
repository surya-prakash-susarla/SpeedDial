"""
MacOSPlatform — thin adapter over macOS Accessibility and Quartz APIs.

This module is the only place in the codebase that directly calls macOS APIs.
It is not unit-tested (it requires a live macOS session with Accessibility
permissions). Integration testing is done by running the app itself.
"""
import ctypes
import logging
import time
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Private AX API: _AXUIElementGetWindow
# Gives us the CGWindowID for any AXUIElement window directly — no position
# guessing. This is a private symbol in ApplicationServices, stable since 10.6.
# ---------------------------------------------------------------------------
_ax_lib = None


def _get_ax_lib():
    global _ax_lib
    if _ax_lib is None:
        _ax_lib = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        _ax_lib._AXUIElementGetWindow.restype = ctypes.c_int32
        _ax_lib._AXUIElementGetWindow.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
        ]
    return _ax_lib


def _ax_element_get_window_id(ax_win) -> Optional[int]:
    """Return the CGWindowID for an AX window element, or None on failure."""
    try:
        import objc
        wid = ctypes.c_uint32(0)
        err = _get_ax_lib()._AXUIElementGetWindow(objc.pyobjc_id(ax_win), ctypes.byref(wid))
        return wid.value if err == 0 else None
    except Exception:
        log.debug("_ax_element_get_window_id failed", exc_info=True)
        return None


def _get_ax_windows(ax_app, retries: int = 3, delay: float = 0.05):
    """
    Fetch kAXWindowsAttribute with retry. Some apps (e.g. Chrome, Firefox)
    return an empty list immediately after activation before their AX tree
    is ready. A short retry loop resolves this.
    """
    import ApplicationServices as AS
    for attempt in range(retries):
        err, windows = AS.AXUIElementCopyAttributeValue(
            ax_app, AS.kAXWindowsAttribute, None
        )
        if err != AS.kAXErrorSuccess:
            log.debug("_get_ax_windows: err=%d on attempt %d", err, attempt)
            return None
        if windows:
            return windows
        if attempt < retries - 1:
            log.debug("_get_ax_windows: empty result, retrying in %.0fms", delay * 1000)
            time.sleep(delay)
    return None


class MacOSPlatform:
    def get_frontmost_pid(self) -> Optional[int]:
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        return app.processIdentifier()

    def get_focused_window_title(self, pid: int) -> Optional[str]:
        import ApplicationServices as AS
        ax_app = AS.AXUIElementCreateApplication(pid)
        err, ax_window = AS.AXUIElementCopyAttributeValue(
            ax_app, AS.kAXFocusedWindowAttribute, None
        )
        if err != AS.kAXErrorSuccess or ax_window is None:
            log.debug("get_focused_window_title: no focused window for pid=%d (err=%d)", pid, err)
            return None
        err, title = AS.AXUIElementCopyAttributeValue(
            ax_window, AS.kAXTitleAttribute, None
        )
        if err != AS.kAXErrorSuccess:
            log.debug("get_focused_window_title: no title for pid=%d (err=%d)", pid, err)
            return None
        return title

    def get_focused_window_id(self, pid: int) -> Optional[int]:
        """
        Return the CGWindowID of the currently focused window for the given app.
        Uses _AXUIElementGetWindow (private but stable) for a direct mapping.
        Falls back to position-based CGWindowList cross-reference if needed.
        """
        import ApplicationServices as AS
        ax_app = AS.AXUIElementCreateApplication(pid)
        err, ax_window = AS.AXUIElementCopyAttributeValue(
            ax_app, AS.kAXFocusedWindowAttribute, None
        )
        if err != AS.kAXErrorSuccess or ax_window is None:
            return None

        # Primary: private API — direct, no heuristics
        wid = _ax_element_get_window_id(ax_window)
        if wid:
            log.debug("get_focused_window_id: pid=%d -> window_id=%d (via _AXUIElementGetWindow)", pid, wid)
            return wid

        # Fallback: position cross-reference
        wid = self._cgwindow_id_by_position(ax_window, pid)
        if wid:
            log.debug("get_focused_window_id: pid=%d -> window_id=%d (via position)", pid, wid)
        else:
            log.debug("get_focused_window_id: could not resolve window_id for pid=%d", pid)
        return wid

    def get_running_pids(self) -> set:
        from AppKit import NSWorkspace
        apps = NSWorkspace.sharedWorkspace().runningApplications()
        return {app.processIdentifier() for app in apps}

    def get_window_ids_for_pid(self, pid: int) -> list:
        import Quartz
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        return [
            info["kCGWindowNumber"]
            for info in window_list
            if info.get("kCGWindowOwnerPID") == pid
        ]

    def activate_app(self, pid: int) -> bool:
        from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            if app.processIdentifier() == pid:
                result = bool(app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps))
                log.debug("activate_app: pid=%d -> %s", pid, result)
                return result
        log.warning("activate_app: no app found with pid=%d", pid)
        return False

    def raise_window(self, pid: int, window_id: int, title: str = "") -> bool:
        """
        Raise the target window. After activating the app, we find the specific
        AX window by CGWindowID (via _AXUIElementGetWindow), falling back to
        title match, then first window. Retries on empty AX window list.
        """
        import ApplicationServices as AS
        ax_app = AS.AXUIElementCreateApplication(pid)
        windows = _get_ax_windows(ax_app)

        if not windows:
            log.debug("raise_window: no AX windows available for pid=%d — app activated, accepting", pid)
            return True

        target = None

        # 1. CGWindowID match — exact, title-change-resistant
        if window_id:
            for ax_win in windows:
                wid = _ax_element_get_window_id(ax_win)
                if wid == window_id:
                    target = ax_win
                    log.debug("raise_window: matched by window_id=%d", window_id)
                    break

        # 2. Title match — handles apps that don't expose CGWindowID via AX
        if target is None and title:
            for ax_win in windows:
                e, win_title = AS.AXUIElementCopyAttributeValue(
                    ax_win, AS.kAXTitleAttribute, None
                )
                if e == AS.kAXErrorSuccess and win_title == title:
                    target = ax_win
                    log.debug("raise_window: matched by title '%s'", title)
                    break

        # 3. First window fallback
        if target is None:
            target = windows[0]
            log.debug("raise_window: using first window as fallback for pid=%d", pid)

        err = AS.AXUIElementPerformAction(target, AS.kAXRaiseAction)
        if err != AS.kAXErrorSuccess:
            log.warning("raise_window: kAXRaiseAction failed for pid=%d (err=%d)", pid, err)
        return True

    def _cgwindow_id_by_position(self, ax_window, pid: int) -> Optional[int]:
        """Position-based CGWindowID lookup — fallback only."""
        import ApplicationServices as AS
        import Quartz
        err, pos_val = AS.AXUIElementCopyAttributeValue(
            ax_window, AS.kAXPositionAttribute, None
        )
        if err != AS.kAXErrorSuccess:
            return None
        ok, ax_pos = AS.AXValueGetValue(pos_val, AS.kAXValueCGPointType, None)
        if not ok:
            return None
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        for info in window_list:
            if info.get("kCGWindowOwnerPID") != pid:
                continue
            bounds = info.get("kCGWindowBounds", {})
            if abs(bounds.get("X", -9999) - ax_pos.x) < 2 and abs(bounds.get("Y", -9999) - ax_pos.y) < 2:
                return info.get("kCGWindowNumber")
        return None
