"""The panel that drops out of the menu bar.

Laid out by hand rather than by Auto Layout: the panel is a fixed width and
its height is a straightforward sum of its parts, so arithmetic is clearer
than constraints and there is nothing to fight when a section appears or
disappears.
"""

from __future__ import annotations

import objc
from AppKit import (
    NSControlSizeSmall,
    NSImage,
    NSLeftTextAlignment,
    NSNoBorder,
    NSRightTextAlignment,
    NSScrollerStyleOverlay,
    NSScrollView,
    NSViewController,
)
from Foundation import NSMakeRect, NSMakeSize

from . import theme
from .theme import PAD, PANEL_WIDTH, ROW_HEIGHT
from .views import (
    Caption,
    DocumentRow,
    EmptyState,
    FlippedView,
    IconButton,
    PillButton,
    ProgressBar,
    Rule,
    Sparkline,
    friendly_day,
    make_label,
)

HEADER_HEIGHT = 24
TOTAL_HEIGHT = 46
SUBTITLE_HEIGHT = 17
GOAL_ROW_HEIGHT = 16
CAPTION_HEIGHT = 14
FOOTER_HEIGHT = 26
EMPTY_HEIGHT = 52


def _symbol(name: str, fallback: str = ""):
    """An SF Symbol image, or a stock one on systems that lack it."""
    image = None
    if hasattr(NSImage, "imageWithSystemSymbolName_accessibilityDescription_"):
        try:
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                name, None
            )
        except Exception:
            image = None
    if image is None and fallback:
        image = NSImage.imageNamed_(fallback)
    if image is not None:
        image.setTemplate_(True)
        image.setSize_(NSMakeSize(14, 14))
    return image


