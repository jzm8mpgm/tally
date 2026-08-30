"""The live-counting engine.

Two things keep the number in the menu bar honest:

1. A filesystem watcher (FSEvents, via watchdog) that fires the instant a
   document is saved.
2. A slow backstop poll, for the cases watchers miss — a file synced in by
   Dropbox, a volume that woke from sleep, a watcher that quietly died.

Counting itself is cheap because :class:`~tally.counter.CountCache` skips
any document whose size and modification time are unchanged.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field

from .counter import (
    CountCache,
    UnreadableDocument,
    documents_in_folder,
    is_supported,
)
from .store import Project, Source, State

# Word writes a document by creating a temporary file and renaming it over
# the original, so a single save produces a small flurry of events.
DEBOUNCE_SECONDS = 0.35

# How long we let the watcher go unquestioned before checking for ourselves.
BACKSTOP_SECONDS = 3.0


@dataclass
class Document:
    path: str
    name: str
    words: int = 0
    characters: int = 0
    error: str | None = None
    missing: bool = False
    # Which source it came from — a folder name, or "" for a hand-picked file.
    group: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None and not self.missing


@dataclass
class Snapshot:
    documents: list[Document] = field(default_factory=list)
    total: int = 0
    characters: int = 0
    readable: int = 0
    problems: int = 0


# ── filesystem watching ──────────────────────────────────────────────────

try:  # watchdog is optional; the backstop poll covers its absence
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG = True
except Exception:  # pragma: no cover - depends on the install
    _WATCHDOG = False
    FileSystemEventHandler = object  # type: ignore[assignment]
    Observer = None  # type: ignore[assignment]


class _Handler(FileSystemEventHandler):  # type: ignore[misc]
    def __init__(self, notify) -> None:
        self._notify = notify

    def on_any_event(self, event) -> None:  # pragma: no cover - needs a real FS
        if getattr(event, "is_directory", False):
            return
        candidates = (
            getattr(event, "src_path", "") or "",
            getattr(event, "dest_path", "") or "",
        )
        if any(is_supported(path) for path in candidates if path):
            self._notify()


class FileWatcher:
    """Watches a set of directories, collapsing everything to one callback."""

    def __init__(self, notify) -> None:
        self._notify = notify
        self._observer = None
        self._watched: frozenset[str] = frozenset()

    @property
    def active(self) -> bool:
        return self._observer is not None

    def watch(self, directories: set[str]) -> None:
        wanted = frozenset(d for d in directories if os.path.isdir(d))
        if wanted == self._watched and self._observer is not None:
            return
        self.stop()
        self._watched = wanted
        if not _WATCHDOG or not wanted:
            return
        try:
            observer = Observer()
            handler = _Handler(self._notify)
            for directory in _prune_nested(wanted):
                observer.schedule(handler, directory, recursive=True)
            observer.daemon = True
            observer.start()
            self._observer = observer
        except Exception:  # pragma: no cover - watcher is best effort
            self._observer = None

    def stop(self) -> None:
        observer, self._observer = self._observer, None
        if observer is None:
            return
        try:
            observer.stop()
            observer.join(timeout=1.5)
        except Exception:  # pragma: no cover
            pass


def _prune_nested(directories: frozenset[str]) -> list[str]:
    """Drop directories already covered by a recursive watch on an ancestor."""
    ordered = sorted(directories, key=len)
    kept: list[str] = []
    for directory in ordered:
        normalised = os.path.normpath(directory)
        if any(
            normalised == parent or normalised.startswith(parent + os.sep)
            for parent in kept
        ):
            continue
        kept.append(normalised)
    return kept


# ── the engine ───────────────────────────────────────────────────────────


class Engine:
    """Turns a :class:`~tally.store.Project` into a live :class:`Snapshot`."""

    def __init__(self, state: State) -> None:
        self.state = state
        self.cache = CountCache()
        self.snapshot = Snapshot()
        self.written_today = 0

        self._dirty = threading.Event()
        self._last_event = 0.0
        self._last_refresh = 0.0
        self._watcher = FileWatcher(self._mark_dirty)

    # ── lifecycle ────────────────────────────────────────────────────

    def stop(self) -> None:
        self._watcher.stop()

    def _mark_dirty(self) -> None:
        self._last_event = time.monotonic()
        self._dirty.set()

    # ── scanning ─────────────────────────────────────────────────────

    def _resolve(self, project: Project) -> list[tuple[str, str]]:
        """``(path, group_label)`` for every document in the project."""
        resolved: list[tuple[str, str]] = []
        seen: set[str] = set()
        for source in project.sources:
            if source.is_folder:
                label = os.path.basename(source.path.rstrip("/")) or source.path
                for path in documents_in_folder(source.path, source.recursive):
                    if path not in seen:
                        seen.add(path)
                        resolved.append((path, label))
            else:
                if source.path not in seen:
                    seen.add(source.path)
                    resolved.append((source.path, ""))
        return resolved

    def watch_directories(self, project: Project) -> set[str]:
        directories: set[str] = set()
        for source in project.sources:
            if source.is_folder:
                directories.add(source.path)
            else:
                directories.add(os.path.dirname(source.path))
        return {d for d in directories if d}

    def resync_watches(self) -> None:
        self._watcher.watch(self.watch_directories(self.state.active))

    def refresh(self) -> Snapshot:
        """Recount everything in the active project and update history."""
        project = self.state.active
        documents: list[Document] = []
        total = characters = readable = problems = 0

        for path, group in self._resolve(project):
            name = os.path.splitext(os.path.basename(path))[0]
            if not os.path.exists(path):
                documents.append(
                    Document(path=path, name=name, missing=True, group=group)
                )
                problems += 1
                continue
            try:
                count = self.cache.count(path)
            except UnreadableDocument as exc:
                documents.append(
                    Document(path=path, name=name, error=str(exc), group=group)
                )
                problems += 1
                continue
            documents.append(
                Document(
                    path=path,
                    name=name,
                    words=count.words,
                    characters=count.characters,
                    group=group,
                )
            )
            total += count.words
            characters += count.characters
            readable += 1

        documents.sort(key=lambda d: (not d.ok, -d.words, d.name.lower()))

        self.snapshot = Snapshot(
            documents=documents,
            total=total,
            characters=characters,
            readable=readable,
            problems=problems,
        )
        self.written_today = self.state.record_total(project.id, total)
        self._last_refresh = time.monotonic()
        self._dirty.clear()
        return self.snapshot

    def sources_changed(self) -> Snapshot:
        """Call after documents are added or removed.

        Re-points the watcher and shifts today's baseline so that importing a
        finished 80,000-word manuscript does not read as a heroic morning.
        """
        before = self.snapshot.total
        self.cache.clear()
        self.resync_watches()
        snapshot = self.refresh()
        self.state.shift_baseline(self.state.active.id, snapshot.total - before)
        self.written_today = self.state.written_today(self.state.active.id)
        return snapshot

    def project_changed(self) -> Snapshot:
        """Call after switching projects."""
        self.cache.clear()
        self.resync_watches()
        return self.refresh()

    def tick(self) -> bool:
        """Called once a second from the main thread. True if the count moved."""
        now = time.monotonic()
        settled = now - self._last_event >= DEBOUNCE_SECONDS
        due = now - self._last_refresh >= BACKSTOP_SECONDS

        if not ((self._dirty.is_set() and settled) or due):
            return False

        previous_total = self.snapshot.total
        previous_count = len(self.snapshot.documents)
        previous_problems = self.snapshot.problems
        snapshot = self.refresh()
        return (
            snapshot.total != previous_total
            or len(snapshot.documents) != previous_count
            or snapshot.problems != previous_problems
        )


def source_for(path: str) -> Source:
    if os.path.isdir(path):
        return Source(kind="folder", path=path, recursive=True)
    return Source(kind="file", path=path)
