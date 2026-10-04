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
Qt's system dependencies. Calendar and notes work offline; scheduled clock checks use the public NTP service.

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
or visible button. A smaller bottom line also shows the official Finnish date, e.g.
`1. heinäkuuta 2026`. Its font size is adjustable in settings. The background is fully
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

## Two AppImage launchers

The private GitHub release provides two independent x86_64 downloads, with Python
and PyQt6 included. Choose the calendar or the transparent desktop clock:

```bash
chmod +x Goottikalenteri-0.2.2-x86_64.AppImage Goottikalenteri-widget-0.2.2-x86_64.AppImage
./Goottikalenteri-0.2.2-x86_64.AppImage
./Goottikalenteri-widget-0.2.2-x86_64.AppImage
```

The calendar package opens only the calendar by default. The widget package opens
only the clock; no command-line switch is needed. Both are self-contained, so you
can download just the one you want. The widget's context menu can still open the
full calendar. Either package also accepts `--calendar` or `--widget-only` to override
its default. Neither enables automatic login startup.

If one package is already running, the other launcher tells that process to display
the calendar or widget. Both views can remain open together while one process owns
the event file. A repeated launch does not create duplicate clocks. Closing the
calendar after launching the widget leaves the clock running; use its right-click
“Lopeta” command to exit everything. Notes and font settings are shared.

Download from https://github.com/Jakke77/goottikalenteri/releases (requires access).
If FUSE mounting is unavailable, add `--appimage-extract-and-run` before the app
arguments. Notes and settings remain outside the read-only AppImage.

Target: x86_64 Linux desktops, including Ubuntu 26.04 and 26.10. The release's
`build-info.json` records the required glibc symbol version. Offscreen tests verify
both launch modes, calendar logic, IPC, font settings and background transparency;
actual clean GNOME/Wayland installations remain untested.

Build both packages on Linux x86_64:

```bash
sudo apt install python3-venv binutils squashfs-tools
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python packaging/build_appimage.py --version 0.2.2 --variant both
```

Use `--variant calendar` or `--variant widget` to build just one. The script puts a
PyInstaller onedir bundle inside each AppImage, includes original source/license
notices, checks pinned official tooling hashes, and tests the launcher's default mode.
Outputs, source ZIP, `build-info.json` and `SHA256SUMS` go into `release-assets/`,
which is excluded from Git. Each archive includes build instructions and the
GitHub Actions release workflow. Actions builds both images on Ubuntu 24.04 when
a release is published, tests them and uploads the assets to that private release.
The workflow can also be run manually for an existing release tag.

The original code is MIT. Bundled dependencies retain their own licenses, including
PyQt6 GPLv3; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

### Ajan tarkistus

Sovellus tarkistaa ajan julkiselta `time.mikes.fi`-NTP-palvelimelta jokaisen
goottikuun päivänä 7 klo 07.07.07 tietokoneen paikallista aikaa. Suljettuna
väliin jäänyt tarkistus tehdään seuraavalla käynnistyksellä. Verkkovirheen
jälkeen uusi yritys tehdään tunnin kuluttua. Widgetin oikean painikkeen valikko
näyttää tarkistuksen tilan. UDP-portin 123 on oltava käytettävissä.
Korjaus vaikuttaa vain sovelluksen kelloon ja tämän päivän päivämäärään;
järjestelmäkelloa ei muuteta eikä ylläpitäjän oikeuksia tarvita. NTP-korjaus
on istuntokohtainen; tietokoneen oma ajan synkronointi kannattaa pitää päällä.
