"""Forecast dates, localization and failure handling independent of live weather."""
import unittest
from datetime import date
from weather import forecast_lines

def day(d, lo='2', hi='9'):
    return {'date': d, 'mintempC': lo, 'maxtempC': hi,
            'hourly': [{'time': '0', 'chanceofrain': '80', 'weatherDesc': [{'value': 'Rain'}]},
                       {'time': '1200', 'chanceofrain': '20', 'lang_fi': [{'value': 'Pilvinen'}]}]}

class ForecastTests(unittest.TestCase):
    def test_three_future_days_and_noon_localization(self):
        data={'nearest_area': [{'areaName': [{'value': 'Helsinki'}], 'country': [{'value': 'Finland'}]}],
              'weather':[day('2026-10-03'), day('2026-10-04'),day('2026-10-05'),day('2026-10-06'),day('2026-10-07')]}
        lines=forecast_lines(data,date(2026,10,4))
        self.assertEqual(len(lines),4)
        self.assertIn('Helsinki',lines[0])
        self.assertIn('4.10.',lines[1])
        self.assertIn('Pilvinen',lines[1])
        self.assertIn('sade 80 %',lines[1])
        self.assertIn('6.10.',lines[-1])

    def test_expired_and_invalid_forecasts_are_rejected(self):
        with self.assertRaises(ValueError):
            forecast_lines({'weather':[day('2026-10-03')]},date(2026,10,4))
        with self.assertRaises(ValueError):
            forecast_lines({'weather':[day('invalid')]},date(2026,10,4))
