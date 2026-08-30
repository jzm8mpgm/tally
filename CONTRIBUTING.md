# Contributing to Tally

Thank you for looking. Tally is a small app with a deliberately small scope,
and contributions of every size are welcome — a typo fix is a contribution.

## Getting set up

```bash
git clone https://github.com/jzm8mpgm/tally.git
cd tally
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m tally
```

Running `python3 -m tally` gives you the app straight from source, with the
menu bar icon and everything else. Quit it from the ⋯ menu.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

The counting engine, the project store and the scanning engine are all pure
Python and fully tested — they run on any platform, including CI. The AppKit
layer is not unit tested; changes there need checking by hand on a Mac.

If you change how counting works, please add a case to `tests/test_counter.py`.
Word documents for tests are built inline by `make_docx()`, so no binary
fixtures are needed.

## Code shape

- `tally/counter.py` — reads documents, counts words. No AppKit.
- `tally/store.py` — projects, goals, daily history, persistence. No AppKit.
- `tally/engine.py` — ties those together, watches the filesystem. No AppKit.
- `tally/theme.py` — fonts, colours, spacing.
- `tally/views.py` — custom AppKit views.
- `tally/panel.py` — the popover's layout.
- `tally/app.py` — the status item, menus and application delegate.

Keeping the first three free of AppKit is the rule worth preserving: it is what
makes the logic testable.

Colours come from AppKit's semantic colours (`labelColor`, `controlAccentColor`
and friends) so that light mode, dark mode, increased contrast and the user's
chosen accent colour all work without special cases. Please don't hard-code a
colour value.

## Ideas that would be welcome

- Support for `.pages`, `.rtf` and `.odt`
- An export of the writing history as CSV
- A weekly, rather than daily, goal
- Localisation
- Code signing and notarisation in the release workflow

## Ideas that are probably out of scope

Tally is a counter. It is not an editor, a backup tool, a sync service or a
place to store your manuscript. Anything that needs a network connection is
almost certainly the wrong shape for this app.

## Pull requests

Small and focused is easier to review than large and sweeping. Please describe
what the change does and, if it touches the interface, say which macOS version
you tried it on.
