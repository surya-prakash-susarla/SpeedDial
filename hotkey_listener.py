"""
HotkeyListener — captures global key events via CGEventTap and routes them
to on_assign / on_jump callbacks.

Modifier constants match Quartz CGEventFlags values (masked to the bits we care about).
The routing logic (_handle_event) is pure Python and fully testable without a real event tap.
"""
import logging
from typing import Callable

log = logging.getLogger(__name__)

# Modifier flag masks (CGEventFlags, lower 32 bits)
MOD_SHIFT   = 0x00020000
MOD_CONTROL = 0x00040000
MOD_OPTION  = 0x00080000
MOD_COMMAND = 0x00100000

# Mask covering only the four modifiers we care about
_MOD_MASK = MOD_SHIFT | MOD_CONTROL | MOD_OPTION | MOD_COMMAND

# US keyboard key codes for digit keys 0-9
# (kVK_* constants from Carbon/Events.h)
DIGIT_KEY_CODES: dict[int, int] = {
    18: 1,
    19: 2,
    20: 3,
    21: 4,
    23: 5,
    22: 6,
    26: 7,
    28: 8,
    25: 9,
    29: 0,
}


class HotkeyListener:
    def __init__(
        self,
        super_modifiers: int,
        on_assign: Callable[[int], None],
        on_jump: Callable[[int], None],
    ):
        self._super = super_modifiers
        self._on_assign = on_assign
        self._on_jump = on_jump
        self._tap = None

    # ------------------------------------------------------------------
    # Routing logic — pure, testable, no macOS deps
    # ------------------------------------------------------------------

    def _handle_event(self, keycode: int, modifiers: int) -> bool:
        """
        Process a key event. Returns True if the event was consumed (hotkey matched).
        modifiers is already masked to _MOD_MASK before this is called.
        """
        masked = modifiers & _MOD_MASK
        slot = DIGIT_KEY_CODES.get(keycode)
        if slot is None:
            return False

        jump_mods = self._super & _MOD_MASK
        assign_mods = (self._super | MOD_SHIFT) & _MOD_MASK

        if masked == assign_mods:
            log.debug("assign slot %d", slot)
            self._on_assign(slot)
            return True
        if masked == jump_mods:
            log.debug("jump slot %d", slot)
            self._on_jump(slot)
            return True
        return False

    # ------------------------------------------------------------------
    # CGEventTap lifecycle — macOS-only, not unit-tested
    # ------------------------------------------------------------------

    def start(self) -> None:
        import Quartz

        def _callback(proxy, event_type, event, refcon):
            if event_type != Quartz.kCGEventKeyDown:
                return event
            try:
                keycode = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventKeycode
                )
                modifiers = Quartz.CGEventGetFlags(event)
                consumed = self._handle_event(keycode=keycode, modifiers=modifiers)
                return None if consumed else event
            except Exception:
                log.exception("error in hotkey callback")
                return event

        self._callback_ref = _callback  # keep alive
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
            _callback,
            None,
        )
        if self._tap is None:
            raise RuntimeError(
                "Could not create CGEventTap. "
                "Grant Accessibility access in System Settings → Privacy & Security → Accessibility."
            )
        loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            loop_source,
            Quartz.kCFRunLoopCommonModes,
        )
        Quartz.CGEventTapEnable(self._tap, True)
        log.info("hotkey listener started (super=0x%08x)", self._super)

    def stop(self) -> None:
        if self._tap is not None:
            import Quartz
            Quartz.CGEventTapEnable(self._tap, False)
            self._tap = None
            log.info("hotkey listener stopped")
