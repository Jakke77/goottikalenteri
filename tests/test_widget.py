"""Optional Qt checks; skipped if PyQt6 is not installed."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HAS_QT = importlib.util.find_spec('PyQt6') is not None

@unittest.skipUnless(HAS_QT, 'PyQt6 not installed')
class WidgetTests(unittest.TestCase):
    def setUp(self):
        from PyQt6.QtCore import QSettings
        from PyQt6.QtWidgets import QApplication
        from ui import CalendarWindow, STYLE
        from storage import EventStore
        self.app = QApplication.instance() or QApplication([])
        self.app.setStyleSheet(STYLE)
        self.directory = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          self.directory.name)
        self.app.setOrganizationName('GoottiTest')
        self.app.setApplicationName('GoottiTest')
        self.owner = CalendarWindow(EventStore(Path(self.directory.name) / 'events.json'))
        self.owner.set_widget_enabled(True)
        self.app.processEvents()

    def tearDown(self):
        self.owner.widget_only = False
        self.owner.set_widget_enabled(False)
        self.owner.reminders.shutdown()
        self.owner.close()
        self.owner.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def test_transparency_and_resize_cancel(self):
        from widget import SettingsDialog, load_options
        widget = self.owner.desktop_widget
        self.assertEqual(widget.grab().toImage().pixelColor(0, 0).alpha(), 0)
        before = widget.width()
        dialog = SettingsDialog(self.owner)
        dialog.controls['clock_size'].setValue(65)
        self.assertGreater(widget.width(), before)
        dialog.controls['opacity'].setValue(50)
        self.assertEqual(widget.options['opacity'], 50)
        dialog.reject()
        self.assertEqual(widget.options, load_options(self.owner.settings))

    def test_settings_save_and_standalone_disable(self):
        from PyQt6.QtCore import QTimer
        from widget import load_options
        def accept_settings():
            dialog = self.app.activeModalWidget()
            dialog.controls['clock_size'].setValue(55)
            dialog.controls['seconds'].setChecked(False)
            dialog.accept()
        QTimer.singleShot(0, accept_settings)
        self.owner.open_settings()
        saved = load_options(self.owner.settings)
        self.assertEqual(saved['clock_size'], 55)
        self.assertFalse(saved['seconds'])
        self.assertEqual(self.owner.desktop_widget.options['clock_size'], 55)
        self.owner.widget_only = True
        self.owner.hide()
        self.owner.set_widget_enabled(False)
        self.assertTrue(self.owner.isVisible())
        self.owner.widget_only = False
