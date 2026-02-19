"""
HotkeyListener routes key events to on_assign / on_jump callbacks.

The listener's routing logic is tested by feeding synthetic events through
the _handle_event method directly — no real CGEventTap is created in tests.

Key codes for digits 0-9 on a US keyboard:
  0=29, 1=18, 2=19, 3=20, 4=21, 5=23, 6=22, 7=26, 8=28, 9=25
"""
import pytest
from unittest.mock import MagicMock, call
from hotkey_listener import HotkeyListener, DIGIT_KEY_CODES

# Modifier flag constants (mirrors Quartz values, defined in hotkey_listener)
from hotkey_listener import MOD_OPTION, MOD_SHIFT, MOD_CONTROL, MOD_COMMAND


def make_event(keycode, modifiers):
    """Synthetic event object matching what _handle_event receives."""
    ev = MagicMock()
    ev.getIntegerValueField_.side_effect = lambda field: {
        "keycode": keycode,
        "modifiers": modifiers,
    }.get(field, 0)
    return ev


def make_listener(super_mods=MOD_OPTION):
    on_assign = MagicMock()
    on_jump = MagicMock()
    listener = HotkeyListener(
        super_modifiers=super_mods,
        on_assign=on_assign,
        on_jump=on_jump,
    )
    return listener, on_assign, on_jump


class TestDigitKeyCodes:
    def test_digit_key_codes_has_ten_entries(self):
        assert len(DIGIT_KEY_CODES) == 10

    def test_digit_key_codes_covers_zero_through_nine(self):
        assert set(DIGIT_KEY_CODES.values()) == set(range(10))

    def test_digit_key_codes_all_positive_integers(self):
        for kc in DIGIT_KEY_CODES:
            assert isinstance(kc, int) and kc > 0


class TestHotkeyListenerJump:
    def test_super_plus_digit_fires_on_jump(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        for keycode, slot in DIGIT_KEY_CODES.items():
            on_jump.reset_mock()
            listener._handle_event(keycode=keycode, modifiers=MOD_OPTION)
            on_jump.assert_called_once_with(slot)

    def test_super_plus_digit_does_not_fire_on_assign(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        listener._handle_event(keycode=list(DIGIT_KEY_CODES)[0], modifiers=MOD_OPTION)
        on_assign.assert_not_called()

    def test_jump_fires_for_each_digit_zero_through_nine(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        slots_fired = []
        on_jump.side_effect = lambda s: slots_fired.append(s)
        for keycode in DIGIT_KEY_CODES:
            listener._handle_event(keycode=keycode, modifiers=MOD_OPTION)
        assert sorted(slots_fired) == list(range(10))


class TestHotkeyListenerAssign:
    def test_super_plus_shift_plus_digit_fires_on_assign(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        for keycode, slot in DIGIT_KEY_CODES.items():
            on_assign.reset_mock()
            listener._handle_event(keycode=keycode, modifiers=MOD_OPTION | MOD_SHIFT)
            on_assign.assert_called_once_with(slot)

    def test_super_plus_shift_does_not_fire_on_jump(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        listener._handle_event(
            keycode=list(DIGIT_KEY_CODES)[0],
            modifiers=MOD_OPTION | MOD_SHIFT,
        )
        on_jump.assert_not_called()

    def test_assign_fires_for_each_digit_zero_through_nine(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        slots_fired = []
        on_assign.side_effect = lambda s: slots_fired.append(s)
        for keycode in DIGIT_KEY_CODES:
            listener._handle_event(keycode=keycode, modifiers=MOD_OPTION | MOD_SHIFT)
        assert sorted(slots_fired) == list(range(10))


class TestHotkeyListenerIgnoresIrrelevantEvents:
    def test_wrong_modifier_only_does_nothing(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        keycode = list(DIGIT_KEY_CODES)[0]
        listener._handle_event(keycode=keycode, modifiers=MOD_CONTROL)
        on_jump.assert_not_called()
        on_assign.assert_not_called()

    def test_non_digit_keycode_with_super_does_nothing(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        non_digit_keycode = 0  # `a` key
        listener._handle_event(keycode=non_digit_keycode, modifiers=MOD_OPTION)
        on_jump.assert_not_called()
        on_assign.assert_not_called()

    def test_no_modifier_does_nothing(self):
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        keycode = list(DIGIT_KEY_CODES)[0]
        listener._handle_event(keycode=keycode, modifiers=0)
        on_jump.assert_not_called()
        on_assign.assert_not_called()

    def test_super_plus_extra_modifier_does_nothing(self):
        # Option+Cmd+digit should NOT fire — only exact super match
        listener, on_assign, on_jump = make_listener(super_mods=MOD_OPTION)
        keycode = list(DIGIT_KEY_CODES)[0]
        listener._handle_event(keycode=keycode, modifiers=MOD_OPTION | MOD_COMMAND)
        on_jump.assert_not_called()
        on_assign.assert_not_called()


class TestHotkeyListenerCustomSuperKey:
    def test_control_command_as_super_fires_jump(self):
        super_mods = MOD_CONTROL | MOD_COMMAND
        listener, on_assign, on_jump = make_listener(super_mods=super_mods)
        keycode = list(DIGIT_KEY_CODES)[0]
        listener._handle_event(keycode=keycode, modifiers=super_mods)
        on_jump.assert_called_once()

    def test_option_alone_does_not_fire_when_super_is_control_command(self):
        super_mods = MOD_CONTROL | MOD_COMMAND
        listener, on_assign, on_jump = make_listener(super_mods=super_mods)
        keycode = list(DIGIT_KEY_CODES)[0]
        listener._handle_event(keycode=keycode, modifiers=MOD_OPTION)
        on_jump.assert_not_called()
