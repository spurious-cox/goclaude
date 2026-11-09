#!/usr/bin/env python3
"""Regression check: double-click and Return in gobrowser reveal in Finder.

WARNING: this drives the REAL Finder and the real mouse and keyboard. It posts
a double-click and a Return into the gobrowser window, which makes Finder open
/etc. It never closes or moves windows that were already open: it remembers
the ids of the Finder windows that exist beforehand and closes only a window
it created itself. If /etc is already open in one of your windows, Finder just
reuses that window and the check leaves it alone.

Needs gobrowser running with a bookmark called `etc` (-> /etc) visible in the
first column, and Accessibility permission for the terminal running this.
Run: python3 check_open.py
"""
import subprocess, sys, time
from Quartz import (CGEventCreateMouseEvent, CGEventPost, CGEventSetIntegerValueField,
                    CGEventCreateKeyboardEvent, kCGEventLeftMouseDown, kCGEventLeftMouseUp,
                    kCGHIDEventTap, kCGMouseButtonLeft, kCGMouseEventClickState)

NAME, WANT = "etc", "/private/etc/"


def osa(script):
    return subprocess.run(["osascript", "-e", script], capture_output=True, text=True).stdout.strip()


def row_center():
    out = osa('''tell application "System Events" to tell process "gobrowser"
    set col to list 1 of scroll area 1 of scroll area 1 of browser 1 of window 1
    repeat with i from 1 to (count of UI elements of col)
        try
            set e to UI element i of col
            if value of e is "%s" then
                set {p, s} to {position of e, size of e}
                return (((item 1 of p) + (item 1 of s) / 2) as text) & "," & (((item 2 of p) + (item 2 of s) / 2) as text)
            end if
        end try
    end repeat
end tell''' % NAME)
    if not out:
        sys.exit(f"bookmark row '{NAME}' not found in the gobrowser window")
    x, y = out.split(",")
    return float(x), float(y)


def mouse(x, y, clicks):
    for n in range(1, clicks + 1):
        for t in (kCGEventLeftMouseDown, kCGEventLeftMouseUp):
            e = CGEventCreateMouseEvent(None, t, (x, y), kCGMouseButtonLeft)
            CGEventSetIntegerValueField(e, kCGMouseEventClickState, n)
            CGEventPost(kCGHIDEventTap, e)
            time.sleep(0.05)


def finder_front():
    return osa('tell application "Finder" to if (count of Finder windows) > 0 then '
               'POSIX path of (target of front Finder window as alias)')


def window_ids():
    out = osa('tell application "Finder" to get id of every Finder window')
    return {i.strip() for i in out.split(",") if i.strip()}


def close_new(before):
    """Close only the Finder windows that did not exist before the action."""
    for wid in window_ids() - before:
        osa(f'tell application "Finder" to close (first Finder window whose id is {wid})')


failed = False
for label, action in (("double-click", lambda x, y: mouse(x, y, 2)),
                      ("Return", lambda x, y: (mouse(x, y, 1), time.sleep(0.5),
                                               osa('tell application "System Events" to key code 36')))):
    before = window_ids()
    x, y = row_center()
    action(x, y)
    time.sleep(2)
    got = finder_front()
    close_new(before)
    ok = got == WANT
    failed |= not ok
    print(f"{'PASS' if ok else 'FAIL'}  {label}: Finder front window = {got or 'none'}")
sys.exit(1 if failed else 0)
