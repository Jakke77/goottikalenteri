import unittest
from datetime import datetime
from time_service import latest_due

class ScheduleTests(unittest.TestCase):
    def test_first_month_and_exact_second(self):
        self.assertIsNone(latest_due(datetime(2026, 10, 5, 7, 7, 6)))
        self.assertEqual(latest_due(datetime(2026, 10, 5, 7, 7, 7)),
                         datetime(2026, 10, 5, 7, 7, 7))
    def test_thirty_day_month_catchup(self):
        self.assertEqual(latest_due(datetime(2026, 11, 4, 7, 7, 6)),
                         datetime(2026, 10, 5, 7, 7, 7))
        self.assertEqual(latest_due(datetime(2026, 11, 4, 7, 7, 7)),
                         datetime(2026, 11, 4, 7, 7, 7))
