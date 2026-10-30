# go.claude

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

Download `go.claude-1.0.1.dmg` from the
[latest release](https://github.com/spurious-cox/go.claude/releases/latest)
(signed with a Developer ID and notarized by Apple), or just copy the
`go.claude` file from this repository. Put it somewhere on your machine, for
example `~/bin/`, and make it executable:

```sh
mkdir -p ~/bin && cp go.claude ~/bin/ && chmod +x ~/bin/go.claude
```

Then add this function to your `~/.zshrc` (it is needed so that `go` can
change the directory of your current shell):

```sh
go() { noglob eval $(python3 ~/bin/go.claude "$@"); }
```

Open a new terminal and run `go -help`.

## Usage

```
go - Quick location bookmarking and navigation tool

USAGE:
    go                          List all locations
    go mnemonic                 Navigate to or open location
    go -add|-a [-f] mnemonic path  Add a new location (-f to force if path doesn't exist)
    go -disable|-d mnemonic     Disable a location (prefix with #)
    go -repair|-r mnemonic path Update path and re-enable location
    go -which|-w mnemonic       Show the path for a mnemonic
    go -quicklook|-q mnemonic   Open location in QuickLook
    go -find|-fn mnemonic       Open location in Finder
    go -edit|-e mnemonic        Edit a file location in $EDITOR
    go -sort|-s                 List locations sorted by date
    go -help|-h                 Show this help message

LOCATION TYPES:
    d - directory (changes to directory)
    f - file (opens in $EDITOR)
    m - macOS document (.numbers, .pages, .key, etc. - opens with default app)
    e - executable (runs the file)
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
    - For directory navigation, add to .zshrc:
      go() { noglob eval $(python3 ~/bin/go.claude "$@"); }
```

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
