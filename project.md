# SpeedDial

## The Idea

Modern workflows on macOS involve rapidly switching between many applications and windows — terminals, browsers, editors, log viewers, chat tools. The built-in `Cmd+Tab` switcher is cyclic and app-level: it remembers only the last-used order, it cannot target a specific window of a specific app, and it requires multiple keypresses to reach anything beyond the last app. When your mental model has a spatial assignment — "Cursor on 1, terminal on 2, browser on 3" — the cyclic switcher is friction at every switch.

SpeedDial solves this with a numeric hotkey system, like the speed dial on a phone. You assign a window to a slot (0–9), and from that point on, a single chord teleports you directly to that window, regardless of what is currently focused, what space it is on, or whether it is behind other windows. There is no cycling. There is no hunting. There is just the number.

### How It Works

**Running:** SpeedDial runs as a macOS menu bar application. It has no dock icon. The only visible UI is an `NSStatusItem` in the menu bar showing the current state of all 10 slots. Clicking the item opens a dropdown showing each slot number and the title of the assigned window (or `—` if empty).

**Assigning a slot:** While any window is focused, press `<super> + Shift + <N>` where N is 0–9. SpeedDial detects the currently focused window using the macOS Accessibility API (`AXUIElement`), captures its process ID and window ID, and stores that mapping to slot N. If slot N was previously occupied, the old assignment is silently replaced.

**Jumping to a slot:** Press `<super> + <N>`. SpeedDial looks up the window stored in slot N, raises it to front, and activates its owning application. If the slot is empty, nothing happens. If the previously assigned window no longer exists (the app was closed), the slot is treated as empty and the jump is a no-op.

**Super key:** The super key combination is user-configurable. It is expressed as a set of macOS modifier flags (e.g., `Option`, `Control`, `Command`, or combinations thereof). The default and the exact key used is a runtime configuration — not hardcoded — so any user can bind it to their own hyper key or modifier chord.

**No persistence:** Slot assignments are in-memory only. On quit or reboot, all slots clear. There is no config file for assignments.

**Window closed:** If a window is closed after assignment, the slot silently becomes empty. The menu bar reflects this immediately — no error, no alert.

---

## Design Decisions

> **Rule:** Any major design decision made going forward must be logged here with a brief rationale.

### 1. Window-level targeting via CGWindowID + PID

We target individual windows, not applications. This is the entire point — two windows of the same app (e.g., two Cursor editors) must be independently assignable.

We identify a window by the pair `(pid, window_id)` where `window_id` is the `CGWindowID` obtained from `CGWindowListCopyWindowInfo`. This ID is stable within a session and unique system-wide. PID is included as a sanity check and to locate the owning process for activation.

Alternatives considered:
- AXUIElement reference: not reliably stable across focus changes.
- Window title alone: fragile — titles change (e.g., file name in editor title bar).
- Window index within app: fragile — window order shifts.

### 2. Global hotkey capture via CGEventTap

We use `CGEventTap` (from `pyobjc-framework-Quartz`) to intercept keydown events system-wide. This requires Accessibility permissions. We request them at launch and bail with a clear error if not granted.

Alternative (`NSEvent.addGlobalMonitorForEventsMatchingMask`) was rejected: it cannot consume events, only observe them — meaning the hotkey chord would also pass through to the active app.

### 3. Window activation via NSRunningApplication + AXUIElement

To bring a window forward: activate the owning app via `NSRunningApplication.activateWithOptions_`, then raise the specific window via `AXUIElementPerformAction_(kAXRaiseAction)` on its `AXUIElement`. This correctly handles apps in different Spaces.

### 4. pyobjc, no third-party abstractions (matching clock app)

We use raw pyobjc bindings (AppKit, Foundation, Quartz, ApplicationServices) directly, mirroring the clock app. No `rumps`, no wrappers. This keeps the dependency surface minimal and the code readable to anyone familiar with the clock codebase.

### 5. Menu bar renders slot state as plain text

