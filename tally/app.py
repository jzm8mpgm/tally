"""The application itself: a status item, a panel, and a one-second heartbeat."""

from __future__ import annotations

import os
import signal
import time

import objc
from AppKit import (
    NSAlert,
    NSAlertFirstButtonReturn,
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSEventMaskLeftMouseUp,
    NSEventMaskRightMouseUp,
    NSEventTypeRightMouseUp,
    NSImageLeft,
    NSMenu,
    NSMenuItem,
    NSMinYEdge,
    NSModalResponseOK,
    NSOpenPanel,
    NSPopover,
    NSPopoverBehaviorTransient,
    NSStatusBar,
    NSTextField,
    NSVariableStatusItemLength,
    NSWorkspace,
)
from Foundation import (
    NSMakeRect,
    NSObject,
    NSRunLoop,
    NSRunLoopCommonModes,
    NSTimer,
    NSURL,
)

from . import __version__, icons, login_item, theme
from .counter import SUPPORTED_EXTS
from .engine import Engine, source_for
from .panel import PanelController
from .store import (
    MENU_BAR_ICON_ONLY,
    MENU_BAR_TODAY,
    MENU_BAR_TOTAL,
    State,
)

HOMEPAGE = "https://github.com/jzm8mpgm/tally"

# Tally is free. If it earns anything, it goes to 2wish, whose mission is that
# everyone affected by the sudden death of a child or young adult aged 25 or
# under has the bereavement support they need.
#
# The UTM tags let 2wish see in their analytics that a visitor arrived from the
# app. The message field, which the donation flow asks for anyway, is what
# actually tells them by name. Keep the UTM values lowercase and unchanged —
# they are compared as literal strings at the other end.
DONATION_URL = (
    "https://2wish.enthuse.com/donate"
    "?utm_source=tally&utm_medium=macapp&utm_campaign=tally-for-2wish"
    "#!/"
)

# I write in Ulysses myself, and I'm on their Ambassador programme — this is
# my own referral link, disclosed as such wherever it appears.
ULYSSES_URL = "https://ulysses.app/drmattmorgan/"

SAVE_INTERVAL = 45.0

FILE_TYPES = sorted(ext.lstrip(".") for ext in SUPPORTED_EXTS)

# Ctrl-C, and `kill`, when running from source.
#
# A Python signal handler only runs between bytecode instructions, and while
# the AppKit event loop has control the interpreter is not executing any. The
# handler therefore cannot quit the app itself; it raises a flag, and the
# one-second heartbeat — the next Python code to run — acts on it. Without
# this, Ctrl-C prints "^C" and nothing happens.
_INTERRUPTED = []


def _note_interrupt(signum, frame):
    _INTERRUPTED.append(signum)


def install_signal_handlers():
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(signum, _note_interrupt)
        except (ValueError, OSError):  # not the main thread, or unsupported
            pass


