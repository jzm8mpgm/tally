# Backlog

What is wanted next, and why. Roughly in priority order. When something is
done it moves to the bottom rather than being deleted, so the reasoning
survives.

If you are looking for somewhere to help, anything here is fair game — say so
in an issue first so two people don't do the same work.

---

## 1. First-launch polish

The app runs. Three bugs from the very first launch are fixed (see Done), but
it has only been run by one person on one Mac, so the shallow end is not yet
well explored. Worth checking, and worth an issue if any of it is wrong:

- The panel's height is a sum of constants in `panel.py::_layout`. Does it
  still fit correctly with one document? With forty? With a very long
  filename?
- Hovering a bar in the chart should replace the subtitle with that day's
  figure, and restore it on the way out.
- A single click on a row opens the document; right-click offers Reveal in
  Finder and Remove.
- The menu bar figure uses a monospaced-digit font so it should not jitter as
  the number changes.
- Light mode. Everything so far has been looked at in dark mode.
- Increased-contrast and reduce-transparency accessibility settings.

## 2. A dedicated fundraising page for 2wish

Donations currently go to 2wish's general form, and attribution depends on
someone typing "Tally" into the message box, which most people will not do. A
fundraising page created for Tally would give a real running total and
something worth linking to. Needs an account, so it is a decision rather than
a task.

## 3. Code signing and notarisation

Every new user currently meets "unidentified developer" and has to right-click
to open. An Apple Developer account removes that, and the signing step slots
into the existing release workflow. Worth doing only once the app has an
audience.

## Ideas, not committed to

- `.pages`, `.rtf` and `.odt`
- Export the writing history as CSV
- Weekly goals as well as daily
- A "since I sat down" count, distinct from "today"
- Localisation

---

## Done

**2026-09-10 — a real screenshot.** `assets/hero.png` is now a photograph of
the running app rather than a rendering.

**2026-09-10 — count checked against Word.** Compared Tally's figure against
Word's own count on a real manuscript; the gap is the expected, documented
one (punctuation-only tokens), not an extraction bug.

**2026-08-30 — the first three bugs.** The popover clipped its own header; the
ellipsis button was invisible; Ctrl-C would not quit it. All three are the kind
that only appear when a person actually runs the thing. See the journal.
