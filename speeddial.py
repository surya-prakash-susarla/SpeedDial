"""
speeddial.py — entry point.

Wires all modules together and runs the NSApplication main loop.

Default super key: Option (MOD_OPTION = 0x00080000).
To change it, set the SPEEDDIAL_SUPER_MODS environment variable to a hex
integer representing the desired CGEventFlags modifier mask. For example:
  SPEEDDIAL_SUPER_MODS=0x00040000  # Control
  SPEEDDIAL_SUPER_MODS=0x001C0000  # Control+Option+Command
"""
import logging
import os
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stderr,
)

from hotkey_listener import HotkeyListener, MOD_OPTION
from slot_registry import SlotRegistry
from window_manager import WindowManager
from menu_bar import MenuBar
from app import SpeedDialApp


def _get_super_modifiers() -> int:
    raw = os.environ.get("SPEEDDIAL_SUPER_MODS", "")
    if raw:
        try:
            return int(raw, 16)
        except ValueError:
            print(f"[speeddial] Invalid SPEEDDIAL_SUPER_MODS value: {raw!r}, using Option")
    return MOD_OPTION


def build_app(platform=None, appkit=None, return_listener=False):
    """
    Construct and wire all components. Returns SpeedDialApp.
    If return_listener=True, returns (SpeedDialApp, HotkeyListener) — used in tests.
    """
    super_mods = _get_super_modifiers()

    registry = SlotRegistry()

    from window_manager import WindowManager
    wm = WindowManager(platform=platform)

    # Placeholder app so we can pass on_assign/on_jump to the listener
    # We build MenuBar first, then App, then close the loop via listener
    mb = MenuBar(registry=registry, appkit=appkit)

    speed_app = SpeedDialApp(
        registry=registry,
        window_manager=wm,
        menu_bar=mb,
    )

    listener = HotkeyListener(
        super_modifiers=super_mods,
        on_assign=speed_app.handle_assign,
        on_jump=speed_app.handle_jump,
    )

    if return_listener:
        return speed_app, listener
    return speed_app


def main():
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    speed_app, listener = build_app(return_listener=True)

    try:
        listener.start()
    except RuntimeError as e:
        print(f"[speeddial] Fatal: {e}", file=sys.stderr)
        sys.exit(1)

    speed_app._menu_bar.refresh()

    app.run()


if __name__ == "__main__":
    main()
