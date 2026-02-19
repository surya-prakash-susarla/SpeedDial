"""
SpeedDialApp — controller that wires SlotRegistry, WindowManager, and MenuBar.

All dependencies are injected. Tests verify:
  - handle_assign: gets focused window, assigns to slot, refreshes menu
  - handle_jump: looks up slot, raises window, clears slot if window gone, refreshes
  - Edge cases: empty slot jump, no focused window on assign, already-dead window on jump
"""
import pytest
from unittest.mock import MagicMock, call
from window_info import WindowInfo
from slot_registry import SlotRegistry
from app import SpeedDialApp


def make_window(pid=1, window_id=1, title="Window"):
    return WindowInfo(pid=pid, window_id=window_id, title=title)


def make_app(focused_window=None, raise_result=True, alive=True):
    registry = SlotRegistry()
    window_manager = MagicMock()
    window_manager.get_focused_window.return_value = focused_window
    window_manager.raise_window.return_value = raise_result
    window_manager.is_window_alive.return_value = alive
    menu_bar = MagicMock()
    app = SpeedDialApp(
        registry=registry,
        window_manager=window_manager,
        menu_bar=menu_bar,
    )
    return app, registry, window_manager, menu_bar


class TestHandleAssign:
    def test_assigns_focused_window_to_slot(self):
        w = make_window(title="iTerm2")
        app, registry, wm, mb = make_app(focused_window=w)
        app.handle_assign(3)
        assert registry.get(3) == w

    def test_refreshes_menu_after_assign(self):
        w = make_window()
        app, registry, wm, mb = make_app(focused_window=w)
        app.handle_assign(0)
        mb.refresh.assert_called_once()

    def test_does_nothing_when_no_focused_window(self):
        app, registry, wm, mb = make_app(focused_window=None)
        app.handle_assign(5)
        assert registry.get(5) is None
        mb.refresh.assert_not_called()

    def test_replaces_existing_assignment(self):
        old = make_window(pid=1, window_id=1, title="Old")
        new = make_window(pid=2, window_id=2, title="New")
        app, registry, wm, mb = make_app(focused_window=new)
        registry.assign(4, old)
        app.handle_assign(4)
        assert registry.get(4) == new

    def test_queries_focused_window_from_window_manager(self):
        w = make_window()
        app, registry, wm, mb = make_app(focused_window=w)
        app.handle_assign(1)
        wm.get_focused_window.assert_called_once()

    def test_all_slots_assignable(self):
        for slot in range(10):
            w = make_window(pid=slot + 1, window_id=slot + 1, title=f"App{slot}")
            app, registry, wm, mb = make_app(focused_window=w)
            app.handle_assign(slot)
            assert registry.get(slot) == w


class TestHandleJump:
    def test_raises_window_for_assigned_slot(self):
        w = make_window()
        app, registry, wm, mb = make_app(raise_result=True)
        registry.assign(2, w)
        app.handle_jump(2)
        wm.raise_window.assert_called_once_with(w)

    def test_does_nothing_for_empty_slot(self):
        app, registry, wm, mb = make_app()
        app.handle_jump(7)
        wm.raise_window.assert_not_called()
        mb.refresh.assert_not_called()

    def test_clears_slot_when_raise_returns_false(self):
        w = make_window()
        app, registry, wm, mb = make_app(raise_result=False)
        registry.assign(1, w)
        app.handle_jump(1)
        assert registry.get(1) is None

    def test_refreshes_menu_when_slot_cleared_after_failed_raise(self):
        w = make_window()
        app, registry, wm, mb = make_app(raise_result=False)
        registry.assign(1, w)
        app.handle_jump(1)
        mb.refresh.assert_called_once()

    def test_does_not_refresh_menu_on_successful_jump(self):
        w = make_window()
        app, registry, wm, mb = make_app(raise_result=True)
        registry.assign(1, w)
        app.handle_jump(1)
        mb.refresh.assert_not_called()

    def test_does_not_clear_slot_on_successful_jump(self):
        w = make_window()
        app, registry, wm, mb = make_app(raise_result=True)
        registry.assign(6, w)
        app.handle_jump(6)
        assert registry.get(6) == w

    def test_does_not_call_raise_for_empty_slot(self):
        app, registry, wm, mb = make_app()
        app.handle_jump(3)
        wm.raise_window.assert_not_called()


class TestHandleAssignAndJumpIntegration:
    def test_assign_then_jump_reaches_correct_window(self):
        w = make_window(pid=42, window_id=99, title="Slack")
        app, registry, wm, mb = make_app(focused_window=w, raise_result=True)
        app.handle_assign(5)
        app.handle_jump(5)
        wm.raise_window.assert_called_once_with(w)

    def test_reassign_then_jump_uses_new_window(self):
        old = make_window(pid=1, window_id=1, title="Old")
        new = make_window(pid=2, window_id=2, title="New")
        app, registry, wm, mb = make_app(raise_result=True)
        registry.assign(0, old)
        wm.get_focused_window.return_value = new
        app.handle_assign(0)
        app.handle_jump(0)
        wm.raise_window.assert_called_once_with(new)
