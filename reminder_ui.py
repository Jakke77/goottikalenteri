"""Reminder editor, agenda, notifications and local audio preferences."""
from datetime import datetime
from pathlib import Path
import os
import sys
from PyQt6.QtCore import Qt, QTimer, QTime, QProcess
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QTextEdit,
    QTimeEdit, QVBoxLayout)
from calendar_model import CalendarDate, MONTH_NAMES, from_gregorian
from reminders import ReminderStore, parse_instant, utc_now
from sound import ReminderSound


def sound_options(settings):
    return dict(enabled=settings.value('reminders/sound_enabled', True, type=bool),
                volume=settings.value('reminders/volume', 50, type=int),
                path=settings.value('reminders/sound_file', '', type=str))


from startup import autostart_path, startup_choices, set_autostart


class ReminderEditor(QDialog):
    def __init__(self, owner, date, item=None, parent=None):
        super().__init__(parent or owner)
        self.owner, self.item = owner, item
        self.setWindowTitle('Muokkaa muistutusta' if item else 'Uusi muistutus')
        self.resize(560, 460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title = QLineEdit(item['title'] if item else '')
        self.title.setMaxLength(200)
        self.title.setPlaceholderText('Mistä haluat muistutuksen?')
        form.addRow('Otsikko', self.title)
        self.year = QLineEdit(str(date.year))
        form.addRow('Varjoajan vuosi', self.year)
        self.month = QComboBox()
        self.month.addItems([f'{i}. {name}' for i, name in enumerate(MONTH_NAMES)])
        self.month.setCurrentIndex(date.month)
        form.addRow('Kuukausi', self.month)
        self.day = QSpinBox()
        self.day.setRange(0, 29)
        self.day.setValue(date.day)
        form.addRow('Päivä', self.day)
        local = parse_instant(item['due']).astimezone() if item else datetime.now().replace(hour=12, minute=0)
        self.time = QTimeEdit(QTime(local.hour, local.minute))
        self.time.setDisplayFormat('HH:mm')
        form.addRow('Paikallinen kellonaika', self.time)
        self.enabled = QCheckBox('Ilmoitus käytössä')
        self.enabled.setChecked(item['enabled'] if item else True)
        form.addRow('', self.enabled)
        layout.addLayout(form)
        self.body = QTextEdit()
        self.body.setAcceptRichText(False)
        self.body.setPlaceholderText('Lisätiedot (valinnainen)')
        self.body.setPlainText(item['body'] if item else '')
        layout.addWidget(self.body)
        hint = QLabel('Kellonaika on tämän koneen paikallista aikaa. Muistutus soi kerran.\n'
                      'Ohjelman pitää olla käynnissä; voit pitää vain widgetin näkyvissä.')
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Tallenna')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Peruuta')
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        if not self.title.text().strip():
            QMessageBox.warning(self, 'Otsikko puuttuu', 'Anna muistutukselle otsikko.')
            return
        try:
            date = CalendarDate(int(self.year.text()), self.month.currentIndex(), self.day.value())
            from reminders import local_instant
            due = local_instant(date, self.time.time().hour(), self.time.time().minute())
            if self.enabled.isChecked() and due <= utc_now():
                answer = QMessageBox.question(self, 'Ajankohta on jo mennyt',
                                              'Tämä aika on jo mennyt. Ilmoitetaanko heti tallennuksen jälkeen?',
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                              QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return
            self.owner.reminders.store.save(date, self.time.time().hour(), self.time.time().minute(),
                self.title.text(), self.body.toPlainText(), self.item['id'] if self.item else None,
                self.enabled.isChecked())
        except (ValueError, OSError, OverflowError) as error:
            QMessageBox.warning(self, 'Muistutusta ei tallennettu', str(error))
            return
        self.owner.reminders.changed()
        self.accept()


class AgendaDialog(QDialog):
    def __init__(self, owner, date=None, parent=None):
        super().__init__(parent or owner)
        self.owner, self.date = owner, date
        self.setWindowTitle('Muistutukset · Varjoaika')
        self.resize(670, 500)
        layout = QVBoxLayout(self)
        heading = QLabel(date.label if date else 'Huhuilun muistikirja')
        heading.setWordWrap(True)
        heading.setObjectName('section')
        layout.addWidget(heading)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.edit)
        layout.addWidget(self.list)
        actions = QHBoxLayout()
        for text, action in [('＋ Lisää', self.add), ('Muokkaa', self.edit), ('Poista', self.remove)]:
            button = QPushButton(text)
            button.clicked.connect(action)
            actions.addWidget(button)
        layout.addLayout(actions)
        hint = QLabel('Muistutukset toimivat myös kalenteri-ikkunan ollessa piilossa, kun widget on käynnissä.\n'
                      'Tietokoneen nukkuessa erääntyneet ilmoitetaan heräämisen jälkeen kerran.')
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        layout.addWidget(hint)
        close = QPushButton('Sulje')
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.refresh()

    def refresh(self):
        self.list.clear()
        values = self.owner.reminders.store.items
        if self.date:
            values = self.owner.reminders.store.on_date(self.date)
        for value in sorted(values, key=lambda item: parse_instant(item['due']), reverse=False):
            status = 'Ilmoitettu' if value['delivered'] else ('Odottaa' if value['enabled'] else 'Pois käytöstä')
            date = CalendarDate.from_key(value['date'])
            clock = parse_instant(value['due']).astimezone().strftime('%H:%M')
            row = QListWidgetItem(f'{value["title"]}\n{date.label} · {clock} · {status}')
            row.setData(Qt.ItemDataRole.UserRole, value['id'])
            self.list.addItem(row)
        if not self.list.count():
            row = QListWidgetItem('Ei vielä muistutuksia. Lisää ensimmäinen ＋ Lisää -painikkeesta.')
            row.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(row)

    def current(self):
        row = self.list.currentItem()
        ident = row.data(Qt.ItemDataRole.UserRole) if row else None
        return next((value for value in self.owner.reminders.store.items if value['id'] == ident), None)

    def add(self):
        ReminderEditor(self.owner, self.date or self.owner.date, parent=self).exec()
        self.refresh()

    def edit(self, *args):
        value = self.current()
        if value:
            ReminderEditor(self.owner, CalendarDate.from_key(value['date']), value, self).exec()
            self.refresh()

    def remove(self):
        value = self.current()
        if not value:
            return
        answer = QMessageBox.question(self, 'Poista muistutus', f'Poistetaanko muistutus “{value["title"]}”?',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.owner.reminders.store.remove(value['id'])
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, 'Poisto epäonnistui', str(error))
            return
        self.owner.reminders.changed()
        self.refresh()


class SoundSettingsDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.sound = ReminderSound(self)
        self.sound.failed.connect(lambda text: QMessageBox.warning(self, 'Ilmoitusääni', text))
        self.setWindowTitle('Ilmoitukset ja ääni · Varjoaika')
        self.resize(570, 350)
        layout = QVBoxLayout(self)
        opts = sound_options(owner.settings)
        self.enabled = QCheckBox('Soita muistutuksen ilmoitusääni')
        self.enabled.setChecked(opts['enabled'])
        layout.addWidget(self.enabled)
        form = QFormLayout()
        self.volume = QSpinBox()
        self.volume.setRange(0, 100)
        self.volume.setSuffix(' %')
        self.volume.setValue(opts['volume'])
        form.addRow('Voimakkuus', self.volume)
        self.path = QLineEdit(opts['path'])
        self.path.setPlaceholderText('Oletus: huuhkajan huhuilu')
        form.addRow('Äänitiedosto', self.path)
        layout.addLayout(form)
        actions = QHBoxLayout()
        for text, action in [('Valitse ääni…', self.choose), ('Huuhkaja', lambda: self.path.clear()),
                             ('Kokeile', self.play), ('Pysäytä', self.sound.stop)]:
            button = QPushButton(text)
            button.clicked.connect(action)
            actions.addWidget(button)
        layout.addLayout(actions)
        widget, calendar = startup_choices()
        self.autostart = QCheckBox('Avaa widget kirjautuessa')
        self.autostart.setChecked(widget)
        self.autostart_calendar = QCheckBox('Avaa kalenteri kirjautuessa')
        self.autostart_calendar.setChecked(calendar)
        layout.addWidget(self.autostart)
        layout.addWidget(self.autostart_calendar)
        hint = QLabel('Oletus on oma huuhkajan huhuilua jäljittelevä ääni.\n'
                      'Oma paikallinen WAV, OGG, MP3 tai FLAC: toisto riippuu Qt:n ja Ubuntun koodekeista.\n'
                      '0 % mykistää. Ilmoituksen teksti näkyy silti. Lopeta sulkee myös muistutukset.')
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Tallenna')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Peruuta')
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.finished.connect(lambda result: self.sound.stop())
        self.volume.valueChanged.connect(lambda value: self.sound.output.setVolume(value / 100) if self.sound.output else None)

    def choose(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Valitse ilmoitusääni', '',
                'Äänitiedostot (*.wav *.ogg *.mp3 *.flac *.m4a *.opus);;Kaikki tiedostot (*)')
        if path:
            self.path.setText(path)

    def play(self):
        self.sound.play(self.path.text().strip(), self.volume.value(), self.enabled.isChecked())

    def save(self):
        path = self.path.text().strip()
        if path and not Path(path).expanduser().is_file():
            QMessageBox.warning(self, 'Äänitiedostoa ei löydy', 'Valitse olemassa oleva paikallinen äänitiedosto.')
            return
        try:
            set_autostart(self.autostart.isChecked(), self.autostart_calendar.isChecked())
        except OSError as error:
            QMessageBox.warning(self, 'Automaattikäynnistys epäonnistui', str(error))
            return
        self.owner.settings.setValue('reminders/sound_enabled', self.enabled.isChecked())
        self.owner.settings.setValue('reminders/volume', self.volume.value())
        self.owner.settings.setValue('reminders/sound_file', path)
        self.owner.settings.sync()
        self.accept()


