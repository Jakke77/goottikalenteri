# Goottikalenteri

Modular Python / PyQt6 desktop application intended for Ubuntu 26.04 and 26.10
with GNOME. Finnish interface, dark charcoal backgrounds and neon blue highlights.

## Packages and installation

Required: Python 3 and PyQt6. Install Ubuntu packages and launch:

```bash
sudo apt update
sudo apt install python3 python3-pyqt6
cd goottikalenteri
python3 main.py
```

Alternatively install `python3-venv`, then:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Qt automatically selects Wayland or X11. The Ubuntu package installation supplies
Qt's system dependencies. The application requires no runtime network connection.

## Calendar

Years begin at 0001; each has exactly 13 months (0–12) and 30 days per month (0–29).
One year is 390 days. Days last 24 hours; weeks have seven days, Monday to Sunday.
The user's parallel-calendar anchor is Sunday 4 October 2026 = year 0001,
month 0 (Varjojenkuu), day 6. Therefore day 0 is Monday 28 September 2026.
Weekdays continue across month boundaries. All visible dates and years use only the fictional calendar. Gregorian
dates are used internally to determine today from the computer clock. The app opens on today's fictional date using the computer's local
date; before the epoch it opens at day 0. “Tänään” returns to today.

Day 0 is always a fictional new moon. The full moon at day 15 and intermediate
phase labels are symbolic, not astronomical predictions. There are no leap days.
This is a date calendar, not a clock or alarm application; daylight saving does
not change its date arithmetic. Local midnight controls the today marker.
There is no application-imposed maximum year. Both timelines continue beyond
year 9999 using integer arithmetic. ‘Siirry vuoteen…’ jumps directly to any positive
year. Practical limits are available memory, display width, and Python's integer
text-conversion limit. The 390-day year naturally drifts relative to Gregorian years,
while both calendars refer to the same passing days.

## Events

Click a day to edit its plain-text note. Enter multiple events on separate lines.
“Tallenna” saves, “Peruuta” cancels, “Poista” deletes after confirmation.
Saving blank text removes the note. Notes persist between restarts.

Default storage uses Qt's XDG application-data location, normally
`~/.local/share/Goottikalenteri/events.json`. The exact path is shown in the status
bar. Override with `python3 main.py --data-file /absolute/path/events.json`.
JSON structure:

```json
{"version": 1, "events": {"0001-02-05": "Example note"}}
```

Writes use a private temporary file and atomic replacement. Failed writes preserve
the previous data and leave the editor open. Malformed JSON or invalid dates stop
startup without overwriting the file; repair or back up that file before restarting.
A file lock prevents simultaneous application instances writing the same file.
Back up events.json as needed; it contains plain text.

## Keyboard and GNOME

Tab moves focus; Space/Enter activates day buttons. Alt+Left/Right changes month,
Alt+Up/Down changes year. Ctrl+Enter saves the editor; Escape cancels.
Scalable native widgets, automatic Qt display scaling, and a scrollable grid support
GNOME displays. The Fusion palette keeps the entire application dark regardless
of the desktop's light/dark preference.

Optional GNOME launcher: copy `goottikalenteri.desktop` to
`~/.local/share/applications/`. Its Exec path points to this project location;
update it if you move the files or use a virtual environment.

## Modules and validation

`main.py`: startup, palette, data location and locking.
`calendar_model.py`: custom dates, lunar labels, parallel dates and weekdays.
`storage.py`: validated JSON and atomic writes.
`ui.py`: calendar grid and note editor.

```bash
python3 -m unittest discover -s tests -v
```

Calendar/storage tests, Python compilation and offscreen PyQt6 GUI tests were run.
The GUI checks verify transparent background pixels, font resizing, preview cancellation,
persistent settings and standalone controls. The widget and settings were rendered
and visually inspected. Actual Ubuntu GNOME/Wayland desktop integration remains
untested; the offscreen checks do not simulate a compositor.

