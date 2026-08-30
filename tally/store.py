"""Persistent state: projects, the documents in them, goals and history.

Everything lives in one small JSON file under Application Support. It is
written atomically, so a crash mid-save can never leave a writer without
their history.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field, replace

APP_NAME = "Tally"

SCHEMA_VERSION = 1
HISTORY_DAYS_KEPT = 730
SPARKLINE_DAYS = 14

MENU_BAR_TOTAL = "total"
MENU_BAR_TODAY = "today"
MENU_BAR_ICON_ONLY = "icon"
MENU_BAR_MODES = (MENU_BAR_TOTAL, MENU_BAR_TODAY, MENU_BAR_ICON_ONLY)


def support_dir() -> str:
    base = os.path.expanduser("~/Library/Application Support")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def state_path() -> str:
    return os.path.join(support_dir(), "state.json")


def today_key() -> str:
    return _dt.date.today().isoformat()


# ── model ────────────────────────────────────────────────────────────────


@dataclass
class Source:
    """A file the writer added, or a folder they pointed at."""

    kind: str  # "file" | "folder"
    path: str
    recursive: bool = True

    @property
    def is_folder(self) -> bool:
        return self.kind == "folder"

    def to_json(self) -> dict:
        data = {"kind": self.kind, "path": self.path}
        if self.is_folder:
            data["recursive"] = self.recursive
        return data

    @classmethod
    def from_json(cls, data: dict) -> "Source":
        return cls(
            kind=data.get("kind", "file"),
            path=data.get("path", ""),
            recursive=bool(data.get("recursive", True)),
        )


@dataclass
class Project:
    name: str
    sources: list[Source] = field(default_factory=list)
    goal: int = 0  # daily word target; 0 means "no goal"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "sources": [s.to_json() for s in self.sources],
        }

    @classmethod
    def from_json(cls, data: dict) -> "Project":
        return cls(
            id=data.get("id") or uuid.uuid4().hex[:12],
            name=data.get("name", "Untitled"),
            goal=int(data.get("goal", 0) or 0),
            sources=[Source.from_json(s) for s in data.get("sources", [])],
        )


@dataclass
class Settings:
    menu_bar_mode: str = MENU_BAR_TOTAL
    launch_at_login: bool = False

    def to_json(self) -> dict:
        return {
            "menu_bar_mode": self.menu_bar_mode,
            "launch_at_login": self.launch_at_login,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Settings":
        mode = data.get("menu_bar_mode", MENU_BAR_TOTAL)
        if mode not in MENU_BAR_MODES:
            mode = MENU_BAR_TOTAL
        return cls(
            menu_bar_mode=mode,
            launch_at_login=bool(data.get("launch_at_login", False)),
        )


class State:
    """The whole of Tally's memory."""

    def __init__(
        self,
        projects: list[Project] | None = None,
        active_id: str | None = None,
        history: dict | None = None,
        settings: Settings | None = None,
        path: str | None = None,
    ) -> None:
        self.projects: list[Project] = projects or []
        self.history: dict[str, dict[str, dict]] = history or {}
        self.settings: Settings = settings or Settings()
        self.path = path or state_path()
        if not self.projects:
            self.projects = [Project(name="My Writing")]
        self._active_id = active_id or self.projects[0].id
        if not self.project(self._active_id):
            self._active_id = self.projects[0].id

    # ── projects ─────────────────────────────────────────────────────

    @property
    def active_id(self) -> str:
        return self._active_id

    @active_id.setter
    def active_id(self, value: str) -> None:
        if self.project(value):
            self._active_id = value

    @property
    def active(self) -> Project:
        return self.project(self._active_id) or self.projects[0]

    def project(self, project_id: str) -> Project | None:
        for project in self.projects:
            if project.id == project_id:
                return project
        return None

    def add_project(self, name: str) -> Project:
        project = Project(name=name)
        self.projects.append(project)
        self._active_id = project.id
        return project

    def remove_project(self, project_id: str) -> None:
        if len(self.projects) <= 1:
            return
        self.projects = [p for p in self.projects if p.id != project_id]
        self.history.pop(project_id, None)
        if self._active_id == project_id:
            self._active_id = self.projects[0].id

    # ── history ──────────────────────────────────────────────────────

    def _day(self, project_id: str, day: str) -> dict | None:
        return self.history.get(project_id, {}).get(day)

    def record_total(self, project_id: str, total: int) -> int:
        """Log ``total`` for today and return how many words that is up on
        where the day started.

        The first count seen on any given day becomes that day's baseline, so
        "today" means what a writer means by it.
        """
        day = today_key()
        days = self.history.setdefault(project_id, {})
        entry = days.get(day)
        if entry is None:
            entry = {"start": total, "end": total}
            days[day] = entry
        else:
            entry["end"] = total
            # A document that shrinks below the baseline (a heavy edit, or a
            # file removed) should not leave the day stuck at a negative.
            if total < entry["start"]:
                entry["start"] = total
        return entry["end"] - entry["start"]

    def shift_baseline(self, project_id: str, delta: int) -> None:
        """Adding or removing a document is not writing.

        When the set of tracked files changes, move today's baseline by the
        same amount so the day's progress stays honest.
        """
        entry = self._day(project_id, today_key())
        if entry is not None:
            entry["start"] = max(0, entry["start"] + delta)

    def written_today(self, project_id: str) -> int:
        entry = self._day(project_id, today_key())
        if not entry:
            return 0
        return max(0, entry["end"] - entry["start"])

    def daily_series(self, project_id: str, days: int = SPARKLINE_DAYS) -> list[tuple[str, int]]:
        """``(iso_date, words_written)`` for the last ``days`` days, oldest first."""
        today = _dt.date.today()
        stored = self.history.get(project_id, {})
        series: list[tuple[str, int]] = []
        for offset in range(days - 1, -1, -1):
            day = (today - _dt.timedelta(days=offset)).isoformat()
            entry = stored.get(day)
            written = max(0, entry["end"] - entry["start"]) if entry else 0
            series.append((day, written))
        return series

    def streak(self, project_id: str) -> int:
        """Consecutive days up to today with any words written."""
        today = _dt.date.today()
        stored = self.history.get(project_id, {})
        count = 0
        for offset in range(0, HISTORY_DAYS_KEPT):
            day = (today - _dt.timedelta(days=offset)).isoformat()
            entry = stored.get(day)
            written = (entry["end"] - entry["start"]) if entry else 0
            if written > 0:
                count += 1
            elif offset == 0:
                continue  # today may not have started yet
            else:
                break
        return count

    def _prune(self) -> None:
        cutoff = (_dt.date.today() - _dt.timedelta(days=HISTORY_DAYS_KEPT)).isoformat()
        for project_id, days in list(self.history.items()):
            self.history[project_id] = {d: v for d, v in days.items() if d >= cutoff}

    # ── persistence ──────────────────────────────────────────────────

    def to_json(self) -> dict:
        return {
            "version": SCHEMA_VERSION,
            "active": self._active_id,
            "projects": [p.to_json() for p in self.projects],
            "history": self.history,
            "settings": self.settings.to_json(),
        }

    def save(self) -> None:
        self._prune()
        payload = json.dumps(self.to_json(), indent=1)
        directory = os.path.dirname(self.path)
        os.makedirs(directory, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            "w", dir=directory, prefix=".state-", suffix=".json", delete=False
        )
        try:
            with handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(handle.name, self.path)
        except OSError:
            try:
                os.unlink(handle.name)
            except OSError:
                pass

    @classmethod
    def load(cls, path: str | None = None) -> "State":
        path = path or state_path()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return cls(path=path)

        projects = [Project.from_json(p) for p in data.get("projects", [])]
        return cls(
            projects=projects,
            active_id=data.get("active"),
            history=data.get("history", {}) or {},
            settings=Settings.from_json(data.get("settings", {}) or {}),
            path=path,
        )


__all__ = [
    "APP_NAME",
    "MENU_BAR_ICON_ONLY",
    "MENU_BAR_MODES",
    "MENU_BAR_TODAY",
    "MENU_BAR_TOTAL",
    "SPARKLINE_DAYS",
    "Project",
    "Settings",
    "Source",
    "State",
    "replace",
    "support_dir",
]
