# Journal

Written by the coding session, read by the planning session. Newest first.

---

## 2026-08-30 — First run on a real Mac; popover sizing fixed; 2wish added

Matt ran it. The menu bar count works. One real bug: the popover kept the
content size it had when first shown — the empty state, before any documents
were added — so once documents arrived the panel was about 125pt too short and
the header, the total and the subtitle were clipped off the top edge.

`setPreferredContentSize_` alone does not move an NSPopover that has already
been displayed. The fix is for the panel to hold a reference to its popover and
set `contentSize` directly at the end of `_layout`. See
`panel.py::attach_popover`.

Also added donation routing to 2wish rather than to the author: a `⋯ → Support
2wish…` menu item, a button in the About box, `.github/FUNDING.yml` for the
repo's Sponsor button, and a README section. Attribution is carried two ways —
UTM tags on the URL for 2wish's analytics, and a prompt asking donors to write
"Tally" in the donation form's message box, which is what actually reaches a
human.

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
