"""Dark, keyboard-accessible PyQt6 desktop interface."""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QGridLayout, QInputDialog, QComboBox, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
)
from calendar_model import (CalendarDate, MONTH_NAMES, moon_label,
                            from_gregorian, weekday, WEEKDAY_NAMES, WEEKDAY_SHORT_NAMES)
from time_service import TimeService
from PyQt6.QtCore import QTimer, QSettings
from widget import DesktopWidget, SettingsDialog, load_options

from theme import STYLE, LunarBanner, MONTH_MOTIFS, DayButton
from reminder_ui import ReminderController, AgendaDialog, SoundSettingsDialog

class NoteDialog(QDialog):
    def __init__(self, date, store, parent=None):
        super().__init__(parent)
        self.date, self.store = date, store
        self.setWindowTitle(date.label)
        self.resize(620, 430)
        layout = QVBoxLayout(self)
        heading = QLabel(date.label)
        heading.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(QLabel(f'Kuun vaihe: {moon_label(date.day)}'))
        layout.addWidget(QLabel(WEEKDAY_NAMES[weekday(date)]))
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText('Kirjoita päivän tapahtumat ja muistiinpanot…')
        self.editor.setPlainText(store.get(date))
        self.editor.setAccessibleName('Päivän muistiinpanot')
        layout.addWidget(self.editor)
        reminders = QPushButton('◷ Päivän muistutukset…')
        reminders.clicked.connect(lambda: AgendaDialog(parent, date, self).exec())
        reminders.setEnabled(parent is not None and hasattr(parent, 'reminders'))
        layout.addWidget(reminders)
        buttons = QDialogButtonBox()
        save = buttons.addButton('Tallenna', QDialogButtonBox.ButtonRole.AcceptRole)
        cancel = buttons.addButton('Peruuta', QDialogButtonBox.ButtonRole.RejectRole)
        delete = buttons.addButton('Poista', QDialogButtonBox.ButtonRole.DestructiveRole)
        save.clicked.connect(self.save)
        cancel.clicked.connect(self.reject)
        delete.clicked.connect(self.delete)
        delete.setEnabled(bool(store.get(date)))
        layout.addWidget(buttons)
        shortcut = QShortcut(QKeySequence('Ctrl+Return'), self)
        shortcut.activated.connect(self.save)

    def persist(self, text):
        try:
            self.store.save_note(self.date, text)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, 'Tallennus epäonnistui', str(error))
            return
        self.accept()

    def save(self):
        self.persist(self.editor.toPlainText())

    def delete(self):
        answer = QMessageBox.question(self, 'Poista muistiinpano',
                                      'Poistetaanko tämän päivän tallennettu muistiinpano?',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.persist('')

class CalendarWindow(QMainWindow):
    def __init__(self, store, restore_widget=True):
        super().__init__()
        self.store = store
        self.settings = QSettings()
        self.time_service = TimeService(self.settings, self)
        self.widget_enabled = (self.settings.value('widget/enabled', False, type=bool) if restore_widget else False)
        self.desktop_widget = None
        self.widget_only = False
        try:
            self.date = from_gregorian(self.time_service.now().date())
        except ValueError:
            self.date = CalendarDate()
        self.setWindowTitle('Varjoaika')
        self.resize(1080, 900)
        self.setMinimumSize(680, 540)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)
        eyebrow = QLabel('VARJOAIKA   /   KUUN VARJOJEN KIERTO')
        eyebrow.setObjectName('muted')
        layout.addWidget(eyebrow)
        self.title = QLabel()
        self.title.setObjectName('title')
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.banner = LunarBanner()
        layout.addWidget(self.banner)
        self.subtitle = QLabel('13 kuukautta · 30 päivää · 7 päivän viikko · 24 h / päivä · Päivä 0: uusikuu')
        self.subtitle.setObjectName('muted')
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)
        nav = QHBoxLayout()
        self.prev_year = self.nav_button('« Vuosi', lambda: self.navigate(years=-1), nav, 'Edellinen vuosi')
        self.prev_month = self.nav_button('‹ Kuu', lambda: self.navigate(months=-1), nav, 'Edellinen kuukausi')
        nav.addStretch()
        self.nav_button('Tänään', self.go_today, nav, 'Näytä tämä päivä')
        self.nav_button('Kuu ›', lambda: self.navigate(months=1), nav, 'Seuraava kuukausi')
        self.nav_button('Vuosi »', lambda: self.navigate(years=1), nav, 'Seuraava vuosi')
        self.nav_button('⚙', self.open_settings, nav, 'Widgetin asetukset')
        jump_row = QHBoxLayout()
        self.nav_button('Siirry vuoteen…', self.jump_year, jump_row, 'Siirry haluttuun vuoteen')
        self.month_picker = QComboBox()
        self.month_picker.setAccessibleName('Valitse kuukausi')
        self.month_picker.addItems([f'{index}. {name}' for index, name in enumerate(MONTH_NAMES)])
        self.month_picker.currentIndexChanged.connect(self.select_month)
        jump_row.addWidget(self.month_picker)
        self.nav_button('Vuoden kaikki kuukaudet', self.year_overview, jump_row, 'Näytä kaikki 13 kuukautta')
        self.nav_button('◷ Muistutukset', self.open_reminders, jump_row, 'Muistutukset')
        self.nav_button('♫', self.open_sound_settings, jump_row, 'Ilmoitukset ja ääni')
        layout.addLayout(nav)
        layout.addLayout(jump_row)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        self.grid = grid = QGridLayout(panel)
        grid.setSpacing(10)
        for column, name in enumerate(WEEKDAY_SHORT_NAMES):
            label = QLabel(name)
            label.setToolTip(WEEKDAY_NAMES[column])
            label.setAccessibleName(WEEKDAY_NAMES[column])
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(label, 0, column)
        self.days = []
        for day in range(30):
            button = DayButton()
            button.setCheckable(True)
            button.setMinimumSize(88, 68)
            button.clicked.connect(lambda checked=False, d=day: self.edit_day(d))
            grid.addWidget(button, 1 + day // 7, day % 7)
            self.days.append(button)
        for column in range(7):
            grid.setColumnStretch(column, 1)
        for row in range(1, 7):
            grid.setRowStretch(row, 1)
        scroll.setWidget(panel)
        layout.addWidget(scroll, 1)
        self.footer = QLabel()
        self.footer.setObjectName('muted')
        self.footer.setWordWrap(True)
        layout.addWidget(self.footer)
        self.statusBar().showMessage(f'Tallennus: {store.path}')
        for sequence, action in [('Alt+Left', lambda: self.navigate(months=-1)),
                                 ('Alt+Right', lambda: self.navigate(months=1)),
                                 ('Alt+Up', lambda: self.navigate(years=1)),
                                 ('Alt+Down', lambda: self.navigate(years=-1))]:
            QShortcut(QKeySequence(sequence), self).activated.connect(action)
        self.reminders = ReminderController(self)
        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(60000)
        self.set_widget_enabled(self.widget_enabled, persist=False)

    def set_widget_enabled(self, enabled, persist=True):
        self.widget_enabled = enabled
        if persist:
            self.settings.setValue('widget/enabled', enabled)
        if enabled:
            if self.desktop_widget is None:
                self.desktop_widget = DesktopWidget(self, self.settings)
            self.desktop_widget.apply_options(load_options(self.settings))
            self.desktop_widget.show()
        elif self.desktop_widget is not None:
            self.desktop_widget.hide()
            if self.widget_only and not self.isVisible():
                self.show()

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for key, value in dialog.options().items():
                self.settings.setValue('widget/' + key, value)
            self.set_widget_enabled(dialog.enabled.isChecked())
            self.settings.sync()

    def open_reminders(self):
        AgendaDialog(self).exec()

    def open_sound_settings(self):
        SoundSettingsDialog(self).exec()

    def closeEvent(self, event):
        if self.widget_enabled or self.reminders.store.pending():
            if not self.widget_enabled:
                self.set_widget_enabled(True, persist=False)
            self.hide()
            event.ignore()
            return
        if self.desktop_widget is not None:
            self.desktop_widget.hide()
        self.reminders.shutdown()
        self.time_service.shutdown()
        self.settings.sync()
        super().closeEvent(event)
        if self.widget_only:
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().quit()

    def go_today(self):
        try:
            self.date = from_gregorian(self.time_service.now().date())
        except ValueError:
            return
        self.refresh()

    def nav_button(self, text, action, layout, accessible):
        button = QPushButton(text)
        button.setAccessibleName(accessible)
        button.clicked.connect(action)
        layout.addWidget(button)
        return button

    def select_month(self, month):
        self.date = CalendarDate(self.date.year, month, self.date.day)
        self.refresh()

    def year_overview(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Vuosi {self.date.year:04d} · Kaikki 13 kuukautta')
        layout = QVBoxLayout(dialog)
        grid = QGridLayout()
        for month, name in enumerate(MONTH_NAMES):
            count = sum(bool(self.store.get(CalendarDate(self.date.year, month, day)))
                        for day in range(30))
            button = QPushButton(f'{month}. {name}\n{count} päivää muistiinpanoilla')
            button.setCheckable(True)
            button.setChecked(month == self.date.month)
            def choose(checked=False, selected=month):
                self.select_month(selected)
                dialog.accept()
            button.clicked.connect(choose)
            grid.addWidget(button, month // 3, month % 3)
        layout.addLayout(grid)
        close = QPushButton('Sulje')
        close.clicked.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()

    def jump_year(self):
        text, accepted = QInputDialog.getText(
            self, 'Siirry vuoteen', 'Vuosi (vähintään 1):', text=str(self.date.year))
        if not accepted:
            return
        try:
            year = int(text.strip())
            self.date = CalendarDate(year, self.date.month, self.date.day)
        except ValueError:
            QMessageBox.warning(self, 'Virheellinen vuosi', 'Anna positiivinen kokonaisluku.')
            return
        self.refresh()

    def navigate(self, months=0, years=0):
        try:
            self.date = self.date.shift_month(months).shift_year(years)
        except ValueError:
            return
        self.refresh()

    def refresh(self):
        self.title.setText(f'{self.date.month}. {MONTH_NAMES[self.date.month]}  ·  Vuosi {self.date.year:04d}')
        motif, accent = MONTH_MOTIFS[self.date.month]
        self.title.setStyleSheet(f'color: {accent}; font-size: 30px; font-weight: bold;')
        self.banner.day, self.banner.month = self.date.day, self.date.month
        self.banner.update()
        self.subtitle.setText(f'{motif} · 13 kuuta · 30 päivää · Kuun vaiheet ovat symbolisia')
        self.month_picker.blockSignals(True)
        self.month_picker.setCurrentIndex(self.date.month)
        self.month_picker.blockSignals(False)
        self.prev_year.setEnabled(self.date.year > 1)
        self.prev_month.setEnabled(self.date.year > 1 or self.date.month > 0)
        count = 0
        try:
            current = from_gregorian(self.time_service.now().date())
        except ValueError:
            current = None
        start = weekday(CalendarDate(self.date.year, self.date.month, 0))
        for day, button in enumerate(self.days):
            date = CalendarDate(self.date.year, self.date.month, day)
            self.grid.removeWidget(button)
            self.grid.addWidget(button, 1 + (start + day) // 7, (start + day) % 7)
            note = self.store.get(date)
            reminders = self.reminders.store.on_date(date)
            pending = sum(value['enabled'] and value['delivered'] is None for value in reminders)
            count += bool(note)
            phase = 'UUSIKUU' if day == 0 else ('TÄYSIKUU' if day == 15 else '')
            today = date == current
            labels = [f'{day}' + ('  TÄNÄÄN' if today else '')]
            if phase:
                labels.append(phase)
            if note:
                labels.append('● Merkintä')
            if pending:
                labels.append(f'◷ {pending} ' + ('muistutus' if pending == 1 else 'muistutusta'))
            button.setText('\n'.join(labels))
            button.setProperty('moonDay', day)
            button.setProperty('moonAccent', accent)
            button.setProperty('isToday', today)
            button.setChecked(day == self.date.day)
            button.setProperty('hasNote', bool(note))
            button.setProperty('hasReminder', bool(pending))
            button.setAccessibleName(date.label + (', muistiinpano' if note else '') + (f', {pending} muistutusta' if pending else ''))
            button.setToolTip(f'{moon_label(day)}\n{note[:240]}' if note else moon_label(day))
            button.style().unpolish(button)
            button.style().polish(button)
        today_label = f'Tänään: {current.label}' if current else 'Ennen ajanlaskun alkua'
        self.footer.setText(f'{today_label}\n{count} päivää merkinnöillä · {len(self.reminders.store.pending())} odottavaa muistutusta · 390 päivää vuodessa')

    def edit_day(self, day):
        self.date = CalendarDate(self.date.year, self.date.month, day)
        self.refresh()
        NoteDialog(self.date, self.store, self).exec()
        self.refresh()
