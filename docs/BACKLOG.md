# Backlog

Written by the planning session, read by the coding session. Newest concerns
first. When an item is done, move it to `## Done` with the date rather than
deleting it, so the reasoning survives.

---

## 1. Run the app and fix whatever first launch throws — blocking

Nothing else matters until this is done. The interface has been checked by CI
(it imports cleanly on a real Mac, which proves every PyObjC selector
signature is valid) but **it has never been on a screen**. Expect layout
imperfections and possibly a runtime error or two.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m tally
```

Worth checking specifically, because these are the parts I could not verify:

- Does the popover open at the right size, or is there dead space at the
  bottom? The height is computed in `panel.py::_layout` as a sum of constants.
- Does the sparkline hover work — moving across the bars should swap the
  subtitle line for that day's figure?
- Do document rows respond to a single click (open) and right-click (menu)?
- Does the menu bar number stay put as it changes, or does it jitter? It uses
  a monospaced-digit font, but the leading space may need tuning.
- Does the `⋯` button render? It uses the SF Symbol `ellipsis.circle` with a
  fallback to `NSActionTemplate`.
- Save a document in Word and time how long until the number moves. Should be
  under a second; the debounce is 0.35s in `engine.py`.

## 2. Replace the hero image with a real screenshot

`assets/hero.png` is a rendering of the design, not a photograph of the app.
It is honest as a mockup but it should not stay in the README once the real
thing exists. Shift-Cmd-4, then Space, then click the panel.

## 3. Verify the count against Word itself

Open a real manuscript in Word, note its count, and compare. A small gap is
expected and documented (Tally does not count punctuation-only tokens) but a
large one means the extraction is wrong. If they diverge badly, the place to
look is `counter.py::_docx_text` and which tags are treated as breaks.

## 4. Decide on the GitHub account

The repo is on `jzm8mpgm`, which has no display name and looks auto-generated.
If this is to be a public project with Matt's name on it, that should be
settled before it gets any attention.

## 5. Code signing and notarisation

Every new user currently meets "unidentified developer" and has to right-click
to open. An Apple Developer account (£79/year) removes that, and the signing
step slots into the existing release workflow. Worth it only if the app finds
an audience — revisit after it has been shared.

## Ideas, not yet committed to

- `.pages`, `.rtf` and `.odt` support
- Export the writing history as CSV
- Weekly goals as well as daily
- A "since I started this session" count, distinct from "today"