class TallyApp(NSObject):
    """Application delegate."""

    # ── lifecycle ────────────────────────────────────────────────────

    def init(self):
        self = objc.super(TallyApp, self).init()
        if self is None:
            return None
        self.state = State.load()
        self.engine = Engine(self.state)
        self._popover = None
        self._panel = None
        self._timer = None
        self._status_item = None
        self._last_save = time.monotonic()
        return self

    def applicationDidFinishLaunching_(self, notification):  # noqa: N802
        self._build_status_item()

        self._panel = PanelController.alloc().initWithApp_(self)
        self._popover = NSPopover.alloc().init()
        self._popover.setContentViewController_(self._panel)
        self._popover.setBehavior_(NSPopoverBehaviorTransient)
        self._popover.setAnimates_(True)
        self._panel.attach_popover(self._popover)

        self.engine.resync_watches()
        self.engine.refresh()
        self._panel.render()
        self._update_status_title()

        self._timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0, self, "tick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSRunLoopCommonModes)

        if not self.state.active.sources:
            # Nothing to show yet, so let the app introduce itself.
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.7, self, "openPanelOnce:", None, False
            )

    def applicationWillTerminate_(self, notification):  # noqa: N802
        self.engine.stop()
        self.state.save()

    def openPanelOnce_(self, timer):  # noqa: N802
        self._show_popover()

    # ── status item ──────────────────────────────────────────────────

    @objc.python_method
    def _build_status_item(self):
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        button = self._status_item.button()
        button.setImage_(icons.menu_bar_image())
        button.setImagePosition_(NSImageLeft)
        button.setFont_(theme.font_menu_bar())
        button.setTarget_(self)
        button.setAction_("statusItemClicked:")
        button.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)
        button.setToolTip_("Tally — live word counts")

    @objc.python_method
    def _update_status_title(self):
        if self._status_item is None:
            return
        button = self._status_item.button()
        mode = self.state.settings.menu_bar_mode
        if mode == MENU_BAR_ICON_ONLY:
            button.setTitle_("")
            return
        if mode == MENU_BAR_TODAY:
            written = self.engine.written_today
            text = f"+{theme.thousands(written)}" if written else "—"
        else:
            text = theme.thousands(self.engine.snapshot.total)
        button.setTitle_(f" {text}")

    def statusItemClicked_(self, sender):  # noqa: N802
        event = NSApp.currentEvent()
        if event is not None and event.type() == NSEventTypeRightMouseUp:
            self._show_quick_menu()
        elif self._popover.isShown():
            self._popover.performClose_(self)
        else:
            self._show_popover()

    @objc.python_method
    def _show_popover(self):
        self.engine.refresh()
        self._panel.render()
        button = self._status_item.button()
        self._popover.showRelativeToRect_ofView_preferredEdge_(
            button.bounds(), button, NSMinYEdge
        )
        NSApp.activateIgnoringOtherApps_(True)

    @objc.python_method
    def _close_popover(self):
        if self._popover is not None and self._popover.isShown():
            self._popover.performClose_(self)

    # ── heartbeat ────────────────────────────────────────────────────

    def tick_(self, timer):  # noqa: N802
        if _INTERRUPTED:
            self.quitTally_(None)
            return

        if self.engine.tick():
            self._update_status_title()
            if self._popover.isShown():
                self._panel.render()
        elif self.state.settings.menu_bar_mode == MENU_BAR_TODAY:
            self._update_status_title()

        now = time.monotonic()
        if now - self._last_save >= SAVE_INTERVAL:
            self._last_save = now
            self.state.save()

    @objc.python_method
    def _reload(self, sources_changed=False, project_changed=False):
        if project_changed:
            self.engine.project_changed()
        elif sources_changed:
            self.engine.sources_changed()
        else:
            self.engine.refresh()
        self.state.save()
        self._update_status_title()
        self._panel.render()

    # ── adding and removing documents ────────────────────────────────

    def addDocuments_(self, sender):  # noqa: N802
        NSApp.activateIgnoringOtherApps_(True)
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(True)
        panel.setMessage_("Choose the documents you want Tally to count")
        panel.setPrompt_("Add")
        try:
            panel.setAllowedFileTypes_(FILE_TYPES)
        except Exception:
            pass
        if panel.runModal() != NSModalResponseOK:
            return
        self._add_paths([url.path() for url in panel.URLs()])

    def addFolder_(self, sender):  # noqa: N802
        NSApp.activateIgnoringOtherApps_(True)
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(False)
        panel.setCanChooseDirectories_(True)
        panel.setAllowsMultipleSelection_(True)
        panel.setMessage_("Choose a folder to watch")
        panel.setPrompt_("Watch")
        if panel.runModal() != NSModalResponseOK:
            return
        self._add_paths([url.path() for url in panel.URLs()])

    @objc.python_method
    def _add_paths(self, paths):
        project = self.state.active
        existing = {source.path for source in project.sources}
        added = False
        for path in paths:
            if path and path not in existing:
                project.sources.append(source_for(path))
                existing.add(path)
                added = True
        if added:
            self._reload(sources_changed=True)
        self._show_popover()

    def removePath_(self, path):  # noqa: N802
        project = self.state.active
        remaining = [source for source in project.sources if source.path != path]
        if len(remaining) == len(project.sources):
            self._alert(
                "That document is inside a watched folder",
                "Remove the folder from this project to stop counting it.",
            )
            return
        project.sources = remaining
        self._reload(sources_changed=True)

    def openPath_(self, path):  # noqa: N802
        if path and os.path.exists(path):
            NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(path))

    def revealPath_(self, path):  # noqa: N802
        if path and os.path.exists(path):
            NSWorkspace.sharedWorkspace().selectFile_inFileViewerRootedAtPath_(
                path, os.path.dirname(path)
            )

    # ── menus ────────────────────────────────────────────────────────

    @objc.python_method
    def _item(self, menu, title, selector, represented=None, ticked=False, enabled=True):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, selector, ""
        )
        item.setTarget_(self)
        if represented is not None:
            item.setRepresentedObject_(represented)
        if ticked:
            item.setState_(1)
        item.setEnabled_(enabled)
        menu.addItem_(item)
        return item

    @objc.python_method
    def _pop_up(self, menu, sender):
        menu.popUpMenuPositioningItem_atLocation_inView_(
            None, (0, sender.frame().size.height + 2), sender
        )

    def showProjectMenu_(self, sender):  # noqa: N802
        menu = NSMenu.alloc().init()
        for project in self.state.projects:
            self._item(
                menu,
                project.name,
                "chooseProject:",
                represented=project.id,
                ticked=project.id == self.state.active_id,
            )
        menu.addItem_(NSMenuItem.separatorItem())
        self._item(menu, "New Project…", "newProject:")
        self._item(menu, "Rename Project…", "renameProject:")
        self._item(
            menu,
            "Delete Project",
            "deleteProject:",
            enabled=len(self.state.projects) > 1,
        )
        self._pop_up(menu, sender)

    def showSettingsMenu_(self, sender):  # noqa: N802
        settings = self.state.settings
        goal = self.state.active.goal
        menu = NSMenu.alloc().init()

        self._item(
            menu,
            f"Daily Goal: {theme.thousands(goal)} words…" if goal else "Set Daily Goal…",
            "editGoal:",
        )
        if goal:
            self._item(menu, "Clear Daily Goal", "clearGoal:")

        menu.addItem_(NSMenuItem.separatorItem())

        submenu = NSMenu.alloc().init()
        for mode, label in (
            (MENU_BAR_TOTAL, "Total words"),
            (MENU_BAR_TODAY, "Words written today"),
            (MENU_BAR_ICON_ONLY, "Icon only"),
        ):
            self._item(
                submenu,
                label,
                "chooseMenuBarMode:",
                represented=mode,
                ticked=settings.menu_bar_mode == mode,
            )
        parent = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Menu Bar Shows", None, ""
        )
        menu.addItem_(parent)
        menu.setSubmenu_forItem_(submenu, parent)

        self._item(
            menu, "Open at Login", "toggleLoginItem:", ticked=login_item.is_enabled()
        )

        menu.addItem_(NSMenuItem.separatorItem())
        self._item(menu, "Refresh Now", "refreshNow:")
        self._item(menu, "Try Ulysses…", "tryUlysses:")
        self._item(menu, "Support 2wish…", "donate:")
        self._item(menu, f"About Tally {__version__}", "showAbout:")
        menu.addItem_(NSMenuItem.separatorItem())
        self._item(menu, "Quit Tally", "quitTally:")
        self._pop_up(menu, sender)

    @objc.python_method
    def _show_quick_menu(self):
        menu = NSMenu.alloc().init()
        total = theme.thousands(self.engine.snapshot.total)
        today = theme.thousands(self.engine.written_today)
        self._item(
            menu, f"{total} words · +{today} today", "noop:", enabled=False
        )
        menu.addItem_(NSMenuItem.separatorItem())
        self._item(menu, "Refresh Now", "refreshNow:")
        self._item(menu, "Quit Tally", "quitTally:")
        self._status_item.setMenu_(menu)
        self._status_item.button().performClick_(None)
        self._status_item.setMenu_(None)

    # ── menu actions ─────────────────────────────────────────────────

    def noop_(self, sender):  # noqa: N802
        pass

    def chooseProject_(self, sender):  # noqa: N802
        self.state.active_id = sender.representedObject()
        self._reload(project_changed=True)

    def newProject_(self, sender):  # noqa: N802
        name = self._prompt("New project", "What are you working on?", "Untitled")
        if name:
            self.state.add_project(name)
            self._reload(project_changed=True)
            self._show_popover()

    def renameProject_(self, sender):  # noqa: N802
        project = self.state.active
        name = self._prompt("Rename project", "", project.name)
        if name:
            project.name = name
            self._reload()
            self._show_popover()

    def deleteProject_(self, sender):  # noqa: N802
        project = self.state.active
        if not self._confirm(
            f"Delete “{project.name}”?",
            "Your documents are untouched — only this project and its writing "
            "history are removed.",
            "Delete",
        ):
            return
        self.state.remove_project(project.id)
        self._reload(project_changed=True)
        self._show_popover()

    def editGoal_(self, sender):  # noqa: N802
        project = self.state.active
        answer = self._prompt(
            "Daily writing goal",
            "How many words a day are you aiming for?",
            str(project.goal or 1000),
        )
        if answer is None:
            return
        digits = "".join(character for character in answer if character.isdigit())
        project.goal = int(digits) if digits else 0
        self._reload()
        self._show_popover()

    def clearGoal_(self, sender):  # noqa: N802
        self.state.active.goal = 0
        self._reload()

    def chooseMenuBarMode_(self, sender):  # noqa: N802
        self.state.settings.menu_bar_mode = sender.representedObject()
        self.state.save()
        self._update_status_title()

    def toggleLoginItem_(self, sender):  # noqa: N802
        enabled = login_item.set_enabled(not login_item.is_enabled())
        self.state.settings.launch_at_login = enabled
        self.state.save()

    def refreshNow_(self, sender):  # noqa: N802
        self.engine.cache.clear()
        self._reload()

    def donate_(self, sender):  # noqa: N802
        self._close_popover()
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Tally is free — 2wish is not")
        alert.setInformativeText_(
            "If Tally has been useful, please give to 2wish rather than to me."
            "\n\n"
            "Their mission is that everyone affected by the sudden and "
            "unexpected death of a child or young adult aged 25 or under has "
            "the bereavement support they need and deserve.\n\n"
            "As an intensive care doctor, I sit with families in the worst "
            "hours of their lives more often than I would wish, and I have "
            "seen first hand what a difference genuine bereavement support "
            "makes when someone dies suddenly or unexpectedly.\n\n"
            "The donation form has a message box. Putting “Tally” in it lets "
            "them see the app brought you there."
        )
        alert.addButtonWithTitle_("Donate to 2wish")
        alert.addButtonWithTitle_("Not now")
        NSApp.activateIgnoringOtherApps_(True)
        if alert.runModal() == NSAlertFirstButtonReturn:
            NSWorkspace.sharedWorkspace().openURL_(
                NSURL.URLWithString_(DONATION_URL)
            )

    def tryUlysses_(self, sender):  # noqa: N802
        self._close_popover()
        alert = NSAlert.alloc().init()
        alert.setMessageText_("The app I actually write in")
        alert.setInformativeText_(
            "Tally counts words; it doesn't write them. I do that in "
            "Ulysses — a distraction-free writing app for Mac, iPad and "
            "iPhone that keeps everything as plain text and Markdown, and "
            "exports to Word, PDF, ebook or wherever it needs to go next. "
            "Tally exists because I wanted the count without leaving it.\n\n"
            "I'm on Ulysses's Ambassador programme, so the link below is my "
            "own referral link — a genuine recommendation, not a paid one."
        )
        alert.addButtonWithTitle_("Try Ulysses")
        alert.addButtonWithTitle_("Not now")
        NSApp.activateIgnoringOtherApps_(True)
        if alert.runModal() == NSAlertFirstButtonReturn:
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(ULYSSES_URL))

    def showAbout_(self, sender):  # noqa: N802
        self._close_popover()
        alert = NSAlert.alloc().init()
        alert.setMessageText_(f"Tally {__version__}")
        alert.setInformativeText_(
            "Live word counts for the documents you are writing, in your "
            "menu bar.\n\nFree and open source, under the MIT licence. "
            "If it has been useful, please give to 2wish — bereavement "
            "support for families after the sudden death of a child or young "
            "adult — rather than to me.\n\nI write in Ulysses myself; it's "
            "why Tally exists."
        )
        alert.addButtonWithTitle_("Close")
        alert.addButtonWithTitle_("View on GitHub")
        alert.addButtonWithTitle_("Support 2wish")
        alert.addButtonWithTitle_("Try Ulysses")
        NSApp.activateIgnoringOtherApps_(True)
        response = alert.runModal()
        if response == NSAlertFirstButtonReturn + 1:
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(HOMEPAGE))
        elif response == NSAlertFirstButtonReturn + 2:
            NSWorkspace.sharedWorkspace().openURL_(
                NSURL.URLWithString_(DONATION_URL)
            )
        elif response == NSAlertFirstButtonReturn + 3:
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(ULYSSES_URL))

    def quitTally_(self, sender):  # noqa: N802
        self.engine.stop()
        self.state.save()
        NSApp.terminate_(self)

    # ── small dialogs ────────────────────────────────────────────────

    @objc.python_method
    def _prompt(self, title, message, default=""):
        self._close_popover()
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        if message:
            alert.setInformativeText_(message)
        alert.addButtonWithTitle_("Save")
        alert.addButtonWithTitle_("Cancel")

        field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 240, 24))
        field.setStringValue_(str(default))
        alert.setAccessoryView_(field)
        alert.window().setInitialFirstResponder_(field)

        NSApp.activateIgnoringOtherApps_(True)
        if alert.runModal() != NSAlertFirstButtonReturn:
            return None
        return str(field.stringValue()).strip() or None

    @objc.python_method
    def _confirm(self, title, message, confirm_title="OK"):
        self._close_popover()
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_(confirm_title)
        alert.addButtonWithTitle_("Cancel")
        NSApp.activateIgnoringOtherApps_(True)
        return alert.runModal() == NSAlertFirstButtonReturn

    @objc.python_method
    def _alert(self, title, message):
        self._close_popover()
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        NSApp.activateIgnoringOtherApps_(True)
        alert.runModal()


def main() -> int:
    from PyObjCTools import AppHelper

    application = NSApplication.sharedApplication()
    application.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    install_signal_handlers()

    delegate = TallyApp.alloc().init()
    application.setDelegate_(delegate)
    globals()["_delegate"] = delegate  # keep the delegate alive

    AppHelper.runEventLoop()
    return 0
