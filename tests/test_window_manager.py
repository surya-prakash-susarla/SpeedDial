"""
WindowManager wraps macOS Accessibility and Quartz APIs.
All platform calls are injected via a _platform object so tests never touch real APIs.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from window_info import WindowInfo
from window_manager import WindowManager


def make_platform(
    frontmost_pid=None,
    focused_window_title=None,
    focused_window_id=None,
    running_pids=None,
    window_titles_for_pid=None,
    raise_succeeds=True,
    activate_succeeds=True,
):
    """Build a mock platform object with controllable responses."""
    p = MagicMock()
    p.get_frontmost_pid.return_value = frontmost_pid
    p.get_focused_window_title.return_value = focused_window_title
    p.get_focused_window_id.return_value = focused_window_id
    p.get_running_pids.return_value = set(running_pids or [])
    p.get_window_titles_for_pid.return_value = list(window_titles_for_pid or [])
    p.raise_window.return_value = raise_succeeds
    p.activate_app.return_value = activate_succeeds
    return p


class TestGetFocusedWindow:
    def test_returns_window_info_when_frontmost_app_has_focused_window(self):
        p = make_platform(frontmost_pid=42, focused_window_title="iTerm2", focused_window_id=7)
        wm = WindowManager(platform=p)
        w = wm.get_focused_window()
        assert w is not None
        assert w.pid == 42
        assert w.window_id == 7
        assert w.title == "iTerm2"

    def test_returns_none_when_no_frontmost_app(self):
        p = make_platform(frontmost_pid=None)
        wm = WindowManager(platform=p)
        assert wm.get_focused_window() is None

    def test_returns_none_when_no_focused_window(self):
        p = make_platform(frontmost_pid=42, focused_window_title=None, focused_window_id=None)
        wm = WindowManager(platform=p)
        assert wm.get_focused_window() is None

    def test_queries_platform_for_frontmost_pid(self):
        p = make_platform(frontmost_pid=99, focused_window_title="x", focused_window_id=1)
        wm = WindowManager(platform=p)
        wm.get_focused_window()
        p.get_frontmost_pid.assert_called_once()

    def test_queries_focused_window_using_frontmost_pid(self):
        p = make_platform(frontmost_pid=55, focused_window_title="Chrome", focused_window_id=3)
        wm = WindowManager(platform=p)
        wm.get_focused_window()
        p.get_focused_window_title.assert_called_once_with(55)
        p.get_focused_window_id.assert_called_once_with(55)

    def test_does_not_query_focused_window_when_no_frontmost_pid(self):
        p = make_platform(frontmost_pid=None)
        wm = WindowManager(platform=p)
        wm.get_focused_window()
        p.get_focused_window_title.assert_not_called()


class TestRaiseWindow:
    def test_activates_app_then_raises_window(self):
        p = make_platform(activate_succeeds=True, raise_succeeds=True)
        wm = WindowManager(platform=p)
        w = WindowInfo(pid=10, window_id=5, title="Cursor")
        result = wm.raise_window(w)
        p.activate_app.assert_called_once_with(10)
        p.raise_window.assert_called_once_with(10, 5)
        assert result is True

    def test_returns_false_when_activate_fails(self):
        p = make_platform(activate_succeeds=False, raise_succeeds=True)
        wm = WindowManager(platform=p)
        w = WindowInfo(pid=10, window_id=5, title="Cursor")
        result = wm.raise_window(w)
        assert result is False

    def test_returns_false_when_raise_fails(self):
        p = make_platform(activate_succeeds=True, raise_succeeds=False)
        wm = WindowManager(platform=p)
        w = WindowInfo(pid=10, window_id=5, title="Cursor")
        result = wm.raise_window(w)
        assert result is False

    def test_does_not_raise_window_if_activate_fails(self):
        p = make_platform(activate_succeeds=False)
        wm = WindowManager(platform=p)
        w = WindowInfo(pid=10, window_id=5, title="Cursor")
        wm.raise_window(w)
        p.raise_window.assert_not_called()


class TestIsWindowAlive:
    def test_returns_true_when_pid_running_and_window_id_present(self):
        p = make_platform(running_pids=[42], focused_window_id=7)
        p.get_window_ids_for_pid.return_value = [7, 8, 9]
        wm = WindowManager(platform=p)
        w = WindowInfo(pid=42, window_id=7, title="Anything")
        assert wm.is_window_alive(w) is True

    def test_returns_false_when_pid_not_running(self):
        p = make_platform(running_pids=[])
        p.get_window_ids_for_pid.return_value = []
        wm = WindowManager(platform=p)
        w = WindowInfo(pid=42, window_id=7, title="Anything")
        assert wm.is_window_alive(w) is False

    def test_returns_false_when_window_id_not_found_for_pid(self):
        p = make_platform(running_pids=[42])
        p.get_window_ids_for_pid.return_value = [8, 9, 10]  # 7 is not here
        wm = WindowManager(platform=p)
        w = WindowInfo(pid=42, window_id=7, title="Anything")
        assert wm.is_window_alive(w) is False

    def test_queries_running_pids(self):
        p = make_platform(running_pids=[42])
        p.get_window_ids_for_pid.return_value = [7]
        wm = WindowManager(platform=p)
        wm.is_window_alive(WindowInfo(pid=42, window_id=7, title="X"))
        p.get_running_pids.assert_called_once()

    def test_does_not_query_window_ids_when_pid_not_running(self):
        p = make_platform(running_pids=[])
        wm = WindowManager(platform=p)
        wm.is_window_alive(WindowInfo(pid=42, window_id=7, title="X"))
        p.get_window_ids_for_pid.assert_not_called()
