import pytest
from window_info import WindowInfo
from slot_registry import SlotRegistry


def make_window(pid=1, window_id=1, title="Window"):
    return WindowInfo(pid=pid, window_id=window_id, title=title)


class TestSlotRegistryInitialState:
    def test_all_slots_empty_at_start(self):
        r = SlotRegistry()
        for slot in range(10):
            assert r.get(slot) is None

    def test_has_exactly_ten_slots(self):
        r = SlotRegistry()
        state = r.all_slots()
        assert len(state) == 10

    def test_all_slots_keys_are_zero_through_nine(self):
        r = SlotRegistry()
        assert set(r.all_slots().keys()) == set(range(10))


class TestSlotRegistryAssign:
    def test_assign_stores_window_in_slot(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(3, w)
        assert r.get(3) == w

    def test_assign_replaces_existing_window(self):
        r = SlotRegistry()
        old = make_window(pid=1, window_id=1, title="Old")
        new = make_window(pid=2, window_id=2, title="New")
        r.assign(5, old)
        r.assign(5, new)
        assert r.get(5) == new

    def test_assign_does_not_affect_other_slots(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(0, w)
        for slot in range(1, 10):
            assert r.get(slot) is None

    def test_assign_slot_zero(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(0, w)
        assert r.get(0) == w

    def test_assign_slot_nine(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(9, w)
        assert r.get(9) == w

    def test_assign_invalid_slot_raises(self):
        r = SlotRegistry()
        w = make_window()
        with pytest.raises(ValueError):
            r.assign(10, w)

    def test_assign_negative_slot_raises(self):
        r = SlotRegistry()
        w = make_window()
        with pytest.raises(ValueError):
            r.assign(-1, w)


class TestSlotRegistryGet:
    def test_get_empty_slot_returns_none(self):
        r = SlotRegistry()
        assert r.get(4) is None

    def test_get_invalid_slot_raises(self):
        r = SlotRegistry()
        with pytest.raises(ValueError):
            r.get(10)

    def test_get_negative_slot_raises(self):
        r = SlotRegistry()
        with pytest.raises(ValueError):
            r.get(-1)


class TestSlotRegistryClear:
    def test_clear_removes_assigned_window(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(2, w)
        r.clear(2)
        assert r.get(2) is None

    def test_clear_empty_slot_is_no_op(self):
        r = SlotRegistry()
        r.clear(2)  # should not raise
        assert r.get(2) is None

    def test_clear_does_not_affect_other_slots(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(1, w)
        r.assign(2, w)
        r.clear(1)
        assert r.get(2) == w

    def test_clear_invalid_slot_raises(self):
        r = SlotRegistry()
        with pytest.raises(ValueError):
            r.clear(10)


class TestSlotRegistryAllSlots:
    def test_all_slots_reflects_assignments(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(3, w)
        state = r.all_slots()
        assert state[3] == w

    def test_all_slots_empty_slots_are_none(self):
        r = SlotRegistry()
        r.assign(0, make_window())
        state = r.all_slots()
        for slot in range(1, 10):
            assert state[slot] is None

    def test_all_slots_returns_copy_not_internal_state(self):
        r = SlotRegistry()
        w = make_window()
        r.assign(1, w)
        state = r.all_slots()
        state[1] = None  # mutate the returned copy
        assert r.get(1) == w  # registry unaffected
