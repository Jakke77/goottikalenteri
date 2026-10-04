"""Isolated smoke test used to verify a frozen distribution without user data."""
import tempfile
from pathlib import Path
from PyQt6.QtCore import QSettings, Qt
from storage import EventStore
from calendar_model import CalendarDate, from_gregorian
from datetime import date
from ui import CalendarWindow
from widget import SettingsDialog, load_options

def run(app):
    with tempfile.TemporaryDirectory(prefix='gootti-self-test-') as directory:
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, directory)
        store = EventStore(Path(directory) / 'events.json')
        value = CalendarDate(1000000, 12, 29)
        store.save_note(value, 'Testi: yön ääni')
        assert EventStore(store.path).get(value) == 'Testi: yön ääni'
        assert from_gregorian(date(2026, 10, 4)) == CalendarDate(1, 0, 6)
        window = CalendarWindow(store)
        window.set_widget_enabled(True)
        window.date = CalendarDate(1000000, 12, 29)
        window.navigate(months=1)
        assert window.date == CalendarDate(1000001, 0, 29)
        assert len(window.days) == 30
        window.show()
        app.processEvents()
        widget = window.desktop_widget
        assert widget.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert widget.grab().toImage().pixelColor(0, 0).alpha() == 0
        dialog = SettingsDialog(window)
        dialog.controls['clock_size'].setValue(65)
        assert widget.options['clock_size'] == 65
        dialog.reject()
        assert widget.options == load_options(window.settings)
        window.close()
        widget.deleteLater()
        window.deleteLater()
        app.processEvents()
    print('Goottikalenteri self-test: PASS')
    return 0
