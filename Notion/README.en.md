<!-- version: 1.0.5 -->
[繁體中文](README.md) | **English** | [日本語](README.ja.md) | [ไทย](README.th.md) | [हिन्दी](README.hi.md)

# Notion

A local sticky-notes app for Windows. One folder per day, one file per note, everything stays on your own PC: no cloud, no account, nothing collected.
Written in Python 3.12 (UI: tkinter + customtkinter; packaged with PyInstaller).

> This folder shares only the tool's code and architecture. It contains no user notes or other data.

![Main window (English)](docs/main-en.png)

| Traditional Chinese UI (light) | Settings (tabs) |
|---|---|
| ![Main window (zh-TW)](docs/main-zh.png) | ![Settings](docs/settings-en.png) |

The side panel lists notes by day; the ☆ before a title marks a favorite. The middle is the title and text: `==highlight==`, `!!red!!`, `**bold**` are coloured as you type, ``` blocks get a Copy button, and screenshots show inline. Language, shortcuts, side-panel position and updates are all under ⚙ Settings at the top right.

## Features

| Feature | What it does |
|---|---|
| Notes by day | One group per day in the side panel, as many notes per day as you like; click a day to fold it; long-press a note and drag to reorder within the day; "Add elsewhere" picks a date first (for back-filling); "+ New note" / Ctrl+N always adds to today |
| Favorites | Click the ☆ before a title to make it ★; a "★ Favorites" group appears at the top (below To-do) and opens the note when clicked; click again to remove |
| To-do | A fixed red "To-do" note at the very top that belongs to no date (stored in the `9999-12-31` folder, so it always sorts first) |
| Checklists | A line starting with `- [ ] ` (format bar "Check" or typed) becomes a box; click to tick, done items are struck through; the file holds GitHub-style `- [x]` |
| #tags | `#projectA` in the text shows in the accent colour; Ctrl+click searches that tag in the side panel |
| Right-click menus | Text and title: cut, copy, paste (a screenshot on the clipboard becomes an image), select all, copy as plain text; note rows: open, copy to today, export, older versions, favorite, share, delete; day headers: add here, export the day as one `.md`, clear the day |
| Auto-save | Saves 1.2 s after you stop typing, and on switching or closing; if saving fails a rescue file is kept |
| Markup | Select text and mark `==highlight==` (yellow), `!!warning!!` (red), `**bold**`, `*italic*`; the file stores the marks, so exports stay readable. Marks are hidden except on the cursor line |
| Command blocks | ``` blocks are monospaced on a dark background with a "Command | Copy" header that copies the whole block (commands, prompts) |
| Links | URLs and Windows paths (including `\\server\...`) become links; Ctrl+click opens; executables ask first |
| Images and files | Ctrl+V pastes a screenshot inline, drag the corner handle to resize; drop `.md` / `.txt` (up to 1 MB) into the window to make today's notes; other files are not accepted (use 📎 for attachments) |
| Lists | `1. ` / `- ` at the start of a line continues on Enter |
| Search | Ctrl+F, by date or text; shows "Searching" for large sets |
| Shortcuts | Settings → Shortcuts: every action can get its own key combination; it must include Ctrl or Alt, system copy/paste keys are reserved, two actions can never share one; reset all to defaults |
| Encryption | On by default, using the Windows account (DPAPI): a drive moved to another PC cannot be read; "Export all" before changing PCs. Details: [docs/加密與本機說明.md](docs/加密與本機說明.md) (a .txt copy is in the zip) |
| Import / export | Export one note, a whole day (as one file) or everything as plain `.md`; import `.md` / `.txt` (UTF-8, UTF-16, Big5, GBK, Shift-JIS are detected) |
| Versions and trash | Every note keeps older snapshots (right-click "Older versions…" to view or restore; restoring also keeps the current content); deleted notes go to the trash first, "Restore last delete" brings them back |
| Share | Right-click a note → Share: send by email (opens your mail app, subject = title, body = plain text) or copy to the Google Drive desktop sync folder (you pick a folder if it is not found) |
| Languages | English (default), Traditional Chinese, Simplified Chinese, Japanese; switch under Settings → Appearance without restarting; the translation table is one csv, add a column to add a language |
| Updates | A few seconds after start, the app checks GitHub Releases for a newer version (reads the version number only). If there is one it reminds you: download the zip, skip this version, or turn reminders off (Settings → Update). Updating = close the app and replace `Notion.exe`; notes and settings are untouched |
| Quick tour | A five-page tour on first launch, shown once; Settings → Update shows it again |
| Appearance | Light / system / dark; Ctrl+wheel zoom; side panel on the left, right or bottom, width draggable; collapsible format bar; empty-note hint; "Saved" fades out; dialogs open centred on the main window |
| Other | Single instance; splash screen; progress for long actions; line and character counts; the "today" marker moves on its own after midnight |

## How to use

**Just use it**: take the packaged zip (`Notion.exe` + `Notion.bat` + the two .txt guides, produced by `tools/make_release.py`) and unzip it anywhere.

**Clone and hack** (this folder has no exe):
```
pip install -r requirements.txt
python -m personalnote          # run
build_exe.bat                   # or build dist\Notion.exe (runs the tests first)
```
Double-clicking `Notion.bat` in this folder also works: when it finds no exe it checks Python and the packages and tells you what is missing.

1. Needs Windows 10 / 11 (64-bit). The packaged version needs nothing installed.
2. Run `Notion.bat` (the .bat can set the notes folder, language, font, whether to check for updates, etc.; blank = use the in-app settings). The first time, Windows may show "Windows protected your PC" → "More info" → "Run anyway" (the exe is not signed).
3. Notes are stored in the `Notion` folder on the Desktop by default; change it under ⚙ Settings → Files.
4. Start with Windows: Win+R, type `shell:startup`, and drop a shortcut to `Notion.bat` there (Settings → Files has an "Open startup folder" button).

Shortcuts (defaults; change them in Settings): Ctrl+N new note (today), Ctrl+T today, Ctrl+F search, Ctrl+S save now, Ctrl+\ toggle side panel, Ctrl+PgUp / PgDn previous / next day, Ctrl+H / Ctrl+Shift+H highlight / red, Ctrl+B / I bold / italic, Ctrl+Shift+C command block, Ctrl+= / Ctrl+- font size.

## Where the data lives

```
Notion/                       ← notes folder (back up the whole thing)
  2026-10-28/001.note         ← one file per note; .note encrypted, .md plain; first line "# Title"
  attachments/                ← pasted images and attachments (not encrypted)
  .app/settings.json          ← in-app settings (incl. shortcuts, update reminders); state.json window state and panel position;
                                 order.json manual ordering; favorites.json; history/ snapshots; trash/; error.log
