# Tally — working notes for Claude

A macOS menu bar app that keeps a live word count of a chosen set of Word
documents. Python, PyObjC, no interface builder, no storyboards.

## Two sessions work on this project

- **Planning** happens in a Cowork session. It writes to `docs/BACKLOG.md`.
- **Coding** happens in Claude Code (this session). It writes to `docs/JOURNAL.md`.

They share nothing but this repository, so the protocol is:

1. `git pull` before starting work.
2. Read `docs/BACKLOG.md` for what is wanted and why.
3. Do the work.
4. Append a dated entry to `docs/JOURNAL.md` — what changed, what you decided
   and why, and anything the planning session needs to answer.
5. Commit and push, so the other session can see it.

Architectural decisions that outlive a single task go in `docs/DECISIONS.md`.
If you are about to contradict one, say so explicitly rather than quietly.

**These files are public.** Write them for a stranger who has just found the
repository, not as notes between two sessions. Nothing about accounts,
credentials or private decisions goes in them.

## Architecture

| File | Responsibility |
|---|---|
| `tally/counter.py` | Reads documents, counts words. **No AppKit.** |
| `tally/store.py` | Projects, goals, daily history, persistence. **No AppKit.** |
| `tally/engine.py` | Ties those together, watches the filesystem. **No AppKit.** |
| `tally/theme.py` | Fonts, colours, spacing. |
| `tally/views.py` | Custom AppKit views (all drawing lives here). |
| `tally/panel.py` | The popover's layout. |
| `tally/app.py` | Status item, menus, application delegate. |

**The rule worth protecting:** the first three files never import AppKit. That
is what makes the logic testable on any machine, including CI. Do not reach for
an AppKit type in `counter`, `store` or `engine` — pass a plain value instead.

## PyObjC conventions

This trips people up, so it is written down:

- A method PyObjC exposes to Objective-C has its underscores turned into
  colons. `setDocument_delegate_` becomes `setDocument:delegate:`, and the
  number of underscores **must** equal the number of arguments.
- Any helper that only Python calls must be decorated `@objc.python_method`.
  Without it, a method like `_rebuild_rows(self, documents)` is read as a
  selector, the arity does not match, and the class fails to build **at import
  time**.
- Use `objc.super(Class, self)`, not bare `super()`.
- Views that respond to clicks need `mouseDown_` (even empty) so that
  `mouseUp_` is delivered rather than passed up the responder chain, plus
  `acceptsFirstMouse_` returning True — the popover is often not key.

CI imports the whole AppKit layer on a macOS runner precisely to catch the
first two mistakes. If that step goes red, this section is why.

## Colours

Every colour comes from an AppKit semantic colour (`labelColor`,
`controlAccentColor`, `separatorColor`, …) via `tally/theme.py`. That is what
makes light mode, dark mode, increased contrast and the user's chosen accent
colour work without any special-casing. **Never hard-code a colour value.**

## Commands

```bash
python3 -m tally                                  # run from source
python3 -m unittest discover -s tests -t .        # tests (no Mac needed)
python3 tools/make_icon.py                        # redraw assets/Tally.icns
./build.sh                                        # build dist/Tally.app
./build.sh --zip                                  # …and a release zip
```

## Releasing

Push a tag (`git tag v1.0.1 && git push --tags`). The workflow builds the app
on a macOS runner and attaches `Tally.zip` to the release.

## Scope

Tally is a counter. Not an editor, not a backup tool, not a sync service.
Anything needing a network connection is almost certainly the wrong shape.
