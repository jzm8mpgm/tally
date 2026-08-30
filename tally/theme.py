"""Typography, colour and spacing.

Everything here resolves through AppKit's semantic colours, so Tally
follows the system appearance — light, dark, increased contrast and the
accent colour the writer chose in System Settings — without a line of
theming code anywhere else.
"""

from __future__ import annotations

from AppKit import (
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSFontWeightLight,
    NSFontWeightMedium,
    NSFontWeightRegular,
    NSFontWeightSemibold,
    NSForegroundColorAttributeName,
    NSKernAttributeName,
    NSLineBreakByTruncatingMiddle,
    NSLineBreakByTruncatingTail,
    NSMutableParagraphStyle,
    NSParagraphStyleAttributeName,
)
from Foundation import NSAttributedString

# ── metrics ──────────────────────────────────────────────────────────────

PANEL_WIDTH = 344
PAD = 18
ROW_HEIGHT = 30
LIST_MAX_HEIGHT = 270
SPARK_HEIGHT = 46
BAR_HEIGHT = 5
CORNER = 6

# ── fonts ────────────────────────────────────────────────────────────────


def font_total():
    return NSFont.monospacedDigitSystemFontOfSize_weight_(40, NSFontWeightLight)


def font_subtitle():
    return NSFont.systemFontOfSize_weight_(11.5, NSFontWeightRegular)


def font_caption():
    return NSFont.systemFontOfSize_weight_(9.5, NSFontWeightSemibold)


def font_row():
    return NSFont.systemFontOfSize_weight_(12.5, NSFontWeightRegular)


def font_row_number():
    return NSFont.monospacedDigitSystemFontOfSize_weight_(12.5, NSFontWeightMedium)


def font_small_number():
    return NSFont.monospacedDigitSystemFontOfSize_weight_(11, NSFontWeightMedium)


def font_menu_bar():
    return NSFont.monospacedDigitSystemFontOfSize_weight_(12, NSFontWeightMedium)


def font_button():
    return NSFont.systemFontOfSize_weight_(11.5, NSFontWeightMedium)


# ── colours ──────────────────────────────────────────────────────────────


def accent():
    return NSColor.controlAccentColor()


def primary():
    return NSColor.labelColor()


def secondary():
    return NSColor.secondaryLabelColor()


def tertiary():
    return NSColor.tertiaryLabelColor()


def faint():
    return NSColor.quaternaryLabelColor()


def separator():
    return NSColor.separatorColor()


def warning():
    return NSColor.systemOrangeColor()


def hover_fill():
    return NSColor.labelColor().colorWithAlphaComponent_(0.06)


def track_fill():
    return NSColor.labelColor().colorWithAlphaComponent_(0.10)


# ── text ─────────────────────────────────────────────────────────────────


def paragraph_style(alignment=None, line_break=None, line_spacing=None):
    style = NSMutableParagraphStyle.alloc().init()
    if alignment is not None:
        style.setAlignment_(alignment)
    if line_break is not None:
        style.setLineBreakMode_(line_break)
    if line_spacing is not None:
        style.setLineSpacing_(line_spacing)
    return style


def attributed(
    text,
    font,
    colour,
    alignment=None,
    truncate_middle=False,
    kern=None,
    line_break=None,
):
    """Build an NSAttributedString ready to draw."""
    if line_break is None:
        line_break = (
            NSLineBreakByTruncatingMiddle
            if truncate_middle
            else NSLineBreakByTruncatingTail
        )
    attributes = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: colour,
        NSParagraphStyleAttributeName: paragraph_style(alignment, line_break),
    }
    if kern:
        attributes[NSKernAttributeName] = kern
    return NSAttributedString.alloc().initWithString_attributes_(str(text), attributes)


def thousands(value) -> str:
    return f"{int(value):,}"


def plural(count, singular, many=None) -> str:
    if count == 1:
        return singular
    return many or singular + "s"