class ReminderController:
    def __init__(self, owner):
        self.owner = owner
        self.store = ReminderStore(owner.store.path.with_name(owner.store.path.stem + '-reminders.json'))
        self.sound = ReminderSound(owner)
        self.sound.failed.connect(self.audio_error)
        self.popups = []
        self.processes = []
        self.last_error = ''
        self.closed = False
        self.timer = QTimer(owner)
        self.timer.timeout.connect(self.check)
        self.timer.start(1000)
        QTimer.singleShot(1000, self.check)

    def changed(self):
        self.owner.refresh()
        if self.owner.desktop_widget:
            self.owner.desktop_widget.update_clock()

    def audio_error(self, text):
        self.owner.statusBar().showMessage(text)
        for popup in self.popups:
            popup.audio_status.setText(text)

    def check(self, now=None):
        if self.closed:
            return
        try:
            due = self.store.take_due(now)
        except (OSError, ValueError) as error:
            # Do not signal and lose persistence if writing the delivery state failed.
            text = 'Muistutuksen tilan tallennus epäonnistui: ' + str(error)
            if text != self.last_error:
                self.owner.statusBar().showMessage(text)
                self.last_error = text
            return
        if due:
            self.changed()
            for value in due:
                self.show_notification(value)
            self.sound.play(**sound_options(self.owner.settings))

    def show_notification(self, value):
        # A native GNOME banner plus our accessible, persistent action window.
        import shutil
        import html
        if shutil.which('notify-send'):
            process = QProcess(self.owner)
            self.processes.append(process)
            process.finished.connect(lambda *args, p=process: self.release_process(p))
            process.start('notify-send', ['--app-name=Varjoaika', '--hint=boolean:suppress-sound:true',
                          '--icon=appointment-soon', '--', value['title'], html.escape(value['body'] or 'Varjoajan muistutus')])
        popup = QDialog(None)
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup.setWindowTitle('Huuhkaja muistuttaa · Varjoaika')
        popup.resize(430, 280)
        layout = QVBoxLayout(popup)
        heading = QLabel(value['title'])
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setWordWrap(True)
        heading.setObjectName('title')
        layout.addWidget(heading)
        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setAcceptRichText(False)
        detail.setPlainText(value['body'] or 'Aika pysähtyä hetkeksi.')
        detail.setMaximumHeight(140)
        layout.addWidget(detail)
        stamp = QLabel(CalendarDate.from_key(value['date']).label + ' · ' + parse_instant(value['due']).astimezone().strftime('%H:%M'))
        stamp.setWordWrap(True)
        stamp.setObjectName('muted')
        layout.addWidget(stamp)
        popup.audio_status = QLabel('')
        popup.audio_status.setWordWrap(True)
        layout.addWidget(popup.audio_status)
        buttons = QHBoxLayout()
        snooze = QPushButton('Siirrä 10 min')
        def defer():
            try:
                self.store.snooze(value['id'])
            except (OSError, ValueError) as error:
                QMessageBox.warning(popup, 'Siirto epäonnistui', str(error))
                return
            self.changed()
            popup.close()
        snooze.clicked.connect(defer)
        buttons.addWidget(snooze)
        close = QPushButton('Kuittaa')
        close.clicked.connect(popup.close)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.popups.append(popup)
        popup.finished.connect(lambda result, p=popup: self.popup_closed(p))
        popup.show()
        popup.raise_()
        popup.activateWindow()

    def release_process(self, process):
        if process in self.processes:
            self.processes.remove(process)
        process.deleteLater()

    def popup_closed(self, popup):
        if popup in self.popups:
            self.popups.remove(popup)
        if not self.popups:
            self.sound.stop()

    def shutdown(self):
        self.closed = True
        self.timer.stop()
        self.sound.stop()
        for popup in list(self.popups):
            popup.close()
