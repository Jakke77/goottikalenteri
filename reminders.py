"""Persistent one-shot reminders, using real instants and atomic writes.

The fictional date is converted at creation. UTC instants keep reminders stable
across DST and clock corrections; no note-file migration is necessary.
"""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import tempfile
import uuid
from calendar_model import CalendarDate, to_gregorian, from_gregorian


def utc_now():
    return datetime.now(timezone.utc)


def parse_instant(value):
    if not isinstance(value, str):
        raise ValueError('Muistutuksen aika puuttuu.')
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None:
        raise ValueError('Muistutuksen ajasta puuttuu aikavyöhyke.')
    return instant.astimezone(timezone.utc)


def local_instant(date, hour, minute):
    local = datetime.combine(to_gregorian(date), datetime.min.time()).replace(hour=hour, minute=minute)
    aware = local.astimezone()
    # libc normalizes nonexistent spring-transition times; reject that silently changed time.
    if aware.replace(tzinfo=None) != local:
        raise ValueError('Tätä kellonaikaa ei ole kesäaikaan siirtymisen vuoksi. Valitse toinen aika.')
    return aware.astimezone(timezone.utc)


def display_date(item):
    return from_gregorian(parse_instant(item['due']).astimezone().date())


class ReminderStore:
    def __init__(self, path):
        self.path = Path(path)
        self.items = []
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('reminders'), list):
                raise ValueError('Tuntematon muistutustiedoston muoto.')
            self.validate(data['reminders'])
            self.items = data['reminders']

    @staticmethod
    def validate(items):
        ids = set()
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Virheellinen muistutus.')
            ident = item.get('id')
            if not isinstance(ident, str) or not ident or ident in ids:
                raise ValueError('Virheellinen muistutustunniste.')
            ids.add(ident)
            if not isinstance(item.get('title'), str) or not item['title'].strip():
                raise ValueError('Muistutukselle tarvitaan otsikko.')
            if not isinstance(item.get('body'), str) or type(item.get('enabled')) is not bool:
                raise ValueError('Virheellinen muistutuksen sisältö.')
            CalendarDate.from_key(item['date'])
            parse_instant(item['due'])
            if item.get('delivered') is not None:
                parse_instant(item['delivered'])

    def commit(self, items):
        self.validate(items)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.reminders-', suffix='.tmp', delete=False) as stream:
                temporary = stream.name
                json.dump({'version': 1, 'reminders': items}, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        self.items = deepcopy(items)

    def save(self, date, hour, minute, title, body='', ident=None, enabled=True):
        due = local_instant(date, hour, minute)
        item = dict(id=ident or uuid.uuid4().hex, date=date.key, due=due.isoformat(),
                    title=title.strip(), body=body, enabled=enabled, delivered=None)
        items = [deepcopy(value) for value in self.items if value['id'] != item['id']]
        items.append(item)
        self.commit(items)
        return deepcopy(item)

    def remove(self, ident):
        self.commit([value for value in self.items if value['id'] != ident])

    def on_date(self, date):
        return [deepcopy(value) for value in self.items if value['date'] == date.key]

    def pending(self):
        return sorted((deepcopy(value) for value in self.items
                       if value['enabled'] and value['delivered'] is None),
                      key=lambda value: parse_instant(value['due']))

    def take_due(self, now=None):
        now = now or utc_now()
        due = [value for value in self.pending() if parse_instant(value['due']) <= now]
        if due:
            ids = {value['id'] for value in due}
            updated = deepcopy(self.items)
            for value in updated:
                if value['id'] in ids:
                    value['delivered'] = now.isoformat()
            # Persist before signalling; restart cannot deliver these a second time.
            self.commit(updated)
        return due

    def snooze(self, ident, minutes=10, now=None):
        instant = (now or utc_now()) + timedelta(minutes=minutes)
        updated = deepcopy(self.items)
        found = False
        for value in updated:
            if value['id'] == ident:
                value.update(due=instant.isoformat(), date=from_gregorian(instant.astimezone().date()).key,
                             delivered=None, enabled=True)
                found = True
        if not found:
            raise ValueError('Muistutus on jo poistettu.')
        self.commit(updated)