class PanelController(NSViewController):
    """Owns the popover's content view and keeps it in step with the engine."""

    # ── construction ─────────────────────────────────────────────────

    def initWithApp_(self, app):  # noqa: N802
        self = objc.super(PanelController, self).initWithNibName_bundle_(None, None)
        if self is None:
            return None
        self._app = app
        self._popover = None
        self._rows = []
        self._row_paths = []
        self._subtitle_text = ""
        return self

    @objc.python_method
    def attach_popover(self, popover):
        """The panel resizes its own popover.

        NSPopover latches onto whatever content size it had when it was first
        shown; ``preferredContentSize`` alone does not reliably move it
        afterwards. Setting ``contentSize`` directly does.
        """
        self._popover = popover

    def loadView(self):  # noqa: N802
        width = PANEL_WIDTH
        inner = width - PAD * 2
        root = FlippedView.alloc().initWithFrame_(NSMakeRect(0, 0, width, 480))

        self._project_button = PillButton.alloc().initWithFrame_(
            NSMakeRect(PAD - 8, 0, inner - 30, HEADER_HEIGHT)
        )
        self._project_button.set_alignment(NSLeftTextAlignment)
        self._project_button.set_tint(theme.primary())
        root.addSubview_(self._project_button)

        self._more = IconButton.alloc().initWithFrame_(
            NSMakeRect(width - PAD - 16, 0, 26, 22)
        )
        self._more.configure(
            _symbol("ellipsis.circle", "NSActionTemplate"), self._settings_clicked
        )
        root.addSubview_(self._more)

        self._total_label = make_label(
            NSMakeRect(PAD - 2, 0, inner, TOTAL_HEIGHT),
            theme.font_total(),
            theme.primary(),
        )
        root.addSubview_(self._total_label)

        self._subtitle_label = make_label(
            NSMakeRect(PAD, 0, inner, SUBTITLE_HEIGHT),
            theme.font_subtitle(),
            theme.secondary(),
        )
        root.addSubview_(self._subtitle_label)

        self._goal_label = make_label(
            NSMakeRect(PAD, 0, inner, GOAL_ROW_HEIGHT),
            theme.font_small_number(),
            theme.secondary(),
            alignment=NSRightTextAlignment,
        )
        root.addSubview_(self._goal_label)

        self._progress = ProgressBar.alloc().initWithFrame_(
            NSMakeRect(PAD, 0, inner, theme.BAR_HEIGHT)
        )
        root.addSubview_(self._progress)

        self._sparkline = Sparkline.alloc().initWithFrame_(
            NSMakeRect(PAD, 0, inner, theme.SPARK_HEIGHT)
        )
        self._sparkline.set_hover_callback(self._sparkline_hover)
        root.addSubview_(self._sparkline)

        self._spark_caption = Caption.alloc().initWithFrame_(
            NSMakeRect(PAD, 0, inner, CAPTION_HEIGHT)
        )
        root.addSubview_(self._spark_caption)

        self._top_rule = Rule.alloc().initWithFrame_(NSMakeRect(PAD, 0, inner, 1))
        root.addSubview_(self._top_rule)

        list_width = inner + 16
        self._scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(PAD - 8, 0, list_width, 10)
        )
        self._scroll.setDrawsBackground_(False)
        self._scroll.setBorderType_(NSNoBorder)
        self._scroll.setHasVerticalScroller_(True)
        self._scroll.setAutohidesScrollers_(True)
        try:
            self._scroll.setScrollerStyle_(NSScrollerStyleOverlay)
            self._scroll.verticalScroller().setControlSize_(NSControlSizeSmall)
        except Exception:
            pass
        self._list = FlippedView.alloc().initWithFrame_(
            NSMakeRect(0, 0, list_width, 10)
        )
        self._scroll.setDocumentView_(self._list)
        root.addSubview_(self._scroll)

        self._empty = EmptyState.alloc().initWithFrame_(
            NSMakeRect(PAD, 0, inner, EMPTY_HEIGHT)
        )
        root.addSubview_(self._empty)

        self._bottom_rule = Rule.alloc().initWithFrame_(NSMakeRect(PAD, 0, inner, 1))
        root.addSubview_(self._bottom_rule)

        self._add_files = PillButton.alloc().initWithFrame_(
            NSMakeRect(PAD - 8, 0, 110, FOOTER_HEIGHT)
        )
        self._add_files.configure("+  Documents", self._add_files_clicked)
        root.addSubview_(self._add_files)

        self._add_folder = PillButton.alloc().initWithFrame_(
            NSMakeRect(PAD + 100, 0, 90, FOOTER_HEIGHT)
        )
        self._add_folder.configure("+  Folder", self._add_folder_clicked)
        root.addSubview_(self._add_folder)

        self.setView_(root)

    # ── user intent, forwarded to the app delegate ───────────────────

    @objc.python_method
    def _project_clicked(self, sender):
        self._app.showProjectMenu_(sender)

    @objc.python_method
    def _settings_clicked(self, sender):
        self._app.showSettingsMenu_(sender)

    @objc.python_method
    def _add_files_clicked(self, sender):
        self._app.addDocuments_(sender)

    @objc.python_method
    def _add_folder_clicked(self, sender):
        self._app.addFolder_(sender)

    def openDocument_(self, document):  # noqa: N802
        self._app.openPath_(document.path)

    def openDocumentFromMenu_(self, sender):  # noqa: N802
        self._app.openPath_(sender.representedObject())

    def revealDocumentFromMenu_(self, sender):  # noqa: N802
        self._app.revealPath_(sender.representedObject())

    def removeDocumentFromMenu_(self, sender):  # noqa: N802
        self._app.removePath_(sender.representedObject())

    @objc.python_method
    def _sparkline_hover(self, day, value):
        if day is None:
            self._subtitle_label.setStringValue_(self._subtitle_text)
            self._subtitle_label.setTextColor_(theme.secondary())
            return
        noun = theme.plural(value, "word")
        self._subtitle_label.setStringValue_(
            f"{friendly_day(day)} — {theme.thousands(value)} {noun} written"
        )
        self._subtitle_label.setTextColor_(theme.primary())

    # ── rendering ────────────────────────────────────────────────────

    @objc.python_method
    def render(self):
        self.view()  # force loadView before touching any subview

        state = self._app.state
        engine = self._app.engine
        project = state.active
        snapshot = engine.snapshot

        self._project_button.configure(f"{project.name}  ⌄", self._project_clicked)
        self._total_label.setStringValue_(theme.thousands(snapshot.total))

        readable = snapshot.readable
        if not project.sources:
            self._subtitle_text = "no documents yet"
        elif readable == 0:
            self._subtitle_text = "nothing countable here yet"
        else:
            noun = theme.plural(readable, "document")
            self._subtitle_text = f"words across {readable} {noun}"
            if snapshot.problems:
                self._subtitle_text += f" · {snapshot.problems} skipped"
        self._subtitle_label.setStringValue_(self._subtitle_text)
        self._subtitle_label.setTextColor_(theme.secondary())

        written = engine.written_today
        goal = project.goal
        if goal > 0:
            self._progress.set_fraction(written / float(goal))
            self._goal_label.setStringValue_(
                f"{theme.thousands(written)} of {theme.thousands(goal)} today"
            )
        else:
            self._progress.set_fraction(0.0)
            prefix = "+" if written else ""
            self._goal_label.setStringValue_(
                f"{prefix}{theme.thousands(written)} today"
            )

        self._sparkline.set_series(state.daily_series(project.id), goal)

        streak = state.streak(project.id)
        self._spark_caption.set_text(
            "Last 14 days", f"{streak}-day streak" if streak >= 2 else ""
        )

        self._rebuild_rows(snapshot.documents)
        self._layout()

    @objc.python_method
    def _rebuild_rows(self, documents):
        paths = [document.path for document in documents]
        if paths == self._row_paths and len(self._rows) == len(documents):
            for row, document in zip(self._rows, documents):
                row.configure(document, self)
            return

        for row in self._rows:
            row.removeFromSuperview()
        self._rows = []
        self._row_paths = paths

        width = self._list.frame().size.width
        y = 0.0
        for document in documents:
            row = DocumentRow.alloc().initWithFrame_(
                NSMakeRect(0, y, width, ROW_HEIGHT)
            )
            row.configure(document, self)
            self._list.addSubview_(row)
            self._rows.append(row)
            y += ROW_HEIGHT

        self._list.setFrameSize_(NSMakeSize(width, max(y, 1.0)))

    @objc.python_method
    def _place(self, view, y, height, x=None, width=None):
        frame = view.frame()
        view.setFrame_(
            NSMakeRect(
                frame.origin.x if x is None else x,
                y,
                frame.size.width if width is None else width,
                height,
            )
        )

    @objc.python_method
    def _layout(self):
        y = float(PAD) - 2

        self._place(self._project_button, y, HEADER_HEIGHT)
        self._place(self._more, y + 1, 22)
        y += HEADER_HEIGHT + 10

        self._place(self._total_label, y, TOTAL_HEIGHT)
        y += TOTAL_HEIGHT - 2

        self._place(self._subtitle_label, y, SUBTITLE_HEIGHT)
        y += SUBTITLE_HEIGHT + 14

        self._place(self._goal_label, y, GOAL_ROW_HEIGHT)
        y += GOAL_ROW_HEIGHT + 5

        self._place(self._progress, y, theme.BAR_HEIGHT)
        y += theme.BAR_HEIGHT + 18

        self._place(self._sparkline, y, theme.SPARK_HEIGHT)
        y += theme.SPARK_HEIGHT + 7

        self._place(self._spark_caption, y, CAPTION_HEIGHT)
        y += CAPTION_HEIGHT + 14

        self._place(self._top_rule, y, 1)
        y += 7

        if self._rows:
            self._empty.setHidden_(True)
            self._scroll.setHidden_(False)
            height = min(theme.LIST_MAX_HEIGHT, len(self._rows) * ROW_HEIGHT)
            self._place(self._scroll, y, height)
            y += height + 6
        else:
            self._scroll.setHidden_(True)
            self._empty.setHidden_(False)
            self._empty.set_message(
                "Nothing countable in this project yet."
                if self._app.state.active.sources
                else "Add the documents you are working on,\nand Tally keeps the count."
            )
            self._place(self._empty, y, EMPTY_HEIGHT)
            y += EMPTY_HEIGHT + 4

        self._place(self._bottom_rule, y, 1)
        y += 5

        files_width = self._add_files.fitting_width()
        self._place(self._add_files, y, FOOTER_HEIGHT, x=PAD - 8, width=files_width)
        self._place(
            self._add_folder,
            y,
            FOOTER_HEIGHT,
            x=PAD - 8 + files_width + 2,
            width=self._add_folder.fitting_width(),
        )
        y += FOOTER_HEIGHT + PAD - 4

        size = NSMakeSize(PANEL_WIDTH, float(round(y)))
        self.view().setFrameSize_(size)
        self.setPreferredContentSize_(size)
        if self._popover is not None:
            self._popover.setContentSize_(size)
