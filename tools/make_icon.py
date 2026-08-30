#!/usr/bin/env python3
"""Generate Tally's app icon.

Draws the mark once at high resolution, then writes every size macOS asks
for into ``assets/Tally.icns`` — no Xcode, no iconutil, no design tool.

    python3 tools/make_icon.py
"""

from __future__ import annotations

import os
import struct
import sys
from io import BytesIO

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

# Big Sur icon geometry: the rounded square fills 824 of a 1024pt canvas.
CANVAS = 1024
SQUARE = 824
RADIUS = 185
SUPERSAMPLE = 2

TOP = (0x33, 0x40, 0x66)
BOTTOM = (0x13, 0x1B, 0x2E)
INK = (0xF7, 0xF4, 0xEC)

# The mark: four strokes and a fifth laid across them.
COLUMNS = (-186, -62, 62, 186)
STROKE_HALF_HEIGHT = 176
STROKE_WIDTH = 50
DIAGONAL = ((-234, 116), (234, -84))


def _gradient(size, top, bottom):
    image = Image.new("RGB", (1, size), top)
    pixels = image.load()
    for y in range(size):
        t = y / max(1, size - 1)
        pixels[0, y] = tuple(
            round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)
        )
    return image.resize((size, size))


def _capsule(draw, start, end, width, fill):
    """A line with round caps — Pillow has no cap style of its own."""
    radius = width / 2.0
    draw.line([start, end], fill=fill, width=width)
    for x, y in (start, end):
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius], fill=fill
        )


def render(size=CANVAS) -> Image.Image:
    scale = SUPERSAMPLE
    canvas = size * scale
    square = round(SQUARE * size / CANVAS) * scale
    radius = round(RADIUS * size / CANVAS) * scale
    centre = canvas / 2.0
    unit = size / CANVAS * scale

    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))

    mask = Image.new("L", (canvas, canvas), 0)
    offset = (canvas - square) / 2.0
    ImageDraw.Draw(mask).rounded_rectangle(
        [offset, offset, offset + square, offset + square],
        radius=radius,
        fill=255,
    )
    image.paste(_gradient(canvas, TOP, BOTTOM).convert("RGBA"), (0, 0), mask)

    marks = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(marks)
    width = max(1, round(STROKE_WIDTH * unit))
    for column in COLUMNS:
        x = centre + column * unit
        _capsule(
            draw,
            (x, centre - STROKE_HALF_HEIGHT * unit),
            (x, centre + STROKE_HALF_HEIGHT * unit),
            width,
            INK + (255,),
        )
    (x1, y1), (x2, y2) = DIAGONAL
    _capsule(
        draw,
        (centre + x1 * unit, centre + y1 * unit),
        (centre + x2 * unit, centre + y2 * unit),
        width,
        INK + (255,),
    )

    image.alpha_composite(marks)
    return image.resize((size, size), Image.LANCZOS)


# ── .icns writing ────────────────────────────────────────────────────────

# (OSType, pixel size) — everything macOS looks for, as PNG payloads.
ICNS_ENTRIES = (
    (b"icp4", 16),
    (b"icp5", 32),
    (b"icp6", 64),
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
    (b"ic10", 1024),
    (b"ic11", 32),
    (b"ic12", 64),
    (b"ic13", 256),
    (b"ic14", 512),
)


def write_icns(master: Image.Image, path: str) -> None:
    chunks = []
    cache: dict[int, bytes] = {}
    for ostype, size in ICNS_ENTRIES:
        if size not in cache:
            buffer = BytesIO()
            master.resize((size, size), Image.LANCZOS).save(buffer, format="PNG")
            cache[size] = buffer.getvalue()
        payload = cache[size]
        chunks.append(ostype + struct.pack(">I", len(payload) + 8) + payload)

    body = b"".join(chunks)
    with open(path, "wb") as handle:
        handle.write(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> int:
    os.makedirs(ASSETS, exist_ok=True)
    master = render(1024)
    master.save(os.path.join(ASSETS, "icon.png"))
    write_icns(master, os.path.join(ASSETS, "Tally.icns"))
    print("wrote assets/icon.png and assets/Tally.icns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
