"""Word counting.

Reads .docx / .docm straight from the OOXML package — no python-docx, no
external dependency. That makes it fast enough to recount a folder of
manuscripts on every keystroke-save, and it picks up text that naive
paragraph-only readers miss (tables, text boxes, content controls).

Plain text and Markdown files are supported too, because writers rarely
keep everything in one format.
"""

from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree as ET

# WordprocessingML namespace
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Tags whose presence implies a whitespace break between runs of text.
_BREAK_TAGS = frozenset(
    (_W + "p", _W + "br", _W + "tab", _W + "cr", _W + "tc")
)

DOCX_EXTS = frozenset((".docx", ".docm"))
TEXT_EXTS = frozenset((".txt", ".md", ".markdown", ".text"))
SUPPORTED_EXTS = DOCX_EXTS | TEXT_EXTS

# Word treats a "word" as a run of non-whitespace characters. Anything that
# is *only* punctuation (a lone em dash used as a scene break, a row of
# asterisks) is not prose, so it does not earn a tick.
_PUNCT_ONLY = re.compile(r"^[^\w]+$", re.UNICODE)


class UnreadableDocument(Exception):
    """Raised when a file exists but cannot be counted."""


@dataclass(frozen=True)
class Count:
    words: int = 0
    characters: int = 0

    def __add__(self, other: "Count") -> "Count":
        return Count(self.words + other.words, self.characters + other.characters)


ZERO = Count()


# ── file classification ──────────────────────────────────────────────────


def is_temp_file(name: str) -> bool:
    """Word's lock files (``~$chapter.docx``) and dotfiles are not documents."""
    base = os.path.basename(name)
    return base.startswith("~$") or base.startswith(".")


def is_supported(path: str) -> bool:
    if is_temp_file(path):
        return False
    return os.path.splitext(path)[1].lower() in SUPPORTED_EXTS


# ── extraction ───────────────────────────────────────────────────────────


def _docx_text(path: str) -> str:
    """Pull every piece of body text out of an OOXML package."""
    pieces: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            try:
                xml = archive.read("word/document.xml")
            except KeyError as exc:  # not a Word package
                raise UnreadableDocument("no document body") from exc
    except zipfile.BadZipFile as exc:
        raise UnreadableDocument("not a valid .docx package") from exc

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise UnreadableDocument("malformed document XML") from exc

    # Document order. A break tag emits whitespace before its subtree, which
    # is exactly what we want: it separates this paragraph/cell from the last.
    for element in root.iter():
        tag = element.tag
        if tag == _W + "t":
            if element.text:
                pieces.append(element.text)
        elif tag in _BREAK_TAGS:
            pieces.append("\n")

    return "".join(pieces)


def _plain_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in DOCX_EXTS:
        return _docx_text(path)
    if ext in TEXT_EXTS:
        return _plain_text(path)
    raise UnreadableDocument(f"unsupported file type: {ext or 'none'}")


def count_text(text: str) -> Count:
    tokens = text.split()
    words = sum(1 for token in tokens if not _PUNCT_ONLY.match(token))
    characters = sum(len(token) for token in tokens)
    return Count(words=words, characters=characters)


def count_file(path: str) -> Count:
    """Count one document. Raises :class:`UnreadableDocument` on failure."""
    try:
        return count_text(extract_text(path))
    except UnreadableDocument:
        raise
    except OSError as exc:
        raise UnreadableDocument(str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise UnreadableDocument(str(exc)) from exc


# ── caching ──────────────────────────────────────────────────────────────


class CountCache:
    """Counts files, remembering results until their size or mtime changes.

    Recounting an unchanged 90,000-word manuscript costs one ``stat`` call,
    so the app can afford to re-check everything every couple of seconds.
    """

    def __init__(self) -> None:
        self._entries: dict[str, tuple[int, int, Count]] = {}

    def forget(self, path: str) -> None:
        self._entries.pop(path, None)

    def clear(self) -> None:
        self._entries.clear()

    def count(self, path: str) -> Count:
        """Return the count for ``path``, raising :class:`UnreadableDocument`."""
        try:
            info = os.stat(path)
        except OSError as exc:
            self.forget(path)
            raise UnreadableDocument(str(exc)) from exc

        signature = (info.st_size, info.st_mtime_ns)
        cached = self._entries.get(path)
        if cached is not None and cached[:2] == signature:
            return cached[2]

        result = count_file(path)
        self._entries[path] = (signature[0], signature[1], result)
        return result


# ── folder discovery ─────────────────────────────────────────────────────

# Directories that never contain a manuscript worth counting.
_SKIP_DIRS = frozenset(
    (".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist")
)


def documents_in_folder(folder: str, recursive: bool = True) -> list[str]:
    """Every supported document inside ``folder``, sorted by name."""
    found: list[str] = []
    try:
        if recursive:
            for root, dirs, files in os.walk(folder):
                dirs[:] = [
                    d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")
                ]
                found.extend(
                    os.path.join(root, name) for name in files if is_supported(name)
                )
        else:
            with os.scandir(folder) as entries:
                found.extend(
                    entry.path
                    for entry in entries
                    if entry.is_file() and is_supported(entry.name)
                )
    except OSError:
        return []
    return sorted(found, key=lambda p: os.path.basename(p).lower())