%APPDATA%\PersonalNote\logs   ← personalnote.log, crash.log (hang stacks); rescue/ rescue files
```

What encryption covers: note text and snapshots. Attachments, exported .md files and file names in the trash are not encrypted. Encryption is bound to the Windows account: a new PC, a reinstall or a deleted account cannot open the notes, so export everything first.

The app never connects to anything except one read of the version number on GitHub at startup; `set NOTE_UPDATE_CHECK=0` in `Notion.bat` turns even that off.

## Architecture (for maintainers)

```
personalnote/
  __init__.py       APP_NAME, __version__, AUTHOR
  app.py            entry point: log → settings → language → single instance → NoteStore → MainWindow; --startup (Linux)
  config.py         Settings: command line > environment (.bat) > user-chosen folder > settings.json > defaults (see file header for how to add one)
  storage.py        NoteStore: index and title cache, read/write (.tmp + fsync + rename), encoding detection, clear and trash, attachments, snapshots, import/export, favorites, format version
  crypto.py         DPAPI encryption; compatibility constants (do not change)
  i18n.py           _("zh-TW source") → the matching column of assets/lang/strings.csv; the language list comes from the columns
  markup.py         inline marks and ``` blocks (pure text processing)
  links.py / listing.py / imefix.py   link detection, list continuation, IME punctuation fix
  dropfiles.py      drag-and-drop (Windows WM_DROPFILES; the callback never touches Tk, an after() poll delivers the files)
  keys.py           shortcut table: defaults, rules (Ctrl/Alt required, system keys reserved, no duplicates), "Ctrl+Shift+N" → tk sequences
  update.py         update check: GitHub Releases latest, version number only
  platform_.py      everything OS-specific: paths, opening files, fonts, icons, single instance, autostart
  state.py / startup.py / applog.py   window state, autostart (Linux), log and watchdog
  ui/theme.py       colours, spacing, fonts, date format, dialog centring
  ui/sidebar.py     side panel (reports clicks only, never touches files)
  ui/editor.py      text box: auto-save, colouring, images, format bar, counts, key bindings
  ui/datepick.py    date picker; ui/versions.py older-versions dialog
  ui/main_window.py wiring: toolbar, menus, import/export, drag-and-drop, settings (tabs), update prompt, tour, rebuild on language change
tests/              unittest (incl. the compatibility fixture tests/fixtures/v1.0.0, do not edit)
tools/              make_release.py (checks, zip, --publish), check_strings.py (translation table), lang_seed.py,
                    make_icons.py, make_splash.py, make_version_file.py, check_public_words.py, stress/
assets/             icons, splash, lang/strings.csv
docs/               screenshots, encryption and local-only notes
```

