"""Custom AppKit views.

Everything visible in the panel is drawn here rather than assembled from
stock controls. That is what makes it feel like a piece of Mac software
instead of a form: a real progress bar, a real chart, rows that respond to
the cursor.

A note on style, for anyone new to PyObjC: methods that Objective-C needs to
call keep the ``underscore_`` naming that maps onto selectors. Helpers that
only Python calls are marked ``@objc.python_method`` so that PyObjC leaves
them alone.
"""

from __future__ import annotations

import datetime as _dt

import objc
from AppKit import (
    NSBezierPath,
    NSCenterTextAlignment,
    NSCompositingOperationSourceOver,
    NSCursor,
    NSLeftTextAlignment,
    NSLineBreakByTruncatingTail,
    NSLineBreakByWordWrapping,
    NSMenu,
    NSMenuItem,
    NSRightTextAlignment,
    NSStringDrawingUsesLineFragmentOrigin,
    NSTextField,
    NSTrackingActiveAlways,
    NSTrackingArea,
    NSTrackingInVisibleRect,
    NSTrackingMouseEnteredAndExited,
    NSTrackingMouseMoved,
    NSView,
)
from Foundation import NSMakeRect, NSMakeSize

from . import theme


# ── helpers ──────────────────────────────────────────────────────────────


def make_label(frame, font, colour, alignment=NSLeftTextAlignment):
    """A plain, non-interactive text label."""
    label = NSTextField.alloc().initWithFrame_(frame)
    label.setEditable_(False)
    label.setSelectable_(False)
    label.setBordered_(False)
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setFont_(font)
    label.setTextColor_(colour)
    label.setAlignment_(alignment)
    label.setLineBreakMode_(NSLineBreakByTruncatingTail)
    label.cell().setUsesSingleLineMode_(True)
    return label


def draw_text(text, font, colour, rect, alignment=None, truncate_middle=False, kern=None):
    """Draw one line of text, vertically centred in ``rect``."""
    string = theme.attributed(
        text,
        font,
        colour,
        alignment=alignment,
        truncate_middle=truncate_middle,
        kern=kern,
    )
    size = string.size()
    string.drawInRect_(
        NSMakeRect(
            rect.origin.x,
            rect.origin.y + (rect.size.height - size.height) / 2.0,
            rect.size.width,
            size.height,
        )
    )


def rounded(rect, radius):
    return NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, radius, radius)


def friendly_day(iso: str) -> str:
    try:
        day = _dt.date.fromisoformat(iso)
    except ValueError:
        return iso
    today = _dt.date.today()
    if day == today:
        return "Today"
    if day == today - _dt.timedelta(days=1):
        return "Yesterday"
    return day.strftime("%a %d %b").replace(" 0", " ")


# ── base classes ─────────────────────────────────────────────────────────


class FlippedView(NSView):
    """A container whose origin is the top-left, which is how layout reads."""

    def isFlipped(self):  # noqa: N802
        return True


class HoverView(NSView):
    """Base class for views that need to know where the cursor is."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(HoverView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._hovering = False
        return self

    def updateTrackingAreas(self):  # noqa: N802
        for area in list(self.trackingAreas()):
            self.removeTrackingArea_(area)
        options = (
            NSTrackingMouseEnteredAndExited
            | NSTrackingMouseMoved
            | NSTrackingActiveAlways
            | NSTrackingInVisibleRect
        )
        self.addTrackingArea_(
            NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
                self.bounds(), options, self, None
            )
        )
        objc.super(HoverView, self).updateTrackingAreas()

    def mouseEntered_(self, event):  # noqa: N802
        self._hovering = True
        self.setNeedsDisplay_(True)

    def mouseExited_(self, event):  # noqa: N802
        self._hovering = False
        self.setNeedsDisplay_(True)


# ── progress bar ─────────────────────────────────────────────────────────


class ProgressBar(NSView):
    """A slim capsule showing progress toward the day's goal."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(ProgressBar, self).initWithFrame_(frame)
        if self is None:
            return None
        self._fraction = 0.0
        return self

    @objc.python_method
    def set_fraction(self, value):
        self._fraction = max(0.0, min(1.0, float(value)))
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):  # noqa: N802
        bounds = self.bounds()
        radius = bounds.size.height / 2.0

        theme.track_fill().set()
        rounded(bounds, radius).fill()

        if self._fraction <= 0:
            return

        width = max(bounds.size.height, bounds.size.width * self._fraction)
        theme.accent().set()
        rounded(NSMakeRect(0, 0, width, bounds.size.height), radius).fill()


