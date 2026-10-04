"""Fictional calendar arithmetic; intentionally independent of datetime."""
from dataclasses import dataclass

MONTH_NAMES = (
    'Varjojenkuu', 'Hallankuu', 'Routakuu', 'Korppikuu', 'Hylättyjen kuu',
    'Kalmistonkuu', 'Ikiyön kuu', 'Verikuu', 'Pimentojen kuu',
    'Kuihtumisen kuu', 'Aaveiden kuu', 'Marraskuu', 'Sielunkuu',
)
MONTHS_PER_YEAR = 13
DAYS_PER_MONTH = 30

@dataclass(frozen=True)
class CalendarDate:
    year: int = 1
    month: int = 0
    day: int = 0

    def __post_init__(self):
        if any(type(v) is not int for v in (self.year, self.month, self.day)):
            raise ValueError('Date components must be integers.')
        if self.year < 1 or not 0 <= self.month < 13 or not 0 <= self.day < 30:
            raise ValueError('Expected year >= 1, month 0..12, day 0..29.')

    @property
    def key(self):
        return f'{self.year:04d}-{self.month:02d}-{self.day:02d}'

    @property
    def label(self):
        return f'Vuosi {self.year:04d} · {self.month}. {MONTH_NAMES[self.month]} · Päivä {self.day}'

    def shift_month(self, delta):
        index = (self.year - 1) * 13 + self.month + delta
        if index < 0:
            raise ValueError('The calendar begins in year 0001.')
        year, month = divmod(index, 13)
        return CalendarDate(year + 1, month, self.day)

    def shift_year(self, delta):
        return CalendarDate(self.year + delta, self.month, self.day)

    @classmethod
    def from_key(cls, key):
        parts = key.split('-')
        if len(parts) != 3:
            raise ValueError('Invalid date key.')
        date = cls(*(int(part) for part in parts))
        if date.key != key:
            raise ValueError('Noncanonical date key.')
        return date


def moon_label(day):
    """Symbolic phases in a fixed fictional 30-day cycle, not astronomy."""
    CalendarDate(day=day)
    if day == 0:
        return 'Uusikuu'
    if day < 8:
        return 'Kasvava sirppi'
    if day == 8:
        return 'Ensimmäinen neljännes'
    if day < 15:
        return 'Kasvava kuu'
    if day == 15:
        return 'Täysikuu'
    if day < 22:
        return 'Vähenevä kuu'
    if day == 22:
        return 'Viimeinen neljännes'
    return 'Vähenevä sirppi'

# User-defined parallel timeline: 2026-10-04 = 0001-00-06.
from datetime import date as GregorianDate, timedelta
EPOCH = GregorianDate(2026, 9, 28)
WEEKDAY_NAMES = ('Ma', 'Ti', 'Ke', 'To', 'Pe', 'La', 'Su')

def to_gregorian(date):
    offset = (date.year - 1) * 390 + date.month * 30 + date.day
    return EPOCH + timedelta(days=offset)

def from_gregorian(date):
    offset = date.toordinal() - EPOCH.toordinal()
    if offset < 0:
        raise ValueError('Date precedes year 0001.')
    year, remainder = divmod(offset, 390)
    month, day = divmod(remainder, 30)
    return CalendarDate(year + 1, month, day)

def weekday(date):
    # The epoch is Monday; this also works beyond datetime's year limit.
    return ((date.year - 1) * 390 + date.month * 30 + date.day) % 7

@dataclass(frozen=True)
class GregorianParts:
    """Proleptic Gregorian date without datetime's maximum-year restriction."""
    year: int
    month: int
    day: int

    @property
    def label(self):
        return f'{self.day:02d}.{self.month:02d}.{self.year:04d}'

    def toordinal(self):
        previous = self.year - 1
        lengths = [31, 29 if is_leap_year(self.year) else 28, 31, 30, 31, 30,
                   31, 31, 30, 31, 30, 31]
        return (365 * previous + previous // 4 - previous // 100 + previous // 400
                + sum(lengths[:self.month - 1]) + self.day)


def is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def gregorian_parts(date):
    """Convert in bounded work, even for very large fictional years."""
    ordinal = EPOCH.toordinal() + (date.year - 1) * 390 + date.month * 30 + date.day
    cycles, remainder = divmod(ordinal - 1, 146097)
    year = cycles * 400 + 1
    # At most 399 iterations; never iterate across all elapsed years.
    while remainder >= (366 if is_leap_year(year) else 365):
        remainder -= 366 if is_leap_year(year) else 365
        year += 1
    lengths = [31, 29 if is_leap_year(year) else 28, 31, 30, 31, 30,
               31, 31, 30, 31, 30, 31]
    month = 1
    for length in lengths:
        if remainder < length:
            break
        remainder -= length
        month += 1
    return GregorianParts(year, month, remainder + 1)
