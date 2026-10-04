"""Asynchronous wttr.in client; cached forecasts never block the clock."""
import json
import time
from datetime import date
from urllib.parse import quote
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest


def forecast_lines(data, today=None):
    today = today or date.today()
    area = data.get('nearest_area', [{}])[0]
    name = area.get('areaName', [{}])[0].get('value', '')
    country = area.get('country', [{}])[0].get('value', '')
    lines = [f'{name}, {country}'.strip(', ') or 'Sää']
    for item in data.get('weather', []):
        day = date.fromisoformat(item['date'])
        if day < today:
            continue
        hours = item.get('hourly', [])
        noon = min(hours, key=lambda h: abs(int(h.get('time', 0)) - 1200)) if hours else {}
        description = noon.get('lang_fi') or noon.get('weatherDesc') or [{'value': ''}]
        rain = max((int(h.get('chanceofrain', 0)) for h in hours), default=0)
        lines.append(f'{day.day}.{day.month}.  {item["mintempC"]}…{item["maxtempC"]} °C · {description[0]["value"]} · sade {rain} %')
        if len(lines) == 4:
            break
    if len(lines) == 1:
        raise ValueError('Ennusteessa ei ole tulevia päiviä')
    return lines


class WeatherService(QObject):
    changed = pyqtSignal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.manager = QNetworkAccessManager(self)
        self.key = None
        self.reply = None
        self.lines = []
        self.enabled = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(60 * 60 * 1000)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.timeout.connect(self.refresh)

    def configure(self, options):
        enabled = options['weather_enabled']
        key = '' if options['weather_auto'] else options['weather_city'].strip()
        if enabled and not options['weather_auto'] and not key:
            enabled = False
        if (enabled, key) == (self.enabled, self.key):
            return
        self.enabled, self.key = enabled, key
        if self.reply:
            self.reply.abort()
        self.debounce.stop()
        self.lines = []
        if enabled:
            self.lines = ['Säätä haetaan…']
            self.debounce.start(1000)
        self.changed.emit()

    def cached(self):
        try:
            cache = json.loads(self.settings.value('weather/cache', '{}'))
            if cache.get('key') != self.key:
                return None
            lines = forecast_lines(cache['data'])
            age = time.time() - cache['saved']
            return lines, age
        except (ValueError, KeyError, TypeError, IndexError):
            return None

    def refresh(self, force=False):
        if not self.enabled or self.reply:
            return
        cache = self.cached()
        if cache and 0 <= cache[1] < 3600 and not force:
            self.lines = cache[0] + ['wttr.in · päivitetty alle tunti sitten']
            self.changed.emit()
            return
        request = QNetworkRequest(QUrl('https://wttr.in/' + quote(self.key, safe='') + '?format=j1&lang=fi'))
        request.setRawHeader(b'User-Agent', b'Varjoaika/0.5.0')
        request.setTransferTimeout(20000)
        reply = self.manager.get(request)
        self.reply = reply
        key = self.key
        reply.finished.connect(lambda: self.finished(reply, key))

    def finished(self, reply, key):
        if self.reply is reply:
            self.reply = None
        if key != self.key or not self.enabled:
            reply.deleteLater()
            return
        try:
            if reply.error() != reply.NetworkError.NoError:
                raise ValueError('Yhteys epäonnistui')
            payload = bytes(reply.readAll())
            if len(payload) > 1024 * 1024:
                raise ValueError('Liian suuri vastaus')
            data = json.loads(payload)
            self.lines = forecast_lines(data) + ['wttr.in · päivitetty juuri']
            self.settings.setValue('weather/cache', json.dumps({'key': key, 'saved': time.time(), 'data': data}))
        except (ValueError, KeyError, TypeError, IndexError):
            cache = self.cached()
            self.lines = (cache[0] + ['wttr.in · vanha ennuste, yhteys epäonnistui']
                          if cache else ['Säätä ei saatu. Tarkista paikkakunta ja yhteys.', 'wttr.in'])
        reply.deleteLater()
        self.changed.emit()
