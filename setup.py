"""py2app build for gobrowser.app (the `go -g` window)

    ./venv/bin/python setup.py py2app

Built on the python.org Python (universal2). The goclaude script is bundled
as a resource so the app reads bookmarks with the CLI's own parser.
"""

import re
from pathlib import Path

from setuptools import setup

APP = ["gobrowser.py"]
DATA_FILES = [("", ["goclaude"])]


def app_version():
    source = Path(__file__).with_name("gobrowser.py").read_text()
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', source, re.MULTILINE)
    if not match:
        raise SystemExit("setup.py: APP_VERSION not found in gobrowser.py")
    return match.group(1)


VERSION = app_version()

OPTIONS = {
    "argv_emulation": False,
    "arch": "universal2",
    "excludes": ["tkinter", "test", "unittest", "pydoc_data"],
    # goclaude is bundled as a data file, so py2app can't see its imports: list them here.
    "includes": ["importlib.machinery", "importlib.util", "subprocess", "json", "datetime"],
    "plist": {
        "CFBundleName": "gobrowser",
        "CFBundleDisplayName": "gobrowser",
        "CFBundleIdentifier": "com.timmccoy.gobrowser",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSAppleEventsUsageDescription":
            "gobrowser asks Finder for the front window's folder when you add a bookmark.",
        "NSHumanReadableCopyright": "© 2026 Tim McCoy",
    },
}

setup(
    app=APP,
    name="gobrowser",
    version=VERSION,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