# ── sparkline ────────────────────────────────────────────────────────────


class Sparkline(HoverView):
    """Words written per day, most recent on the right.

    Hovering a bar reports that day back to the panel, which shows it in
    place of the usual subtitle — a chart you can read without a legend.
    """

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(Sparkline, self).initWithFrame_(frame)
        if self is None:
            return None
        self._series = []
        self._goal = 0
        self._hover_index = -1
        self._on_hover = None
        return self

    @objc.python_method
    def set_series(self, series, goal):
        self._series = list(series)
        self._goal = int(goal or 0)
        self.setNeedsDisplay_(True)

    @objc.python_method
    def set_hover_callback(self, callback):
        self._on_hover = callback

    @objc.python_method
    def _geometry(self):
        count = max(1, len(self._series))
        gap = 3.0
        return (self.bounds().size.width - gap * (count - 1)) / count, gap

    @objc.python_method
    def _index_at(self, x):
        width, gap = self._geometry()
        step = width + gap
        if step <= 0:
            return -1
        index = int(x // step)
        return index if 0 <= index < len(self._series) else -1

    @objc.python_method
    def _report(self):
        if self._on_hover is None:
            return
        if self._hover_index < 0:
            self._on_hover(None, None)
        else:
            day, value = self._series[self._hover_index]
            self._on_hover(day, value)

    def mouseMoved_(self, event):  # noqa: N802
        point = self.convertPoint_fromView_(event.locationInWindow(), None)
        index = self._index_at(point.x)
        if index != self._hover_index:
            self._hover_index = index
            self.setNeedsDisplay_(True)
            self._report()

    def mouseExited_(self, event):  # noqa: N802
        self._hover_index = -1
        objc.super(Sparkline, self).mouseExited_(event)
        self._report()

    def drawRect_(self, rect):  # noqa: N802
        if not self._series:
            return

        bounds = self.bounds()
        width, gap = self._geometry()
        values = [value for _, value in self._series]
        ceiling = max(values + [self._goal, 1])
        usable = bounds.size.height - 2.0
        radius = min(width / 2.0, 2.5)
        accent = theme.accent()
        last = len(self._series) - 1

        if self._goal > 0:
            y = 1.0 + usable * (min(self._goal, ceiling) / float(ceiling))
            line = NSBezierPath.bezierPath()
            line.setLineWidth_(1.0)
            line.setLineDash_count_phase_([2.0, 3.0], 2, 0.0)
            line.moveToPoint_((0, y))
            line.lineToPoint_((bounds.size.width, y))
            theme.faint().set()
            line.stroke()

        for index, (_, value) in enumerate(self._series):
            x = index * (width + gap)
            height = 2.0 if value <= 0 else max(2.5, usable * (value / float(ceiling)))

            if value <= 0:
                theme.faint().set()
            elif index == self._hover_index or index == last:
                accent.set()
            elif self._goal > 0:
                accent.colorWithAlphaComponent_(
                    1.0 if value >= self._goal else 0.38
                ).set()
            else:
                accent.colorWithAlphaComponent_(0.5).set()

            rounded(NSMakeRect(x, 1.0, width, height), radius).fill()


# ── captions and rules ───────────────────────────────────────────────────


class Caption(NSView):
    """A small uppercase section label, with an optional value on the right."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(Caption, self).initWithFrame_(frame)
        if self is None:
            return None
        self._left = ""
        self._right = ""
        return self

    @objc.python_method
    def set_text(self, left, right):
        self._left = left or ""
        self._right = right or ""
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):  # noqa: N802
        bounds = self.bounds()
        half = bounds.size.width * 0.55
        if self._left:
            draw_text(
                self._left.upper(),
                theme.font_caption(),
                theme.tertiary(),
                NSMakeRect(0, 0, half, bounds.size.height),
                kern=0.7,
            )
        if self._right:
            draw_text(
                self._right.upper(),
                theme.font_caption(),
                theme.tertiary(),
                NSMakeRect(
                    bounds.size.width - half, 0, half, bounds.size.height
                ),
                alignment=NSRightTextAlignment,
                kern=0.7,
            )


class Rule(NSView):
    """A hairline separator."""

    def drawRect_(self, rect):  # noqa: N802
        theme.separator().set()
        bounds = self.bounds()
        NSBezierPath.fillRect_(
            NSMakeRect(0, bounds.size.height / 2.0 - 0.5, bounds.size.width, 1.0)
        )


# ── document row ─────────────────────────────────────────────────────────


class DocumentRow(HoverView):
    """One document: its name, its count, and what to do when clicked."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(DocumentRow, self).initWithFrame_(frame)
        if self is None:
            return None
        self._document = None
        self._delegate = None
        return self

    @objc.python_method
    def configure(self, document, delegate):
        self._document = document
        self._delegate = delegate
        self.setToolTip_(getattr(document, "path", None))
        self.setNeedsDisplay_(True)

    def resetCursorRects(self):  # noqa: N802
        self.addCursorRect_cursor_(self.bounds(), NSCursor.pointingHandCursor())

    def acceptsFirstMouse_(self, event):  # noqa: N802
        # The popover may not be key yet; the first click should still count.
        return True

    def mouseDown_(self, event):  # noqa: N802
        # Claim the event so that mouseUp_ is delivered here rather than
        # being passed up the responder chain.
        pass

    def mouseUp_(self, event):  # noqa: N802
        if self._delegate is not None and self._document is not None:
            self._delegate.openDocument_(self._document)

    def menuForEvent_(self, event):  # noqa: N802
        if self._document is None or self._delegate is None:
            return None
        menu = NSMenu.alloc().init()
        entries = (
            ("Open", "openDocumentFromMenu:"),
            ("Reveal in Finder", "revealDocumentFromMenu:"),
            (None, None),
            ("Remove from Project", "removeDocumentFromMenu:"),
        )
        for title, selector in entries:
            if title is None:
                menu.addItem_(NSMenuItem.separatorItem())
                continue
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                title, selector, ""
            )
            item.setTarget_(self._delegate)
            item.setRepresentedObject_(self._document.path)
            menu.addItem_(item)
        return menu

    def drawRect_(self, rect):  # noqa: N802
        document = self._document
        if document is None:
            return

        bounds = self.bounds()
        if self._hovering:
            theme.hover_fill().set()
            rounded(
                NSMakeRect(0, 1, bounds.size.width, bounds.size.height - 2),
                theme.CORNER,
            ).fill()

        if document.missing:
            value, colour, font = "missing", theme.warning(), theme.font_row()
        elif document.error:
            value, colour, font = "unreadable", theme.warning(), theme.font_row()
        else:
            value = theme.thousands(document.words)
            colour, font = theme.primary(), theme.font_row_number()

        number = theme.attributed(value, font, colour, alignment=NSRightTextAlignment)
        number_size = number.size()
        number_width = min(120.0, float(number_size.width) + 2.0)

        inset = 10.0
        name_width = bounds.size.width - number_width - inset * 2 - 10
        draw_text(
            document.name,
            theme.font_row(),
            theme.primary() if document.ok else theme.secondary(),
            NSMakeRect(inset, 0, max(20.0, name_width), bounds.size.height),
            truncate_middle=True,
        )

        number.drawInRect_(
            NSMakeRect(
                bounds.size.width - inset - number_width,
                (bounds.size.height - number_size.height) / 2.0,
                number_width,
                number_size.height,
            )
        )


