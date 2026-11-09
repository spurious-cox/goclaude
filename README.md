# goclaude

A small command-line tool for bookmarking places on your Mac and jumping to
them with a short name. A bookmark can be a folder, a file, a document, a
program or an app, and `go <name>` does the sensible thing for each: it changes
into a folder, opens a file in your editor, launches an app, and so on.

It is one Python 3 script with no dependencies beyond the standard library.
macOS only (it uses `open` and `qlmanage`).

## History

`go` began as a UNIX shell script for jumping between directories. It was then
carried over to Linux shell scripting, and later rewritten again as a macOS
shell script. This version is the final stage: a Python tool enhanced with
Claude (Anthropic) that adds file, document, app and executable bookmarks,
partial-name matching, QuickLook, Finder reveal and in-place repair of moved
locations, on top of the original idea.

## Install

Download `goclaude-1.5.0.dmg` from the
[latest release](https://github.com/spurious-cox/goclaude/releases/latest)
(signed with a Developer ID and notarized by Apple), or just copy the
`goclaude` file from this repository. Put it somewhere on your machine, for
example `~/bin/`, and make it executable:

```sh
mkdir -p ~/bin && cp goclaude ~/bin/ && chmod +x ~/bin/goclaude
```

To use `go -g`, also drag `gobrowser.app` from the disk image into
`/Applications` (see [gobrowser](#gobrowser-go--g)).

Then add this function to your `~/.zshrc` (it is needed so that `go` can
change the directory of your current shell):

```sh
go() { noglob eval $(python3 ~/bin/goclaude "$@"); }
```

Open a new terminal and run `go -help`.

## Usage

```
go - Quick location bookmarking and navigation tool

USAGE:
    go                          List all locations (alphabetical)
    go mnemonic                 Navigate to or open location
    go name                     If not a mnemonic: cd to / open that file or directory here
    go -add|-a [-f] mnemonic path  Add a new location (-f to force if path doesn't exist)
    go -disable|-d mnemonic     Disable a location (prefix with #)
    go -repair|-r mnemonic path Update path and re-enable location
    go -which|-w mnemonic       Show the path for a mnemonic
    go -quicklook|-q mnemonic   Open location in QuickLook
    go -find|-fn mnemonic       Open location in Finder
    go -edit|-e mnemonic        Edit a file location in $EDITOR
    go -gui|-g                  Browse locations in a Finder-like window (needs
                                gobrowser.app in /Applications; see README)
    go -sort|-s                 List locations sorted by date
    go -help|-h                 Show this help message

LOCATION TYPES:
    d - directory (changes to directory)
    f - file (opens in $EDITOR)
    m - macOS document (.numbers, .pages, .key, etc. - opens with default app)
    e - executable (runs binaries; scripts and dotfiles open in $EDITOR)
    b - bundle/app (opens with 'open' command)

EXAMPLES:
    go -add proj ~/projects/myapp
    go -a -f future ~/projects/notyet    # Add path that doesn't exist yet
    go proj                              # Navigate to ~/projects/myapp
    go -which proj                       # Show path: /home/user/projects/myapp
    go -q proj                           # Open in QuickLook
    go -d proj                           # Disable the 'proj' mnemonic
    go -r proj ~/projects/newapp         # Repair with new path

NOTES:
    - Locations are stored in ~/.go_locations
    - Partial mnemonics work if unambiguous (e.g., 'pro' matches 'projects')
    - Disabled locations (prefixed with #) are ignored in searches
    - -g opens gobrowser.app: a floating window, macOS 11+. Its Add... button
      needs Finder automation permission (System Settings > Privacy & Security
      > Automation); if denied, use Choose Folder...
    - Stache 2.22.0+ can also save the front Finder folder here with its hotkey
    - For directory navigation, add to .zshrc:
      go() { noglob eval $(python3 ~/bin/goclaude "$@"); }
```

## gobrowser (`go -g`)

`go -g` opens gobrowser, a small native window that looks like Finder's column
view. The first column lists your enabled bookmarks, in alphabetical order, from `~/.go_locations`;
click a folder to walk into it, click a file to preview it with Quick Look.

- **Return** or **double-click** opens the selected folder in Finder, or
  reveals the selected file there (the same as `go -find`).
- **Add…** (bottom left) asks for a short name and saves the front Finder
  window's folder as a bookmark, or a folder you choose. Duplicate names are
  refused and only one line is appended to `~/.go_locations`. If the name
  belongs to a bookmark whose location no longer exists, that bookmark takes
  the new location instead of being refused. If you select such a `(missing)`
  bookmark first, **Add…** pre-fills its name and asks for the new folder.
- **Delete…** (beside Add…) removes the selected first-column bookmark from
  `~/.go_locations` after a confirmation (the Delete or Backspace key does the same); use it for locations that no longer
  exist, which are marked `(missing)`. Only that one line goes; the folder
  itself and all other lines are untouched.
- **Cmd-R** reloads the bookmarks; they also reload when you switch back to
  the window after `~/.go_locations` changed. Disabled (`#`) bookmarks are not
  shown.
- **The window stays on top** of other windows, also while another app is in
  front. It stays below alerts, sheets and menus. Finder windows that open
  underneath it can be partly covered: move gobrowser aside.

### Requirements

- **gobrowser.app in `/Applications`** (or `~/Applications`). Without it
  `go -g` prints an error. Get it from the disk image of the
  [latest release](https://github.com/spurious-cox/goclaude/releases/latest)
  (drag it to Applications), or build it yourself (below). The `goclaude`
  script itself needs nothing but Python 3.
- **macOS 11 or later**, Apple silicon or Intel (the app is universal).
- **Finder automation permission** for gobrowser, only for **Add…**: it asks
  Finder for the front window's folder. macOS asks the first time; you can
  change it later in System Settings > Privacy & Security > Automation. If you
  deny it, **Add…** says no Finder window is available and you can still use
  **Choose Folder…**; browsing and opening are unaffected.
- macOS may also ask once to let gobrowser read folders such as Documents,
  Downloads or Desktop when you click into them.

### Saving a Finder folder from Stache

Stache 2.22.0 or later can save the front Finder window's folder into
`~/.go_locations` with its hotkey, using the same format. Stache needs the same
Finder automation permission.

### Building it

gobrowser is PyObjC packaged with py2app, signed and notarized. It reads the
bookmarks with the parser from the `goclaude` script itself, so the script
stays standard-library only: `go -g` just runs `open gobrowser.app`. To build:
`python3 -m venv venv && venv/bin/pip install py2app pyobjc-framework-Cocoa
pyobjc-framework-Quartz`, then `./build.sh` (builds, signs and installs to
`/Applications`; `--no-install` leaves it in `dist/`). `release.sh` notarizes it
and makes the disk image. `check_open.py` is a manual check that drives the real
Finder; read its header first.

## How it works

- **Mnemonics are lowercase** and may be shortened to any unambiguous prefix:
  with `projects` and `photos` saved, `go pro` goes to `projects`, while `go p`
  lists both and exits.
- **Types are detected when you add a location**: `.app` is a bundle (`b`), a
  directory is `d`, a Numbers/Pages/Keynote/Office/LibreOffice/CSV file is a
  macOS document (`m`), an executable is `e`, and anything else is a file
  (`f`). A location that does not exist yet (added with `-f`) is stored with
  type `?` and is typed when you first use it.
- **CSV files** are not opened automatically. `go` prints the commands for
  Numbers, LibreOffice and your editor so you can pick one.
- **Disabling** a location puts `#` in front of its mnemonic so it is skipped.
  `go -repair` points it at a new path and re-enables it.
- **Messages go to stderr; the shell command goes to stdout**, which is what
  lets the `go()` function above `eval` a `cd` without being confused by
  informational text.

### The bookmarks file

`~/.go_locations` is plain text, one location per line, easy to edit by hand:

```
proj         '/Users/you/projects/myapp'                  261001.093015 d
```

The columns are the mnemonic, the quoted path, a `yymmdd.HHMMSS` timestamp
and the type letter.

## License

MIT. See [LICENSE](LICENSE). Copyright (c) 2026 Timothy McCoy.
