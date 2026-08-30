# Decisions

Things settled, with the reasoning, so they are not relitigated by accident.
If a decision turns out to be wrong, add a new entry superseding the old one
rather than editing history.

---

**Read .docx directly rather than via python-docx.**
A .docx is a zip of XML. Reading it with `zipfile` + `ElementTree` is an order
of magnitude faster, removes a dependency, and picks up text in tables, text
boxes and content controls that a paragraph-only reader misses. The cost is
that we own the extraction logic, including which tags count as whitespace.

**`counter.py`, `store.py` and `engine.py` never import AppKit.**
It is what allows the logic to be tested on Linux, which is what allows CI to
run tests on every push without a Mac runner. Protect it.

**Manual frame layout, not Auto Layout.**
The panel is a fixed width and its height is a straightforward sum of its
parts. Arithmetic is easier to read and to change than constraints, and there
is nothing to fight when a section appears or disappears.

**Colours come only from AppKit semantic colours.**
Light mode, dark mode, increased contrast and the user's accent colour then
work with no special-casing at all.

**"Today" is measured from a baseline captured at the first count of each day.**
Adding a document shifts that baseline by the same amount
(`store.py::shift_baseline`), so importing a finished manuscript reads as zero
words written rather than a heroic morning. This matters more than it sounds:
without it the headline number is a lie on any day you reorganise your files.

**Punctuation-only tokens are not words.**
A lone em dash marking a scene break, or a row of asterisks, is not prose.
This puts Tally a word or two below Word on heavily formatted documents. The
trade was made deliberately and is documented in the README.

**A LaunchAgent, not SMAppService, for opening at login.**
SMAppService needs a framework outside `pyobjc-framework-Cocoa` and only works
for a signed bundle. The LaunchAgent works identically from source and from a
built app, with no extra dependency.
