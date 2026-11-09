"""gobrowser - a Finder-like column browser for the goclaude bookmarks.

Launched by `go -g`. The first column lists the enabled bookmarks from
~/.go_locations; further columns walk into folders and show files.

    Return / double-click   open the folder in Finder, or reveal the file there
    Add...                  save the front Finder folder (or a chosen one) as a bookmark
    Delete...               remove the selected bookmark (the folder itself is untouched)
    Delete / Backspace      same as Delete...
    Cmd-R                   reload the bookmarks
    Cmd-W / Cmd-Q           close / quit

The bookmark file is read with read_locations() from the goclaude script,
which is bundled into the app (or found beside this file when run from source).
"""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys

import objc
from AppKit import (
    NSAlert, NSApplication, NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered, NSBrowser, NSButton, NSFloatingWindowLevel,
    NSOpenPanel, NSTextField, NSMakeRect, NSMenu, NSMenuItem, NSObject, NSViewController,
    NSWindow, NSWindowStyleMaskClosable, NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable, NSWindowStyleMaskTitled, NSWorkspace,
)
from Foundation import NSURL, NSNotificationCenter
from Quartz import QLPreviewView

APP_VERSION = "1.5.0"


def load_go():
    """Import the goclaude script (no .py extension) as a module."""
    here = os.environ.get("RESOURCEPATH") or os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "goclaude")
    loader = importlib.machinery.SourceFileLoader("go_claude", path)
    spec = importlib.util.spec_from_loader("go_claude", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


go = load_go()


def is_folder(path):
    """A real folder, not an app or other package (those open, not expand)."""
    ws = NSWorkspace.sharedWorkspace()
    return os.path.isdir(path) and not ws.isFilePackageAtPath_(path)


def open_in_finder(path):
    if not os.path.exists(path):
        return
    if is_folder(path):
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["open", "-R", path])