Rules:
- File I/O only in `storage.py`, `config.py`, `state.py`; UI widgets report through callbacks and the main window wires them.
- All UI text goes through `_("zh-TW source")`; never call `_()` in module-level constants (the language is not set yet). After adding strings run `python tools/check_strings.py` and fill the empty cells in the csv.
- The constants in `crypto.py`, the `.note` header and the `format.json` upgrade rules must not change, or old notes stop opening. Changing the format means bumping the version and keeping the old reader.
- Adding a setting touches the 7 places listed in the `config.py` header; missing one fails silently.
- Never call tkinter inside the Windows message callback (dropfiles): the C runtime terminates the process.
- On every version bump, update the `<!-- version -->` line in all five READMEs; `make_release.py` checks it.

## Development and packaging

```
pip install -r requirements.txt
python -m personalnote                 # run
python -m unittest discover -s tests   # unit tests
python tools/stress/ui_checks.py       # drives a real window (placed off-screen)
build_exe.bat                          # build dist\Notion.exe (runs tests and the translation check first)
python tools/make_release.py --dest <folder> [--publish]   # release folder + zip; --publish uploads to GitHub Releases (needs gh)
python tools/check_public_words.py     # scan for words that must not appear before committing
```

## Supported systems and licences

- Windows 10 / 11 is the main platform; Windows 7 / 8.0 cannot run it (Python 3.12 needs 8.1+), `Notion.bat` explains and stops.
- Linux: everything OS-specific is in `platform_.py`; `Notion.sh` / `build_linux.sh` run and package it; no encryption or drag-and-drop; not yet tested on real hardware.
- No font files are shipped; system fonts are named. Third-party components: Python (PSF), Tcl/Tk (BSD-style), customtkinter (MIT), Pillow (MIT-CMU), PyInstaller (GPL with exception).

## Known limits

- Encryption is bound to the Windows account (see above). "Change folder" does not move old notes.
- Images resize proportionally from the corner handle only; GIFs do not animate.
- On an abrupt Windows shutdown the last 1.2 s of typing may be lost.
- Two instances on the same folder (e.g. RDP and local) are not protected against; the later save wins.
- The side panel lists at most 1000 notes at once; use search for the rest.
- The exe is unsigned, so SmartScreen blocks it once on first run.