Each slot is one line: `[N]  Window Title` or `[N]  —`. Updated on every assignment, every window-closed detection, and on menu open. No custom views. Simplest possible representation.

---

## Git Flow

Every piece of work follows this sequence without exception:

1. `git pull origin master` — start from a clean, up-to-date master.
2. `git checkout -b <descriptive-branch-name>` — all work happens on a branch, never directly on master.
3. Write tests for the module or behavior under development. Commit: `git commit -m "tests: <what is being tested>"`.
4. Write the implementation to make those tests pass. Commit: `git commit -m "feat|fix|refactor: <what changed>"`.
5. Run the full test suite. If anything fails, fix it and commit.
6. Open a PR. Merge to master. Delete the branch.
7. Repeat from step 1 for the next unit of work.

No direct pushes to master. No "just a small fix" shortcuts. No skipping the branch.

---

## Versioning

This project uses [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

- **PATCH** — bug fixes, internal corrections, no behavior change visible to the user. `build.sh` bumps this automatically.
- **MINOR** — new user-visible features, backwards compatible. Bump `VERSION` manually before running `build.sh`.
- **MAJOR** — breaking changes to behavior or configuration format. Bump `VERSION` manually before running `build.sh`.

Current version is always the single source of truth in the `VERSION` file at the root of the repository.

---

## Distribution

SpeedDial is distributed as a macOS `.app` bundle via Homebrew Cask, using the shared tap at `surya-prakash-susarla/homebrew-tap`.

### Files

| File | Purpose |
|------|---------|
| `VERSION` | Single source of truth for the current version |
| `build.sh` | Creates the `.app` bundle and zip via `py2app`, auto-bumps patch version |
| `release.sh` | Tags the release, creates a GitHub release, updates the cask formula |
| `setup.py` | `py2app` configuration — bundle metadata, entitlements |
| `install.sh` | curl-pipe installer for users who don't use Homebrew |
| `homebrew/speed-dial.rb` | Cask formula template (copy to `homebrew-tap/Casks/` on each release) |

### Release Workflow

```
bash build.sh          # bumps patch, builds SpeedDial.app, creates dist/SpeedDial.zip
bash release.sh        # tags, pushes, creates GitHub release, updates homebrew/speed-dial.rb
# then manually:
cp homebrew/speed-dial.rb ../homebrew-tap/Casks/speed-dial.rb
cd ../homebrew-tap && git add . && git commit -m "Update speed-dial to vX.Y.Z" && git push
```

### Required Permissions at Runtime

SpeedDial requires **Accessibility** permissions (System Settings → Privacy & Security → Accessibility). These are needed for both `CGEventTap` (global hotkey capture) and `AXUIElement` (window focus/raise). The app prompts the user on first launch and exits cleanly if permission is denied.

---

## Coding Commandments

These are non-negotiable rules for every line of code written in this repository.

1. **Test-driven, always.** No module is written before its tests exist. Every module begins with a complete test suite expressing the expected behavior. Only then is the implementation written to make those tests pass. This order is never reversed.

2. **Red before green.** Tests are written to fail first. If a test passes before the implementation exists, the test is wrong. Fix the test, not the assumption.

3. **Tests are truth.** Tests are never modified to match observed behavior. If the implementation produces something different from what the test expects, the implementation is wrong. Adjust code, never tests — except to correct an error in the test's own logic, which must be explicitly justified.

4. **Small, single-responsibility modules.** Each module does one thing. A module that needs a paragraph to describe what it does is too large. Split it.

5. **Coverage at every level.** Unit tests cover individual modules in isolation (dependencies mocked). Integration tests cover the interaction between modules. Both layers must exist. Neither substitutes for the other.

6. **No test is decorative.** Every test must be capable of catching a real defect. Tests that always pass regardless of implementation are deleted, not kept.

7. **No implementation leaks into tests.** Tests assert on behavior and outcomes, not on internal state, private methods, or implementation details that could validly change.
