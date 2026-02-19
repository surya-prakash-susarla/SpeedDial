"""
MenuBar — NSStatusItem living in the macOS menu bar.

Renders the 10 speed-dial slots as menu items.
Each slot shows:  [N]  Window Title   or   [N]  —   if empty.

All AppKit types are injected via `appkit` for testability.
In production, pass appkit=None and the real AppKit is imported.
"""
from slot_registry import SlotRegistry

_EMPTY = "\u2014"  # em dash


def _real_appkit():
    from AppKit import (
        NSMenu,
        NSMenuItem,
        NSStatusBar,
        NSVariableStatusItemLength,
    )

    class _AK:
        NSMenu = NSMenu
        NSMenuItem = NSMenuItem
        NSStatusBar = NSStatusBar
        NSVariableStatusItemLength = NSVariableStatusItemLength

    return _AK()


class MenuBar:
    def __init__(self, registry: SlotRegistry, appkit=None, on_quit=None):
        self._registry = registry
        self._ak = appkit if appkit is not None else _real_appkit()
        self._on_quit = on_quit
        self._status_item = (
            self._ak.NSStatusBar.systemStatusBar()
            .statusItemWithLength_(self._ak.NSVariableStatusItemLength)
        )
        try:
            self._status_item.button().setTitle_("⌨")
        except Exception:
            self._status_item.setTitle_("⌨")
        self._menu = self._ak.NSMenu()
        self._status_item.setMenu_(self._menu)

    def refresh(self) -> None:
        """Rebuild the menu from current registry state."""
        self._menu.removeAllItems()
        slots = self._registry.all_slots()
        for slot in range(10):
            window = slots[slot]
            title = window.title if window is not None else _EMPTY
            label = f"[{slot}]  {title}"
            item = self._ak.NSMenuItem(label, "", "")
            item.setEnabled_(False)  # slots are display-only
            self._menu.addItem_(item)

        self._menu.addItem_(self._ak.NSMenuItem("", "", ""))  # separator
        quit_item = self._ak.NSMenuItem("Quit SpeedDial", "terminate:", "q")
        self._menu.addItem_(quit_item)
