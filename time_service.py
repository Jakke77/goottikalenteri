"""Monthly public NTP check; never sets the operating system clock."""
from datetime import datetime, timedelta
import socket
import struct
import time
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from calendar_model import EPOCH

SERVER = 'time.mikes.fi'
NTP_EPOCH = 2208988800

def latest_due(now):
    """Latest fictional day 7 at 07:07:07 in the computer's local timezone."""
    days = (now.date() - EPOCH).days
    cycle = days // 30
    due = datetime.combine(EPOCH + timedelta(days=cycle * 30 + 7),
                           datetime.min.time()).replace(hour=7, minute=7, second=7)
    if now < due:
        due -= timedelta(days=30)
    return due if due.date() >= EPOCH else None

def query_ntp(host=SERVER):
    packet = bytearray(48)
    packet[0] = 0x23  # NTP v4 client
    started = time.time()
    stamp = int((started + NTP_EPOCH) * 2**32) % 2**64
    packet[40:48] = struct.pack('!Q', stamp)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.settimeout(5)
        connection.connect((host, 123))
        connection.send(packet)
        response = connection.recv(512)
        ended = time.time()
    if (len(response) < 48 or response[0] >> 6 == 3 or
        response[0] & 7 != 4 or not 1 <= response[1] <= 15 or
        response[24:32] != packet[40:48]):
        raise ValueError('Invalid or unsynchronised NTP response')
    raw = [struct.unpack('!Q', response[index:index+8])[0] for index in (32, 40)]
    if not all(raw):
        raise ValueError('Missing NTP timestamps')
    stamps = [value / 2**32 - NTP_EPOCH for value in raw]
    # Resolve NTP's 2036 rollover using the closest era to the local clock.
    received, sent = [value + round((started - value) / 2**32) * 2**32
                      for value in stamps]
    if ended - started > 6:
        raise ValueError('Invalid NTP timestamps')
    return ((received - started) + (sent - ended)) / 2

class NtpWorker(QThread):
    succeeded = pyqtSignal(float)
    failed = pyqtSignal(str)
    def run(self):
        try:
            self.succeeded.emit(query_ntp())
        except (OSError, ValueError) as error:
            self.failed.emit(str(error))

class TimeService(QObject):
    changed = pyqtSignal()
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.closed = False
        self.offset = 0.0
        self.worker = None
        self.retry_at = 0.0
        self.status = 'Tarkistus goottikuun päivänä 7 klo 07.07.07'
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_due)
        self.timer.start(1000)
        QTimer.singleShot(0, self.check_due)

    def now(self):
        return datetime.fromtimestamp(time.time() + self.offset)

    def check_due(self):
        if self.closed:
            return
        due = latest_due(self.now())
        if (due is None or self.worker is not None or time.monotonic() < self.retry_at or
            self.settings.value('time/last_due', '') == due.isoformat()):
            return
        self.pending_due = due.isoformat()
        self.worker = NtpWorker(self)
        self.worker.succeeded.connect(self.succeeded)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def succeeded(self, offset):
        if self.closed:
            return
        self.offset = offset
        self.settings.setValue('time/last_due', self.pending_due)
        self.settings.setValue('time/last_check', self.now().isoformat())
        self.settings.sync()
        self.status = f'Aika tarkistettu: {SERVER} (korjaus {offset:+.3f} s)'
        self.changed.emit()

    def failed(self, error):
        if self.closed:
            return
        self.status = 'Aikapalvelin ei vastannut; uusi yritys tunnin kuluttua'
        self.retry_at = time.monotonic() + 3600

    def finished(self):
        self.worker.deleteLater()
        self.worker = None

    def shutdown(self):
        self.closed = True
        self.timer.stop()
        if self.worker is not None:
            self.worker.wait(6500)
