"""Verify the two desktop launchers can reach one running calendar process."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

@unittest.skipUnless(importlib.util.find_spec('PyQt6'), 'PyQt6 not installed')
class InstanceTests(unittest.TestCase):
    def test_two_launcher_modes_share_one_server(self):
        from PyQt6.QtCore import QObject, QProcess
        from PyQt6.QtWidgets import QApplication
        from instance import server_name, start_server
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            name = server_name(Path(directory) / 'events.json')
            owner = QObject()
            received = []
            server = start_server(name, owner, received.append)
            try:
                for mode in ('widget', 'calendar', 'both'):
                    child = QProcess()
                    code = ('from instance import request_mode; import sys; '
                            f'sys.exit(0 if request_mode({name!r}, {mode!r}) else 1)')
                    child.start(sys.executable, ['-c', code])
                    self.assertTrue(child.waitForStarted(2000))
                    deadline = time.monotonic() + 8
                    while child.state() != QProcess.ProcessState.NotRunning and time.monotonic() < deadline:
                        app.processEvents()
                        child.waitForFinished(10)
                    if child.state() != QProcess.ProcessState.NotRunning:
                        child.kill()
                        child.waitForFinished(1000)
                        self.fail('Launcher IPC timed out')
                    self.assertEqual(child.exitCode(), 0, bytes(child.readAllStandardError()).decode())
                self.assertEqual(received, ['widget', 'calendar', 'both'])
            finally:
                server.close()

    def test_calendar_startup_preserves_widget_preference(self):
        from PyQt6.QtCore import QSettings
        from PyQt6.QtWidgets import QApplication
        from ui import CalendarWindow
        from storage import EventStore
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            QSettings.setDefaultFormat(QSettings.Format.IniFormat)
            QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, directory)
            app.setOrganizationName('GoottiLauncherTest')
            app.setApplicationName('GoottiLauncherTest')
            preferences = QSettings()
            preferences.setValue('widget/enabled', True)
            window = CalendarWindow(EventStore(Path(directory) / 'events.json'), restore_widget=False)
            self.assertIsNone(window.desktop_widget)
            self.assertTrue(preferences.value('widget/enabled', type=bool))
            window.close()
            window.deleteLater()
            app.processEvents()
