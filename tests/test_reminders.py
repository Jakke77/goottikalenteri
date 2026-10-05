import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from calendar_model import CalendarDate, from_gregorian
from reminders import ReminderStore, local_instant, parse_instant


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'reminders.json'
        self.store = ReminderStore(self.path)

    def tearDown(self):
        self.directory.cleanup()

    def test_restart_delivers_overdue_once_and_snooze(self):
        date = CalendarDate(1, 0, 7)
        item = self.store.save(date, 12, 0, 'Muista tee', 'Lisätieto')
        deadline = parse_instant(item['due'])
        self.assertEqual(self.store.take_due(deadline - timedelta(seconds=1)), [])
        self.assertEqual(len(self.store.take_due(deadline + timedelta(hours=2))), 1)
        restored = ReminderStore(self.path)
        self.assertEqual(restored.take_due(deadline + timedelta(days=2)), [])
        restored.snooze(item['id'], now=deadline + timedelta(days=2))
        self.assertEqual(restored.take_due(deadline + timedelta(days=2, minutes=9)), [])
        self.assertEqual(len(restored.take_due(deadline + timedelta(days=2, minutes=10))), 1)

    def test_multiple_edit_disable_and_remove(self):
        date = CalendarDate(2, 12, 29)
        a = self.store.save(date, 12, 0, 'A')
        self.store.save(date, 13, 0, 'B', enabled=False)
        self.assertEqual(len(self.store.on_date(date)), 2)
        self.store.save(date, 14, 0, 'Korjattu', ident=a['id'])
        self.assertEqual(len(self.store.items), 2)
        self.assertEqual(self.store.pending()[0]['title'], 'Korjattu')
        self.store.remove(a['id'])
        self.assertEqual(self.store.pending(), [])

    def test_failed_delivery_write_does_not_lose_reminder(self):
        item = self.store.save(CalendarDate(), 12, 0, 'Tärkeä')
        original = self.path.read_bytes()
        with patch('reminders.os.replace', side_effect=OSError('Disk full')):
            with self.assertRaises(OSError):
                self.store.take_due(parse_instant(item['due']))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(len(self.store.pending()), 1)
        self.assertEqual(len(self.store.take_due(parse_instant(item['due']))), 1)

    def test_corruption_and_invalid_title_preserve_file(self):
        self.store.save(CalendarDate(), 12, 0, 'Alkuperäinen')
        original = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.store.save(CalendarDate(), 12, 0, '  ')
        self.assertEqual(self.path.read_bytes(), original)
        self.path.write_text('{broken')
        with self.assertRaises(ValueError):
            ReminderStore(self.path)
        self.assertEqual(self.path.read_text(), '{broken')

    @unittest.skipUnless(hasattr(time, 'tzset'), 'Requires POSIX timezone handling')
    def test_dst_gap_rejected_and_autumn_time_fixed(self):
        before = os.environ.get('TZ')
        os.environ['TZ'] = 'Europe/Helsinki'
        time.tzset()
        try:
            gap = from_gregorian(datetime(2027, 3, 28).date())
            with self.assertRaises(ValueError):
                local_instant(gap, 3, 30)
            autumn = from_gregorian(datetime(2027, 10, 31).date())
            value = local_instant(autumn, 3, 30)
            self.assertIsNotNone(value.tzinfo)
            self.assertEqual(value.astimezone().hour, 3)
        finally:
            if before is None:
                os.environ.pop('TZ', None)
            else:
                os.environ['TZ'] = before
            time.tzset()


class ReminderGuiTests(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QSettings
        from ui import CalendarWindow
        from storage import EventStore
        self.app = QApplication.instance() or QApplication([])
        self.directory = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, self.directory.name)
        self.app.setOrganizationName('ReminderTest')
        self.app.setApplicationName('ReminderTest')
        self.owner = CalendarWindow(EventStore(Path(self.directory.name) / 'events.json'), restore_widget=False)
        self.owner.time_service.shutdown()
        self.owner.reminders.timer.stop()

    def tearDown(self):
        self.owner.reminders.shutdown()
        self.owner.widget_only = False
        self.owner.reminders.store.commit([])
        self.owner.set_widget_enabled(False)
        self.owner.close()
        self.owner.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def test_editor_and_calendar_markers_and_hide(self):
        from reminder_ui import ReminderEditor
        from PyQt6.QtCore import QTime
        date = CalendarDate(3, 0, 2)
        dialog = ReminderEditor(self.owner, date)
        dialog.title.setText('Harjoitus')
        dialog.time.setTime(QTime(12, 35))
        dialog.save()
        self.assertEqual(len(self.owner.reminders.store.pending()), 1)
        self.owner.date = date
        self.owner.refresh()
        self.assertTrue(self.owner.days[2].property('hasReminder'))
        self.owner.show()
        self.owner.close()
        self.assertFalse(self.owner.isVisible())
        self.assertTrue(self.owner.desktop_widget.isVisible())
        self.assertTrue(any('Harjoitus' in line for line, font in self.owner.desktop_widget.lines))

    def test_scheduler_signals_only_after_commit_and_audio_volume(self):
        from sound import ReminderSound
        item = self.owner.reminders.store.save(CalendarDate(), 12, 0, 'Testi')
        now = parse_instant(item['due'])
        with patch.object(self.owner.reminders, 'show_notification') as notify, patch.object(self.owner.reminders.sound, 'play') as play:
            self.owner.reminders.check(now)
            self.owner.reminders.check(now)
            notify.assert_called_once()
            play.assert_called_once()
        sound = ReminderSound()
        if sound.player is not None:
            with patch.object(sound.player, 'play') as play:
                sound.play(volume=37)
                self.assertAlmostEqual(sound.output.volume(), .37, places=5)
                play.assert_called_once()
                sound.play(volume=0)
                play.assert_called_once()
            sound.stop()

    def test_notification_snooze_keeps_a_pending_reminder(self):
        from PyQt6.QtWidgets import QPushButton
        item = self.owner.reminders.store.save(CalendarDate(), 12, 0, 'Huhuu', '<b>Plain text</b>')
        self.owner.settings.setValue('reminders/volume', 0)
        with patch('shutil.which', return_value=None):
            self.owner.reminders.check(parse_instant(item['due']))
        self.assertEqual(len(self.owner.reminders.popups), 1)
        popup = self.owner.reminders.popups[0]
        snooze = next(button for button in popup.findChildren(QPushButton) if button.text() == 'Siirrä 10 min')
        snooze.click()
        self.assertEqual(len(self.owner.reminders.store.pending()), 1)
        self.assertEqual(len(self.owner.reminders.popups), 0)

    def test_theme_zero_alpha_and_cancel(self):
        from widget import SettingsDialog, load_options
        self.owner.set_widget_enabled(True)
        dialog = SettingsDialog(self.owner)
        dialog.controls['background_opacity'].setValue(0)
        image = self.owner.desktop_widget.grab().toImage()
        self.assertEqual(image.pixelColor(4, self.owner.desktop_widget.height() // 2).alpha(), 0)
        dialog.reject()
        self.assertEqual(self.owner.desktop_widget.options, load_options(self.owner.settings))
