# Journal

Written by the coding session, read by the planning session. Newest first.

---

## 2026-08-30 — Rebuild and first publish (Cowork planning session)

Replaced the original draft entirely. It had been two separate programs — a
Tkinter window and a rumps menu bar script — and neither could grow into what
was wanted.

What was built: a single PyObjC app with a real drawn panel (large total,
goal bar, hoverable fourteen-day chart, document rows with hover and context
menus), projects, daily goals, and history. Counting rewritten to read OOXML
directly, dropping python-docx and picking up table text the old version
missed. Dependencies down to two: `pyobjc-framework-Cocoa` and `watchdog`.

Published to github.com/jzm8mpgm/tally, MIT, with a generated app icon,
README, contributing guide, PyInstaller spec and a release workflow.

CI is green: 37 unit tests on Linux, plus a macOS job that imports the whole
AppKit layer — added deliberately, because PyObjC validates selector
signatures at class-creation time, so that import catches a class of mistake
Linux never can. The app builds into a .app successfully.

**Not verified: the app has never actually been run.** See backlog item 1.

Known loose ends:
- `assets/hero.png` is a rendering, not a screenshot.
- The repo owner account has no display name set.
