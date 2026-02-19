"""
Integration tests for the speeddial entry-point wiring.

We don't run NSApplication.run() in tests (that would block forever and
require a real display). Instead we test that build_app() correctly wires
all components together and returns a SpeedDialApp whose callbacks are
connected to the HotkeyListener.

The test simulates the full assign→jump round-trip by:
  1. Calling the on_assign callback (as the HotkeyListener would)
  2. Asserting the registry reflects the assignment
  3. Calling the on_jump callback
  4. Asserting window_manager.raise_window was called with the right window
"""
import pytest
from unittest.mock import MagicMock, patch
from window_info import WindowInfo


def make_platform(pid=42, window_id=7, title="TestApp"):
    p = MagicMock()
    p.get_frontmost_pid.return_value = pid
    p.get_focused_window_title.return_value = title
    p.get_focused_window_id.return_value = window_id
    p.get_running_pids.return_value = {pid}
    p.get_window_ids_for_pid.return_value = [window_id]
    p.activate_app.return_value = True
    p.raise_window.return_value = True
    return p


def make_appkit():
    ak = MagicMock()
    ak.NSVariableStatusItemLength = -1
    menu = MagicMock()
    status_item = MagicMock()
    status_bar = MagicMock()
    status_bar.statusItemWithLength_.return_value = status_item
    ak.NSStatusBar.systemStatusBar.return_value = status_bar
    ak.NSMenu.return_value = menu
    ak.NSMenuItem.return_value = MagicMock()
    return ak


class TestBuildApp:
    def test_build_app_returns_speed_dial_app(self):
        from speeddial import build_app
        from app import SpeedDialApp
        platform = make_platform()
        appkit = make_appkit()
        result = build_app(platform=platform, appkit=appkit)
        assert isinstance(result, SpeedDialApp)

    def test_build_app_wires_assign_callback(self):
        from speeddial import build_app
        platform = make_platform(pid=10, window_id=3, title="Chrome")
        appkit = make_appkit()
        app, listener = build_app(platform=platform, appkit=appkit, return_listener=True)
        # Simulate hotkey press: super+shift+1
        listener._handle_event(keycode=18, modifiers=listener._super | 0x00020000)
        from slot_registry import SlotRegistry
        # The assigned window should be in slot 1
        w = app._registry.get(1)
        assert w is not None
        assert w.pid == 10
        assert w.window_id == 3

    def test_build_app_wires_jump_callback(self):
        from speeddial import build_app
        platform = make_platform(pid=20, window_id=5, title="iTerm2")
        appkit = make_appkit()
        app, listener = build_app(platform=platform, appkit=appkit, return_listener=True)
        # Assign slot 2 via callback
        listener._handle_event(keycode=19, modifiers=listener._super | 0x00020000)
        # Jump to slot 2 via callback
        listener._handle_event(keycode=19, modifiers=listener._super)
        platform.activate_app.assert_called_with(20)
        platform.raise_window.assert_called_with(20, 5)

    def test_full_assign_jump_round_trip(self):
        from speeddial import build_app
        platform = make_platform(pid=99, window_id=11, title="Obsidian")
        appkit = make_appkit()
        app, listener = build_app(platform=platform, appkit=appkit, return_listener=True)
        # Assign slot 0
        listener._handle_event(keycode=29, modifiers=listener._super | 0x00020000)
        assert app._registry.get(0) is not None
        # Jump slot 0
        listener._handle_event(keycode=29, modifiers=listener._super)
        platform.raise_window.assert_called_once_with(99, 11)
