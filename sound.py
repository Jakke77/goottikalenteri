"""Local audio only. Qt Multimedia supports the installed Ubuntu codecs."""
from pathlib import Path
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
except ImportError:
    QMediaPlayer = QAudioOutput = None

DEFAULT_SOUND = Path(__file__).resolve().parent / 'assets' / 'huuhkaja.wav'


class ReminderSound(QObject):
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = None
        self.output = None
        if QMediaPlayer is not None:
            self.output = QAudioOutput(self)
            self.player = QMediaPlayer(self)
            self.player.setAudioOutput(self.output)
            self.player.errorOccurred.connect(lambda error, text: self.failed.emit('Äänen toisto epäonnistui: ' + text))

    def play(self, path='', volume=50, enabled=True):
        if not enabled or volume <= 0:
            return
        if self.player is None:
            self.failed.emit('Qt Multimedia puuttuu. Asenna python3-pyqt6.qtmultimedia tai käytä PyQt6-virtuaaliympäristöä.')
            return
        selected = Path(path).expanduser() if path else DEFAULT_SOUND
        if not selected.is_file():
            self.failed.emit('Äänitiedostoa ei löydy: ' + str(selected))
            return
        self.player.stop()
        self.output.setVolume(max(0, min(100, volume)) / 100)
        self.player.setSource(QUrl.fromLocalFile(str(selected.resolve())))
        self.player.play()

    def stop(self):
        if self.player is not None:
            self.player.stop()
