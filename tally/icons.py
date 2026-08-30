"""The menu bar glyph.

Drawn rather than shipped as an asset, so it stays crisp on every display
and — as a template image — takes its colour from the menu bar itself,
including when the bar is dark, or highlighted, or in increased contrast.

The mark is a writer's tally: four strokes and a fifth laid across them.
"""

from __future__ import annotations

import AppKit
from AppKit import NSBezierPath, NSColor, NSImage
from Foundation import NSMakePoint, NSMakeSize

# Renamed in the macOS 10.15 SDK; older PyObjC builds only know the old name.
ROUND_CAP = getattr(
    AppKit, "NSLineCapStyleRound", getattr(AppKit, "NSRoundLineCapStyle", 1)
)

_WIDTH = 14.0
_HEIGHT = 13.0
_STROKE = 1.6
_COLUMNS = (2.2, 5.0, 7.8, 10.6)
_TOP = 10.6
_BOTTOM = 2.4


def menu_bar_image() -> NSImage:
    image = NSImage.alloc().initWithSize_(NSMakeSize(_WIDTH, _HEIGHT))
    image.lockFocus()

    NSColor.blackColor().set()
    path = NSBezierPath.bezierPath()
    path.setLineWidth_(_STROKE)
    path.setLineCapStyle_(ROUND_CAP)

    for x in _COLUMNS:
        path.moveToPoint_(NSMakePoint(x, _BOTTOM))
        path.lineToPoint_(NSMakePoint(x, _TOP))

    # The fifth stroke, laid across the other four.
    path.moveToPoint_(NSMakePoint(1.0, 3.6))
    path.lineToPoint_(NSMakePoint(11.9, 9.4))

    path.stroke()
    image.unlockFocus()

    image.setTemplate_(True)
    return image
