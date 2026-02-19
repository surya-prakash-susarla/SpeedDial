from typing import Optional
from window_info import WindowInfo

_VALID_SLOTS = range(10)


def _validate_slot(slot: int) -> None:
    if slot not in _VALID_SLOTS:
        raise ValueError(f"Slot must be 0–9, got {slot}")


class SlotRegistry:
    def __init__(self):
        self._slots: dict[int, Optional[WindowInfo]] = {i: None for i in _VALID_SLOTS}

    def assign(self, slot: int, window: WindowInfo) -> None:
        _validate_slot(slot)
        self._slots[slot] = window

    def get(self, slot: int) -> Optional[WindowInfo]:
        _validate_slot(slot)
        return self._slots[slot]

    def clear(self, slot: int) -> None:
        _validate_slot(slot)
        self._slots[slot] = None

    def all_slots(self) -> dict[int, Optional[WindowInfo]]:
        return dict(self._slots)
