"""Validated JSON storage with atomic replacement and rollback on errors."""
import json
import os
from pathlib import Path
import tempfile
from calendar_model import CalendarDate

class EventStore:
    def __init__(self, path):
        self.path = Path(path)
        self.events = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('events'), dict):
                raise ValueError('Unsupported events.json format.')
            for key, note in data['events'].items():
                CalendarDate.from_key(key)
                if not isinstance(note, str):
                    raise ValueError('Every note must be text.')
            self.events = data['events']

    def get(self, date):
        return self.events.get(date.key, '')

    def save_note(self, date, note):
        if not isinstance(note, str):
            raise ValueError('The note must be text.')
        updated = dict(self.events)
        if note.strip():
            updated[date.key] = note
        else:
            updated.pop(date.key, None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.events-', suffix='.tmp', delete=False) as stream:
                temporary = stream.name
                json.dump({'version': 1, 'events': updated}, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        self.events = updated