def front_finder_folder():
    """Folder of the front Finder window, or None (no window, or no permission)."""
    script = ('tell application "Finder" to if (count of Finder windows) > 0 '
              'then POSIX path of (target of front Finder window as alias)')
    try:
        out = subprocess.run(["osascript", "-e", script], capture_output=True,
                             text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out.rstrip("/") or None if out else None


def add_bookmark(name, path):
    """Append one line to ~/.go_locations; returns an error message or None.

    If an enabled bookmark of that name exists but its path is gone, that one
    line is replaced in place with the new location instead.

    Other lines are never rewritten. Duplicates are checked against disabled
    (#) bookmarks too, as re-enabling one would otherwise collide.
    """
    name = name.strip().lower()
    if not name or any(c.isspace() for c in name) or name.startswith("#") or "'" in name:
        return "Use a short name without spaces, quotes or a leading #."
    if "'" in path:
        return "Paths containing a single quote cannot be stored."
    stale = False
    for loc in go.read_locations():
        if loc["mnemonic"] == name and not os.path.exists(loc["path"]):
            stale = True  # same name, old location gone: take the new location
        elif loc["mnemonic"].lstrip("#") == name:
            return f"A bookmark named \u201c{name}\u201d already exists."
    path_field = f"'{path}'"
    line = (f"{name:<12} {path_field}{' ' * max(1, 60 - len(path_field))} "
            f"{go.get_current_timestamp()} {go.get_type(path)}\n")
    if stale:
        try:
            with open(go.GO_LOCATIONS) as f:
                lines = f.readlines()
            for i, old in enumerate(lines):
                entry = go.parse_line(old)
                if entry and entry["mnemonic"] == name:
                    lines[i] = line  # only this line changes
                    break
            tmp = str(go.GO_LOCATIONS) + ".tmp"
            with open(tmp, "w") as f:
                f.writelines(lines)
            os.replace(tmp, go.GO_LOCATIONS)
        except OSError as err:
            return str(err)
        return None
    try:
        needs_newline = False
        if go.GO_LOCATIONS.exists() and go.GO_LOCATIONS.stat().st_size:
            with open(go.GO_LOCATIONS, "rb") as f:
                f.seek(-1, os.SEEK_END)
                needs_newline = f.read(1) != b"\n"
        with open(go.GO_LOCATIONS, "a") as f:
            f.write(("\n" if needs_newline else "") + line)
    except OSError as err:
        return str(err)
    return None


def delete_bookmark(name):
    """Remove the one enabled bookmark `name` from ~/.go_locations.

    Every other line (including comments and disabled ones) is kept byte for
    byte. Only the bookmark is removed, never the folder it points to.
    Returns an error message or None.
    """
    try:
        with open(go.GO_LOCATIONS) as f:
            lines = f.readlines()
        kept = []
        for line in lines:
            entry = go.parse_line(line)
            if entry and entry["mnemonic"] == name:
                continue
            kept.append(line)
        if len(kept) == len(lines):
            return f"\u201c{name}\u201d is no longer in the bookmarks file."
        tmp = str(go.GO_LOCATIONS) + ".tmp"
        with open(tmp, "w") as f:
            f.writelines(kept)
        os.replace(tmp, go.GO_LOCATIONS)
    except OSError as err:
        return str(err)
    return None


class Node(NSObject):
    """One row in the browser: a bookmark (first column) or a file/folder."""

    def initWithPath_label_(self, path, label):
        self = objc.super(Node, self).init()
        if self is None:
            return None
        self.path = path
        self.label = label
        self.folder = is_folder(path)
        self._children = None
        self.mnemonic = None  # set for first-column bookmarks only
        self.missing = False
        return self

    def children(self):
        if self._children is None:
            self._children = []
            try:
                names = sorted(os.listdir(self.path), key=str.lower)
            except OSError:
                names = []
            for name in names:
                if not name.startswith("."):
                    self._children.append(
                        Node.alloc().initWithPath_label_(
                            os.path.join(self.path, name), name))
        return self._children


class Root(NSObject):
    """The invisible root: the enabled bookmarks."""

    def init(self):
        self = objc.super(Root, self).init()
        self.folder = True
        self.reload()
        return self

    def reload(self):
        self._children = []
        for loc in go.sort_locations_alpha(go.read_locations()):
            if loc["mnemonic"].startswith("#"):
                continue
            missing = not os.path.exists(loc["path"])
            node = Node.alloc().initWithPath_label_(
                loc["path"],
                loc["mnemonic"] + ("   (missing)" if missing else ""))
            node.mnemonic = loc["mnemonic"]
            node.missing = missing
            self._children.append(node)

    def children(self):
        return self._children


class PreviewController(NSViewController):
    """Quick Look preview shown in the last column when a file is selected."""

    def initWithPath_(self, path):
        self = objc.super(PreviewController, self).init()
        view = QLPreviewView.alloc().initWithFrame_style_(
            NSMakeRect(0, 0, 320, 400), 0)  # QLPreviewViewStyleNormal
        view.setPreviewItem_(NSURL.fileURLWithPath_(path))
        self.setView_(view)
        return self


class Browser(NSBrowser):
    def keyDown_(self, event):
        if event.keyCode() in (36, 76):  # return, keypad enter
            self.target().openSelection_(self)
        elif event.keyCode() in (51, 117):  # delete, forward delete
            self.target().deleteBookmark_(self)
        else:
            objc.super(Browser, self).keyDown_(event)


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, _note):
        self.root = Root.alloc().init()
        self.mtime = self.bookmarks_mtime()

        style = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
                 | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 900, 500), style, NSBackingStoreBuffered, False)
        self.window.setTitle_("go bookmarks")
        # Stay above other windows, also while another app is frontmost. A
        # floating level is below sheets, alerts and menus, so those still work.
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setHidesOnDeactivate_(False)
        self.window.setFrameAutosaveName_("GoBrowserWindow")
        if not self.window.setFrameUsingName_("GoBrowserWindow"):
            self.window.center()

        content = self.window.contentView().bounds()
        bar = 34
        browser = Browser.alloc().initWithFrame_(
            NSMakeRect(0, bar, content.size.width, content.size.height - bar))
        add = NSButton.alloc().initWithFrame_(NSMakeRect(8, 4, 80, 26))
        add.setTitle_("Add\u2026")
        add.setBezelStyle_(1)  # rounded
        add.setTarget_(self)
        add.setAction_(b"addBookmark:")
        add.setAutoresizingMask_(32)  # NSViewMaxYMargin: stays pinned to the bottom
        delete = NSButton.alloc().initWithFrame_(NSMakeRect(96, 4, 90, 26))
        delete.setTitle_("Delete\u2026")
        delete.setBezelStyle_(1)
        delete.setTarget_(self)
        delete.setAction_(b"deleteBookmark:")
        delete.setAutoresizingMask_(32)
        delete.setEnabled_(False)
        self.delete_button = delete
        self.window.contentView().addSubview_(add)
        self.window.contentView().addSubview_(delete)
        browser.setDelegate_(self)
        browser.setTarget_(self)
        browser.setAction_(b"selectionChanged:")
        browser.setDoubleAction_(b"openSelection:")
        browser.setAutoresizingMask_(18)  # width | height sizable
        browser.setMinColumnWidth_(180)
        browser.setMaxVisibleColumns_(6)
        browser.setSeparatesColumns_(False)
        browser.setTitled_(False)
        browser.setHasHorizontalScroller_(True)
        browser.setAllowsMultipleSelection_(False)
        browser.setAllowsEmptySelection_(True)
        browser.setReusesColumns_(False)
        self.browser = browser
        self.window.contentView().addSubview_(browser)
        self.window.setInitialFirstResponder_(browser)
        self.window.makeKeyAndOrderFront_(None)
        self.window.makeFirstResponder_(browser)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, b"appActivated:", "NSApplicationDidBecomeActiveNotification", None)

    def applicationShouldTerminateAfterLastWindowClosed_(self, _app):
        return True

    # --- bookmark reloading -------------------------------------------------

    def bookmarks_mtime(self):
        try:
            return os.stat(go.GO_LOCATIONS).st_mtime
        except OSError:
            return 0

    def appActivated_(self, _note):
        if self.bookmarks_mtime() != self.mtime:
            self.reload_(None)

    def reload_(self, _sender):
        self.mtime = self.bookmarks_mtime()
        self.root.reload()
        self.browser.loadColumnZero()
        self.delete_button.setEnabled_(False)
        self.window.setTitle_("go bookmarks")

    # --- NSBrowser item-based delegate --------------------------------------

    def rootItemForBrowser_(self, _browser):
        return self.root

    def browser_numberOfChildrenOfItem_(self, _browser, item):
        return len(item.children()) if item.folder else 0

    def browser_child_ofItem_(self, _browser, index, item):
        return item.children()[index]

    def browser_isLeafItem_(self, _browser, item):
        return not item.folder

    def browser_objectValueForItem_(self, _browser, item):
        return item.label

    def browser_previewViewControllerForLeafItem_(self, _browser, item):
        if not os.path.exists(item.path):
            return None
        return PreviewController.alloc().initWithPath_(item.path)

    def browser_shouldShowCellExpansionForRow_column_(self, _b, _r, _c):
        return True

    # --- actions ------------------------------------------------------------

    def selectedItem(self):
        index = self.browser.selectedColumn()
        row = self.browser.selectedRowInColumn_(index)
        return self.browser.itemAtRow_inColumn_(row, index) if row >= 0 else None

    def selectedBookmark(self):
        """The selected first-column bookmark, or None."""
        item = self.selectedItem()
        if item is not None and item.mnemonic and self.browser.selectedColumn() == 0:
            return item
        return None

    def selectionChanged_(self, _sender):
        item = self.selectedItem()
        self.delete_button.setEnabled_(self.selectedBookmark() is not None)
        self.window.setTitle_(
            go_title(item.path) if item is not None else "go bookmarks")

    def addBookmark_(self, _sender):
        finder = front_finder_folder()
        stale = self.selectedBookmark()
        stale = stale if stale is not None and stale.missing else None
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Add bookmark")
        if stale:
            # A selected bookmark whose folder is gone: ask where it lives now.
            alert.setInformativeText_(
                f"\u201c{stale.mnemonic}\u201d no longer exists. Choose its new location.")
        elif finder:
            alert.setInformativeText_(f"Folder: {go_title(finder)}")
        else:
            alert.setInformativeText_(
                "No Finder window is open (or Finder access was refused), so you "
                "will be asked for the folder.")
        field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 260, 24))
        field.setPlaceholderString_("short name, e.g. proj")
        if stale:
            field.setStringValue_(stale.mnemonic)
        alert.setAccessoryView_(field)
        if finder and not stale:
            alert.addButtonWithTitle_("Add")
            alert.addButtonWithTitle_("Choose Folder\u2026")
        elif finder:
            alert.addButtonWithTitle_("Choose Folder\u2026")
            alert.addButtonWithTitle_("Use Finder Folder")
        else:
            alert.addButtonWithTitle_("Choose Folder\u2026")
        alert.addButtonWithTitle_("Cancel")
        alert.window().setInitialFirstResponder_(field)
        result = alert.runModal()
        titles = [b.title() for b in alert.buttons()]
        choice = titles[result - 1000] if 0 <= result - 1000 < len(titles) else "Cancel"
        name = str(field.stringValue())
        if choice == "Cancel":
            return
        if not name.strip():
            warn = NSAlert.alloc().init()
            warn.setMessageText_("Bookmark not added")
            warn.setInformativeText_("Enter a short name first.")
            warn.runModal()
            return
        path = finder
        if choice.startswith("Choose"):
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseDirectories_(True)
            panel.setCanChooseFiles_(True)
            panel.setPrompt_("Choose")
            if panel.runModal() != 1:
                return
            path = panel.URL().path()
        error = add_bookmark(name, path)
        if error:
            warn = NSAlert.alloc().init()
            warn.setMessageText_("Bookmark not added")
            warn.setInformativeText_(error)
            warn.runModal()
            return
        self.reload_(None)

    def deleteBookmark_(self, _sender):
        item = self.selectedBookmark()
        if item is None:
            return
        alert = NSAlert.alloc().init()
        alert.setMessageText_(f"Delete bookmark \u201c{item.mnemonic}\u201d?")
        alert.setInformativeText_(
            f"{go_title(item.path)}\n\n"
            + ("That location no longer exists. " if item.missing else "")
            + "Only the bookmark is removed from ~/.go_locations; "
              "nothing on disk is touched.")
        alert.addButtonWithTitle_("Delete")
        alert.addButtonWithTitle_("Cancel")
        if alert.runModal() != 1000:
            return
        error = delete_bookmark(item.mnemonic)
        if error:
            warn = NSAlert.alloc().init()
            warn.setMessageText_("Bookmark not deleted")
            warn.setInformativeText_(error)
            warn.runModal()
        self.reload_(None)

    def openSelection_(self, _sender):
        item = self.selectedItem()
        if item is not None:
            open_in_finder(item.path)