# ── empty state ──────────────────────────────────────────────────────────


class EmptyState(NSView):
    """Shown before any documents have been added."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(EmptyState, self).initWithFrame_(frame)
        if self is None:
            return None
        self._message = ""
        return self

    @objc.python_method
    def set_message(self, message):
        self._message = message or ""
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):  # noqa: N802
        if not self._message:
            return
        string = theme.attributed(
            self._message,
            theme.font_subtitle(),
            theme.tertiary(),
            alignment=NSCenterTextAlignment,
            line_break=NSLineBreakByWordWrapping,
        )
        bounds = self.bounds()
        width = bounds.size.width - 24
        height = string.boundingRectWithSize_options_(
            NSMakeSize(width, 1000), NSStringDrawingUsesLineFragmentOrigin
        ).size.height
        string.drawInRect_(
            NSMakeRect(
                12,
                max(0.0, (bounds.size.height - height) / 2.0),
                width,
                height + 2,
            )
        )


# ── buttons ──────────────────────────────────────────────────────────────


class PillButton(HoverView):
    """A quiet text button that fills in on hover."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(PillButton, self).initWithFrame_(frame)
        if self is None:
            return None
        self._title = ""
        self._action = None
        self._tint = None
        self._alignment = NSCenterTextAlignment
        return self

    @objc.python_method
    def configure(self, title, action):
        self._title = title or ""
        self._action = action
        self.setNeedsDisplay_(True)

    @objc.python_method
    def set_tint(self, colour):
        self._tint = colour
        self.setNeedsDisplay_(True)

    @objc.python_method
    def set_alignment(self, alignment):
        self._alignment = alignment
        self.setNeedsDisplay_(True)

    @objc.python_method
    def fitting_width(self):
        string = theme.attributed(self._title, theme.font_button(), theme.primary())
        return float(string.size().width) + 22.0

    def resetCursorRects(self):  # noqa: N802
        self.addCursorRect_cursor_(self.bounds(), NSCursor.pointingHandCursor())

    def acceptsFirstMouse_(self, event):  # noqa: N802
        # The popover may not be key yet; the first click should still count.
        return True

    def mouseDown_(self, event):  # noqa: N802
        # Claim the event so that mouseUp_ is delivered here rather than
        # being passed up the responder chain.
        pass

    def mouseUp_(self, event):  # noqa: N802
        if self._action is not None:
            self._action(self)

    def drawRect_(self, rect):  # noqa: N802
        bounds = self.bounds()
        colour = self._tint or theme.accent()
        if self._hovering:
            colour.colorWithAlphaComponent_(0.13).set()
            rounded(bounds, theme.CORNER).fill()
        inset = 0.0 if self._alignment == NSCenterTextAlignment else 8.0
        draw_text(
            self._title,
            theme.font_button(),
            colour,
            NSMakeRect(inset, 0, bounds.size.width - inset * 2, bounds.size.height),
            alignment=self._alignment,
        )


