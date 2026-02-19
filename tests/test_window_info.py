import pytest
from window_info import WindowInfo


class TestWindowInfoConstruction:
    def test_stores_pid(self):
        w = WindowInfo(pid=123, window_id=456, title="My Window")
        assert w.pid == 123

    def test_stores_window_id(self):
        w = WindowInfo(pid=123, window_id=456, title="My Window")
        assert w.window_id == 456

    def test_stores_title(self):
        w = WindowInfo(pid=123, window_id=456, title="My Window")
        assert w.title == "My Window"

    def test_title_can_be_empty_string(self):
        w = WindowInfo(pid=1, window_id=1, title="")
        assert w.title == ""

    def test_pid_zero_is_valid(self):
        w = WindowInfo(pid=0, window_id=0, title="root")
        assert w.pid == 0


class TestWindowInfoEquality:
    def test_equal_when_pid_and_window_id_match(self):
        a = WindowInfo(pid=1, window_id=2, title="A")
        b = WindowInfo(pid=1, window_id=2, title="A")
        assert a == b

    def test_equal_ignores_title_differences(self):
        a = WindowInfo(pid=1, window_id=2, title="Old Title")
        b = WindowInfo(pid=1, window_id=2, title="New Title")
        assert a == b

    def test_not_equal_when_pid_differs(self):
        a = WindowInfo(pid=1, window_id=2, title="Same")
        b = WindowInfo(pid=9, window_id=2, title="Same")
        assert a != b

    def test_not_equal_when_window_id_differs(self):
        a = WindowInfo(pid=1, window_id=2, title="Same")
        b = WindowInfo(pid=1, window_id=9, title="Same")
        assert a != b

    def test_not_equal_to_non_window_info(self):
        w = WindowInfo(pid=1, window_id=2, title="X")
        assert w != (1, 2)
        assert w != "not a window"
        assert w != None


class TestWindowInfoHashing:
    def test_can_be_used_as_dict_key(self):
        w = WindowInfo(pid=1, window_id=2, title="X")
        d = {w: "value"}
        assert d[w] == "value"

    def test_equal_windows_share_hash(self):
        a = WindowInfo(pid=1, window_id=2, title="Old")
        b = WindowInfo(pid=1, window_id=2, title="New")
        assert hash(a) == hash(b)

    def test_different_windows_have_different_hashes(self):
        a = WindowInfo(pid=1, window_id=2, title="X")
        b = WindowInfo(pid=3, window_id=4, title="X")
        assert hash(a) != hash(b)


class TestWindowInfoRepr:
    def test_repr_includes_pid_and_window_id_and_title(self):
        w = WindowInfo(pid=42, window_id=7, title="Terminal")
        r = repr(w)
        assert "42" in r
        assert "7" in r
        assert "Terminal" in r
