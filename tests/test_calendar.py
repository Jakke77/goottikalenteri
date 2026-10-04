import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from calendar_model import CalendarDate, MONTH_NAMES, from_gregorian, to_gregorian, weekday, moon_label, gregorian_parts
from storage import EventStore

class CalendarTests(unittest.TestCase):
    def test_parallel_dates(self):
        self.assertEqual(from_gregorian(date(2026, 10, 4)), CalendarDate(1, 0, 6))
        self.assertEqual(to_gregorian(CalendarDate()), date(2026, 9, 28))
        self.assertEqual(weekday(CalendarDate(1, 0, 6)), 6)
        self.assertEqual(weekday(CalendarDate(1, 1)), 2)
        self.assertEqual(to_gregorian(CalendarDate(2)), date(2027, 10, 23))
        self.assertEqual(len(MONTH_NAMES), 13)
        for year in (1, 2, 17):
            for month in range(13):
                for day in range(30):
                    value = CalendarDate(year, month, day)
                    self.assertEqual(CalendarDate.from_key(value.key), value)
                    self.assertEqual(from_gregorian(to_gregorian(value)), value)
        self.assertEqual(moon_label(0), 'Uusikuu')

    def test_unbounded_parallel_years(self):
        # Check leap/century boundaries against the standard library.
        for civil in (date(2028, 2, 29), date(2100, 3, 1), date(2400, 2, 29),
                      date(9999, 12, 31)):
            fictional = from_gregorian(civil)
            parts = gregorian_parts(fictional)
            self.assertEqual((parts.year, parts.month, parts.day),
                             (civil.year, civil.month, civil.day))
        for year in (10000, 1000000, 10**30):
            fictional = CalendarDate(year, 12, 29)
            parts = gregorian_parts(fictional)
            self.assertEqual(from_gregorian(parts), fictional)
            self.assertEqual(fictional.shift_month(1), CalendarDate(year + 1, 0, 29))
            self.assertEqual(weekday(fictional), (parts.toordinal() - 1) % 7)
            with tempfile.TemporaryDirectory() as directory:
                store = EventStore(Path(directory) / 'events.json')
                store.save_note(fictional, 'Far future')
                self.assertEqual(EventStore(store.path).get(fictional), 'Far future')

    def test_boundaries(self):
        self.assertEqual(CalendarDate(1, 12, 29).shift_month(1), CalendarDate(2, 0, 29))
        self.assertEqual(CalendarDate(2).shift_month(-1), CalendarDate(1, 12))
        for args in ((0, 0, 0), (1, 13, 0), (1, 0, 30), (True, 0, 0)):
            with self.assertRaises(ValueError):
                CalendarDate(*args)
        with self.assertRaises(ValueError):
            CalendarDate().shift_month(-1)

    def test_persistence_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'events.json'
            store = EventStore(path)
            value = CalendarDate(1, 2, 5)
            store.save_note(value, 'Yö\nSalaman ääni')
            self.assertEqual(EventStore(path).get(value), 'Yö\nSalaman ääni')
            original = path.read_bytes()
            with patch('storage.os.replace', side_effect=OSError('Full disk')):
                with self.assertRaises(OSError):
                    store.save_note(value, 'lost')
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(store.get(value), 'Yö\nSalaman ääni')
            store.save_note(value, '')
            self.assertEqual(EventStore(path).get(value), '')
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError):
                EventStore(path)
            self.assertEqual(path.read_text(), '{broken')

if __name__ == '__main__':
    unittest.main()