def go_title(path):
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path == home or path.startswith(home + "/") else path


def make_menu(app, delegate):
    main = NSMenu.alloc().init()

    app_item = NSMenuItem.alloc().init()
    main.addItem_(app_item)
    app_menu = NSMenu.alloc().init()
    app_menu.addItemWithTitle_action_keyEquivalent_("About gobrowser", b"orderFrontStandardAboutPanel:", "")
    app_menu.addItem_(NSMenuItem.separatorItem())
    app_menu.addItemWithTitle_action_keyEquivalent_("Hide gobrowser", b"hide:", "h")
    app_menu.addItem_(NSMenuItem.separatorItem())
    app_menu.addItemWithTitle_action_keyEquivalent_("Quit gobrowser", b"terminate:", "q")
    app_item.setSubmenu_(app_menu)

    file_item = NSMenuItem.alloc().init()
    main.addItem_(file_item)
    file_menu = NSMenu.alloc().initWithTitle_("File")
    reload_item = file_menu.addItemWithTitle_action_keyEquivalent_("Reload Bookmarks", b"reload:", "r")
    reload_item.setTarget_(delegate)
    file_menu.addItemWithTitle_action_keyEquivalent_("Close Window", b"performClose:", "w")
    file_item.setSubmenu_(file_menu)

    app.setMainMenu_(main)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    make_menu(app, delegate)
    app.run()


if __name__ == "__main__":
    main()
