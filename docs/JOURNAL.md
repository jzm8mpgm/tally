# Journal

What changed and why, newest first. Shorter than a commit log and longer than
a changelog: this is the place for reasoning that would otherwise be lost.

---

## 2026-08-30 — First run, and three bugs

Tally ran on a real Mac for the first time and immediately produced three
faults, none of which any amount of static checking would have found.

**The popover clipped its own header.** `NSPopover` keeps the content size it
had when first shown, and `setPreferredContentSize_` does not reliably move it
afterwards. Launching with no documents laid out the short empty state; once
documents were added the panel grew to around 490pt while the popover stayed
at roughly 360, cutting the project name, the total and the subtitle off the
top edge. The panel now holds a reference to its popover and sets
`contentSize` directly at the end of `_layout`.

**The ellipsis button was invisible.** It was an SF Symbol *template* image
drawn by hand with `drawInRect_`. Template images are only tinted when AppKit
hosts them inside a control; drawn directly they render as literal black,
which on a dark popover is nothing at all. It is now three drawn circles
taking their colour from the semantic palette, which cannot fail in either
appearance.

**Ctrl-C would not quit it.** A Python signal handler only runs between
bytecode instructions, and while the AppKit event loop holds control the
interpreter is executing none — so `^C` echoed and nothing happened. The
handler now raises a flag and the one-second heartbeat, being the next Python
code to run, quits on it. SIGTERM is handled the same way.

Also added: support routing to 2Wish rather than to the author — a menu item,
a button in the About box, `.github/FUNDING.yml`, and a README section.
Attribution rides on UTM tags for 2Wish's analytics and, more usefully, on a
prompt asking donors to write "Tally" in the donation form's message box.

## 2026-08-30 — Rebuild and first publish

Replaced the original draft entirely. It had been two separate programs — a
Tkinter window and a rumps menu bar script — and neither could grow into what
was wanted.

Built: a single PyObjC app with a drawn panel (large total, goal bar,
hoverable fourteen-day chart, document rows with hover and context menus),
projects, daily goals and history. Counting rewritten to read OOXML directly,
dropping python-docx and picking up table text the old version missed.
Dependencies down to two.

CI runs 37 unit tests on Linux, then on a macOS runner imports the whole
AppKit layer before building the app. That import step is deliberate: PyObjC
validates selector signatures when a class is created, so importing these
modules is the cheapest way to catch a selector-arity mistake. It cannot,
as the entry above shows, catch anything about how the app looks.
