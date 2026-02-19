"""
MacOSPlatform — thin adapter over macOS Accessibility and Quartz APIs.

This module is the only place in the codebase that directly calls macOS APIs.
It is not unit-tested (it requires a live macOS session with Accessibility
permissions). Integration testing is done by running the app itself.
"""
import logging
from typing import Optional

log = logging.getLogger(__name__)


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
        Best-effort: return the CGWindowID of the focused window by cross-referencing
        the AX window position against CGWindowListCopyWindowInfo.
        Returns None if the match cannot be made — callers must tolerate this.
        """
        import ApplicationServices as AS
        import Quartz
        ax_app = AS.AXUIElementCreateApplication(pid)
        err, ax_window = AS.AXUIElementCopyAttributeValue(
            ax_app, AS.kAXFocusedWindowAttribute, None
        )
        if err != AS.kAXErrorSuccess or ax_window is None:
            return None
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
            if (
                abs(bounds.get("X", -9999) - ax_pos.x) < 2
                and abs(bounds.get("Y", -9999) - ax_pos.y) < 2
            ):
                wid = info.get("kCGWindowNumber")
                log.debug("get_focused_window_id: pid=%d -> window_id=%d", pid, wid)
                return wid
        log.debug("get_focused_window_id: no CGWindow matched AX position for pid=%d", pid)
        return None

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
        Raise the target window. Strategy (in order):
          1. Find AX window whose title matches the stored title.
          2. Fall back to CGWindowID position-match if title match fails.
          3. Fall back to the first window of the app.
        Always returns True once the app is activated — the window raise is
        best-effort and failures are logged, not propagated.
        """
        import ApplicationServices as AS
        ax_app = AS.AXUIElementCreateApplication(pid)
        err, windows = AS.AXUIElementCopyAttributeValue(
            ax_app, AS.kAXWindowsAttribute, None
        )
        if err != AS.kAXErrorSuccess or not windows:
            log.debug("raise_window: no AX windows for pid=%d (err=%d)", pid, err)
            return True  # app is active; no window list — treat as ok

        target = None

        # 1. Title match
        if title:
            for ax_win in windows:
                e, win_title = AS.AXUIElementCopyAttributeValue(
                    ax_win, AS.kAXTitleAttribute, None
                )
                if e == AS.kAXErrorSuccess and win_title == title:
                    target = ax_win
                    log.debug("raise_window: matched by title '%s'", title)
                    break

        # 2. CGWindowID position match
        if target is None and window_id:
            for ax_win in windows:
                wid = self._get_cgwindow_id_for_ax_window(ax_win, pid)
                if wid == window_id:
                    target = ax_win
                    log.debug("raise_window: matched by window_id=%d", window_id)
                    break

        # 3. First window fallback
        if target is None:
            target = windows[0]
            log.debug("raise_window: using first window as fallback for pid=%d", pid)

        err = AS.AXUIElementPerformAction(target, AS.kAXRaiseAction)
        if err != AS.kAXErrorSuccess:
            log.warning("raise_window: kAXRaiseAction failed for pid=%d (err=%d)", pid, err)
        return True

    def _get_cgwindow_id_for_ax_window(self, ax_win, pid: int) -> Optional[int]:
        import ApplicationServices as AS
        import Quartz
        err, pos_val = AS.AXUIElementCopyAttributeValue(
            ax_win, AS.kAXPositionAttribute, None
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
