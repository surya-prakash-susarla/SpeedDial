"""
MacOSPlatform — thin adapter over macOS Accessibility and Quartz APIs.

This module is the only place in the codebase that directly calls macOS APIs.
It is not unit-tested (it requires a live macOS session with Accessibility
permissions). Integration testing is done by running the app itself.
"""
from typing import Optional


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
            return None
        err, title = AS.AXUIElementCopyAttributeValue(
            ax_window, AS.kAXTitleAttribute, None
        )
        if err != AS.kAXErrorSuccess:
            return None
        return title

    def get_focused_window_id(self, pid: int) -> Optional[int]:
        import ApplicationServices as AS
        import Quartz
        ax_app = AS.AXUIElementCreateApplication(pid)
        err, ax_window = AS.AXUIElementCopyAttributeValue(
            ax_app, AS.kAXFocusedWindowAttribute, None
        )
        if err != AS.kAXErrorSuccess or ax_window is None:
            return None
        # Match the AX window to a CGWindowID via position+size cross-reference
        err, pos_val = AS.AXUIElementCopyAttributeValue(
            ax_window, AS.kAXPositionAttribute, None
        )
        err2, size_val = AS.AXUIElementCopyAttributeValue(
            ax_window, AS.kAXSizeAttribute, None
        )
        if err != AS.kAXErrorSuccess or err2 != AS.kAXErrorSuccess:
            return None
        import Quartz.CoreGraphics as CG
        ok, ax_pos = AS.AXValueGetValue(pos_val, AS.kAXValueCGPointType, None)
        ok2, ax_size = AS.AXValueGetValue(size_val, AS.kAXValueCGSizeType, None)
        if not ok or not ok2:
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
                return info.get("kCGWindowNumber")
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
        from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
        apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(None)
        # Find by PID among all running apps
        from AppKit import NSWorkspace
        for app in NSWorkspace.sharedWorkspace().runningApplications():
            if app.processIdentifier() == pid:
                return app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        return False

    def raise_window(self, pid: int, window_id: int) -> bool:
        import ApplicationServices as AS
        ax_app = AS.AXUIElementCreateApplication(pid)
        err, windows = AS.AXUIElementCopyAttributeValue(
            ax_app, AS.kAXWindowsAttribute, None
        )
        if err != AS.kAXErrorSuccess or not windows:
            return False
        import Quartz
        for ax_win in windows:
            # Match by position cross-reference to CGWindowID
            wid = self._get_cgwindow_id_for_ax_window(ax_win, pid)
            if wid == window_id:
                err = AS.AXUIElementPerformAction(ax_win, AS.kAXRaiseAction)
                return err == AS.kAXErrorSuccess
        return False

    def _get_cgwindow_id_for_ax_window(self, ax_win, pid: int) -> Optional[int]:
        import ApplicationServices as AS
        err, pos_val = AS.AXUIElementCopyAttributeValue(
            ax_win, AS.kAXPositionAttribute, None
        )
        err2, size_val = AS.AXUIElementCopyAttributeValue(
            ax_win, AS.kAXSizeAttribute, None
        )
        if err != AS.kAXErrorSuccess or err2 != AS.kAXErrorSuccess:
            return None
        ok, ax_pos = AS.AXValueGetValue(pos_val, AS.kAXValueCGPointType, None)
        if not ok:
            return None
        import Quartz
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
