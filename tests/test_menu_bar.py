"""
MenuBar wraps NSStatusItem and NSMenu.
AppKit objects are injected via a factory so tests never touch real AppKit.

The tested behavior:
  - Menu items are built from registry state on refresh()
  - Empty slots show the em-dash placeholder
  - Assigned slots show the window title
  - Slot numbers 0-9 all appear in order
  - A Quit item is always present at the bottom
  - refresh() replaces the previous items (not appended)

NSMenuItem is created via alloc().initWithTitle_action_keyEquivalent_() — the
correct pyobjc pattern. Tests assert on that call chain, not the bare constructor.
"""
import pytest
from unittest.mock import MagicMock, call
from window_info import WindowInfo
from slot_registry import SlotRegistry
from menu_bar import MenuBar


def make_appkit():
    """Return a mock AppKit namespace with controllable NSMenu/NSMenuItem/NSStatusBar."""
    ak = MagicMock()
    ak.NSVariableStatusItemLength = -1
    menu = MagicMock()
    status_item = MagicMock()
    status_bar = MagicMock()
    status_bar.statusItemWithLength_.return_value = status_item
    ak.NSStatusBar.systemStatusBar.return_value = status_bar
    ak.NSMenu.alloc.return_value.init.return_value = menu
    return ak, menu, status_item


def _init_call_titles(ak):
    """Extract the title argument from every initWithTitle_action_keyEquivalent_ call."""
    init_fn = ak.NSMenuItem.alloc.return_value.initWithTitle_action_keyEquivalent_
    return [c.args[0] for c in init_fn.call_args_list]


class TestMenuBarInit:
    def test_creates_status_item(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        ak.NSStatusBar.systemStatusBar.assert_called_once()

    def test_sets_status_item_title(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        assert (
            status_item.button.return_value.setTitle_.called
            or status_item.setTitle_.called
        )


class TestMenuBarRefreshEmptyRegistry:
    def test_refresh_creates_ten_slot_items_plus_quit(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        init_fn = ak.NSMenuItem.alloc.return_value.initWithTitle_action_keyEquivalent_
        # 10 slot items + 1 quit item = 11 initWithTitle calls
        assert init_fn.call_count == 11

    def test_empty_slots_use_dash_placeholder(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        titles = _init_call_titles(ak)
        dash_items = [t for t in titles if "\u2014" in t]
        assert len(dash_items) == 10

    def test_slot_numbers_zero_through_nine_appear_in_titles(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        titles = " ".join(_init_call_titles(ak))
        for slot in range(10):
            assert str(slot) in titles

    def test_quit_item_is_present(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        titles = _init_call_titles(ak)
        assert any("Quit" in t or "quit" in t for t in titles)

    def test_separator_item_is_added(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        ak.NSMenuItem.separatorItem.assert_called_once()


class TestMenuBarRefreshWithAssignments:
    def test_assigned_slot_shows_window_title(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        r.assign(3, WindowInfo(pid=1, window_id=1, title="iTerm2"))
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        titles = _init_call_titles(ak)
        assert any("iTerm2" in t for t in titles)

    def test_assigned_slot_does_not_show_dash(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        r.assign(3, WindowInfo(pid=1, window_id=1, title="iTerm2"))
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        titles = _init_call_titles(ak)
        slot3_titles = [t for t in titles if "[3]" in t]
        assert slot3_titles, "Expected at least one item referencing slot 3"
        assert not any("\u2014" in t for t in slot3_titles)

    def test_other_slots_still_show_dash(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        r.assign(0, WindowInfo(pid=1, window_id=1, title="Chrome"))
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        titles = _init_call_titles(ak)
        dash_items = [t for t in titles if "\u2014" in t]
        assert len(dash_items) == 9


class TestMenuBarRefreshReplacesPreviousItems:
    def test_second_refresh_does_not_double_items(self):
        ak, menu, status_item = make_appkit()
        r = SlotRegistry()
        mb = MenuBar(registry=r, appkit=ak)
        mb.refresh()
        init_fn = ak.NSMenuItem.alloc.return_value.initWithTitle_action_keyEquivalent_
        first_count = init_fn.call_count
        init_fn.reset_mock()
        menu.removeAllItems.reset_mock()
        mb.refresh()
        second_count = init_fn.call_count
        assert second_count == first_count
        menu.removeAllItems.assert_called()
