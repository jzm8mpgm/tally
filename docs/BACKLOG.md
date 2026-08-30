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

## 2. A real screenshot

`assets/hero.png` is a rendering of the interface, not a photograph of it. It
is accurate, but it should be replaced by the real thing.

## 3. Check the count against Word itself

Open a real manuscript in Word, note its figure, and compare. A small gap is
expected and documented — Tally does not count punctuation-only tokens — but a
large one would mean the extraction is wrong. The place to look is
`counter.py::_docx_text`, and specifically which tags are treated as breaks.

## 4. A dedicated fundraising page for 2wish

Donations currently go to 2wish's general form, and attribution depends on
someone typing "Tally" into the message box, which most people will not do. A
fundraising page created for Tally would give a real running total and
something worth linking to. Needs an account, so it is a decision rather than
a task.

## 5. Code signing and notarisation

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

**2026-08-30 — the first three bugs.** The popover clipped its own header; the
ellipsis button was invisible; Ctrl-C would not quit it. All three are the kind
that only appear when a person actually runs the thing. See the journal.