## Transparent desktop clock

Launch only the compact Conky-style clock, without the main calendar window:

```bash
python3 main.py --widget-only
```

The desktop widget contains only neon text: local time, weekday/day, month name,
and fictional year. There is no painted background, border, title bar, month grid
or visible button. Gregorian dates never appear in it. The background is fully
transparent; text opacity is configurable separately.

Drag the text to reposition it. Right-click or double-click the text to open its
separate settings window. Right-click also provides “Avaa kalenteri”, “Piilota widget”
and “Lopeta”. In widget-only mode, closing the calendar keeps the clock running;
“Lopeta” exits. Hiding the widget opens the calendar so its controls remain accessible.

Settings include font family, separate clock/date/year sizes, text color, text opacity,
seconds, alignment, position locking and optional always-on-top behavior. Appearance
changes preview immediately on an enabled widget; “Tallenna” persists them and
“Peruuta” restores the previous appearance. The enabled flag, appearance and position
are stored in Qt's XDG configuration. Widget settings are also accessible through
the main calendar's “Asetukset” button.

The clock is a transparent frameless Qt surface, not a GNOME Shell extension.
The compositor controls stacking and placement. On Wayland, native drag movement
is used, but exact saved-position restoration is not guaranteed. On X11,
transparency requires compositing. See the official Qt documentation:
https://doc.qt.io/qt-6/qwindow.html#startSystemMove
https://doc.qt.io/qt-6/qwidget.html#creating-translucent-windows

An optional `goottikalenteri-widget.desktop` launcher starts only the clock.
Copy it to `~/.local/share/applications/` and update its Exec path if needed.

## Full calendar navigation

The month dropdown selects any of the 13 months. “Vuoden kaikki kuukaudet” opens
a year overview with all 13 months and each month's note count; click a month to
open it. “Siirry vuoteen…” changes the year directly without changing the selected
month. Previous/next month navigation crosses year boundaries automatically.
Every day of every year supports its own persistent note. Main window, note dialogs,
year overview and desktop widget display only fictional dates and years.

## License

MIT License. Copyright (c) 2026 Jakke77. See [LICENSE](LICENSE).

## AppImage download and build

The private GitHub release provides an x86_64 AppImage with Python and PyQt6 bundled.
Download it from https://github.com/Jakke77/goottikalenteri/releases (requires repository access),
then run:

```bash
chmod +x Goottikalenteri-0.1.0-x86_64.AppImage
./Goottikalenteri-0.1.0-x86_64.AppImage
./Goottikalenteri-0.1.0-x86_64.AppImage --widget-only
```

If FUSE mounting is unavailable, the AppImage runtime supports extraction and execution:

```bash
./Goottikalenteri-0.1.0-x86_64.AppImage --appimage-extract-and-run --widget-only
```

The app requires a Linux desktop, x86_64 and glibc at least 2.43 in this build.
It is intended for Ubuntu 26.04 and 26.10; other/older Linux distributions are not
claimed compatible. Only offscreen smoke tests were performed, not clean GNOME
installations. User notes/settings remain outside the read-only AppImage.

To build from source on x86_64 Ubuntu 26.04 (recommended baseline):

```bash
sudo apt install python3-venv binutils squashfs-tools
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python packaging/build_appimage.py --version 0.1.0
```

The script uses a PyInstaller onedir bundle inside the AppImage, an original SVG
icon, pinned SHA-256 checks for the official packaging tool and runtime, source
archive and license notices. It smoke-tests the resulting AppImage and writes
`release-assets/SHA256SUMS` plus `build-info.json`. Build outputs are excluded from Git.
The continuous upstream tooling downloads are pinned to this release's checksums;
if upstream replaces them, review new tooling before updating those pins.

Run the isolated packaged smoke test with `--self-test` (uses temporary data).
The original code is MIT; bundled dependencies retain their own licenses, including
PyQt6 GPLv3. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
