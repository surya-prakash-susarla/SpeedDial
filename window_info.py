from dataclasses import dataclass


@dataclass
class WindowInfo:
    pid: int
    window_id: int
    title: str

    def __eq__(self, other):
        if not isinstance(other, WindowInfo):
            return NotImplemented
        return self.pid == other.pid and self.window_id == other.window_id

    def __hash__(self):
        return hash((self.pid, self.window_id))

    def __repr__(self):
        return f"WindowInfo(pid={self.pid}, window_id={self.window_id}, title={self.title!r})"