class IconButton(HoverView):
    """A borderless button showing a template image."""

    def initWithFrame_(self, frame):  # noqa: N802
        self = objc.super(IconButton, self).initWithFrame_(frame)
        if self is None:
            return None
        self._image = None
        self._action = None
        return self

    @objc.python_method
    def configure(self, image, action):
        self._image = image
        self._action = action
        self.setNeedsDisplay_(True)

    def resetCursorRects(self):  # noqa: N802
        self.addCursorRect_cursor_(self.bounds(), NSCursor.pointingHandCursor())

    def acceptsFirstMouse_(self, event):  # noqa: N802
        # The popover may not be key yet; the first click should still count.
        return True

    def mouseDown_(self, event):  # noqa: N802
        # Claim the event so that mouseUp_ is delivered here rather than
        # being passed up the responder chain.
        pass

    def mouseUp_(self, event):  # noqa: N802
        if self._action is not None:
            self._action(self)

    def drawRect_(self, rect):  # noqa: N802
        bounds = self.bounds()
        if self._hovering:
            theme.hover_fill().set()
            rounded(bounds, theme.CORNER).fill()
        if self._image is None:
            # Fall back to three dots so the control is never invisible.
            draw_text(
                "•••",
                theme.font_caption(),
                theme.secondary(),
                bounds,
                alignment=NSCenterTextAlignment,
            )
            return
        size = self._image.size()
        self._image.drawInRect_fromRect_operation_fraction_respectFlipped_hints_(
            NSMakeRect(
                (bounds.size.width - size.width) / 2.0,
                (bounds.size.height - size.height) / 2.0,
                size.width,
                size.height,
            ),
            NSMakeRect(0, 0, 0, 0),
            NSCompositingOperationSourceOver,
            1.0 if self._hovering else 0.7,
            True,
            None,
        )
