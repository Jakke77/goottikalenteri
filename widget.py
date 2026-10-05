"""Transparent, movable desktop clock and its separate settings dialog."""
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QLinearGradient
from PyQt6.QtWidgets import (QApplication, QWidget, QDialog, QCheckBox,
    QDialogButtonBox, QVBoxLayout, QFormLayout, QFontComboBox, QSpinBox,
    QComboBox, QPushButton, QColorDialog, QMenu, QLabel, QLineEdit, QToolButton, QScrollArea)
from weather import WeatherService
from calendar_model import CalendarDate, from_gregorian, MONTH_NAMES, weekday, WEEKDAY_NAMES
from reminders import parse_instant
from startup import startup_choices, set_autostart

FINNISH_MONTHS = ('tammikuuta', 'helmikuuta', 'maaliskuuta', 'huhtikuuta',
                  'toukokuuta', 'kesäkuuta', 'heinäkuuta', 'elokuuta',
                  'syyskuuta', 'lokakuuta', 'marraskuuta', 'joulukuuta')

DEFAULTS = {
    'font': 'Ubuntu', 'clock_size': 40, 'date_size': 15, 'year_size': 13, 'official_size': 11,
    'opacity': 100, 'color': '#d9b3a0', 'seconds': True, 'locked': False,
    'on_top': False, 'alignment': 'left',
    'theme': 'shadow', 'background_opacity': 32, 'agenda': True,
    'weather_enabled': False, 'weather_auto': True, 'weather_city': '', 'weather_size': 11,
}

def load_options(settings):
    return {name: settings.value('widget/' + name, default, type=type(default))
            for name, default in DEFAULTS.items()}

class DesktopWidget(QWidget):
    def __init__(self, owner, settings):
        # A tool window can be kept above its application's calendar by GNOME.
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.owner, self.settings = owner, settings
        self.setWindowTitle('Varjoaika-widget')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        # Override the application's opaque global QWidget stylesheet.
        self.setStyleSheet('background: transparent; border: none;')
        self.buttons = []
        for text, tip, action in [('↗', 'Avaa kalenteri', self.open_calendar),
                                  ('◷', 'Muistutukset', owner.open_reminders),
                                  ('⚙', 'Widgetin asetukset', owner.open_settings)]:
            button = QToolButton(self)
            button.setText(text)
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.clicked.connect(action)
            button.setStyleSheet('QToolButton {color: #e3bea9; background: transparent; border: none; font-size: 17px;} QToolButton:hover {background: #39242d; border-radius: 5px;}')
            self.buttons.append(button)
        self.lines = []
        self.origin = None
        self.weather = WeatherService(settings, self)
        self.weather.changed.connect(self.update_clock)
        self.apply_options(load_options(settings))
        geometry = settings.value('widget/geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)
            self.update_clock()
        else:
            screen = QApplication.primaryScreen()
            if screen:
                area = screen.availableGeometry()
                self.move(area.right() - self.width() - 32, area.top() + 32)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

    def apply_options(self, options):
        self.options = {**DEFAULTS, **options}
        self.weather.configure(self.options)
        visible = self.isVisible()
        position = self.pos()
        flags = self.windowFlags() & ~(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowStaysOnBottomHint)
        flags |= (Qt.WindowType.WindowStaysOnTopHint if self.options['on_top']
                  else Qt.WindowType.WindowStaysOnBottomHint)
        self.setWindowFlags(flags)
        self.setCursor(Qt.CursorShape.ArrowCursor if self.options['locked']
                       else Qt.CursorShape.SizeAllCursor)
        self.update_clock()
        if visible:
            self.show()
            self.move(position)
            self.clamp_position()

    def clamp_position(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            x = max(area.left(), min(self.x(), area.right() - self.width() + 1))
            y = max(area.top(), min(self.y(), area.bottom() - self.height() + 1))
            if QPoint(x, y) != self.pos():
                self.move(x, y)

    def update_clock(self):
        now = self.owner.time_service.now() if hasattr(self.owner, "time_service") else datetime.now()
        clock = now.strftime('%H:%M:%S' if self.options['seconds'] else '%H:%M')
        try:
            fictional = from_gregorian(now.date())
            date_text = (f'{WEEKDAY_NAMES[weekday(fictional)]} · Päivä {fictional.day}\n'
                         f'{fictional.month}. {MONTH_NAMES[fictional.month]}')
            year_text = f'Varjoaika · Vuosi {fictional.year:04d}'
        except ValueError:
            date_text, year_text = 'Ennen ajanlaskun alkua', ''
        official_text = (f'{now.day}. {FINNISH_MONTHS[now.month - 1]} {now.year}')
        weather_text = '\n'.join(self.weather.lines) if self.options['weather_enabled'] else ''
        if self.options['weather_enabled'] and not self.options['weather_auto'] and not self.options['weather_city'].strip():
            weather_text = 'Anna sään paikkakunta asetuksissa.'
        self.lines = []
        for text, key in ((clock, 'clock_size'), (date_text, 'date_size'),
                          (year_text, 'year_size'), (official_text, 'official_size'),
                          (weather_text, 'weather_size')):
            font = QFont(self.options['font'], self.options[key])
            if key == 'clock_size':
                font.setBold(True)
            for line in text.splitlines():
                self.lines.append((line, font))
        if self.options['agenda'] and hasattr(self.owner, 'reminders'):
            pending = self.owner.reminders.store.pending()
            if self.options['theme'] == 'shadow':
                self.lines.append(('SEURAAVA HUHUILU', QFont(self.options['font'], 9)))
            if pending:
                value = pending[0]
                instant = parse_instant(value['due']).astimezone()
                date = CalendarDate.from_key(value['date'])
                title = QFontMetrics(QFont(self.options['font'], 11)).elidedText(value['title'], Qt.TextElideMode.ElideRight, 330)
                self.lines.append((title, QFont(self.options['font'], 11)))
                self.lines.append((f'{date.day}. {MONTH_NAMES[date.month]} · {instant:%H:%M}', QFont(self.options['font'], 10)))
            else:
                self.lines.append(('Ei odottavia muistutuksia', QFont(self.options['font'], 10)))
        width = max((QFontMetrics(font).horizontalAdvance(text)
                     for text, font in self.lines), default=100) + 32
        height = sum(QFontMetrics(font).height() + 5 for _, font in self.lines) + 24
        if self.options['theme'] == 'shadow':
            width = max(350, width + 16)
            height += 48
        self.setFixedSize(width, height)
        self.clamp_position()
        for i, button in enumerate(self.buttons):
            button.setVisible(self.options['theme'] == 'shadow')
            button.setGeometry(width - 112 + i * 32, 10, 28, 28)
        self.setAccessibleName(clock + ' · ' + date_text.replace('\n', ' · ') + ' · ' + year_text + ' · ' + official_text)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        color = QColor(self.options['color'])
        color.setAlpha(round(255 * self.options['opacity'] / 100))
        shadow = QColor(0, 0, 0, round(180 * self.options['opacity'] / 100))
        themed = self.options['theme'] == 'shadow'
        if themed and self.options['background_opacity'] > 0:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            alpha = self.options['background_opacity'] / 100
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor(33, 22, 34, round(255 * alpha)))
            gradient.setColorAt(1, QColor(8, 10, 18, round(255 * alpha)))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor(175, 115, 91, round(150 * alpha)), 1))
            painter.drawRoundedRect(QRectF(1, 1, self.width() - 2, self.height() - 2), 16, 16)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(190, 118, 88, round(48 * alpha)), 1))
            painter.drawEllipse(QRectF(self.width() - 225, -70, 290, 290))
            painter.drawEllipse(QRectF(self.width() - 260, -110, 360, 360))
        if themed:
            painter.setFont(QFont(self.options['font'], 9))
            painter.setPen(QColor('#ba9586'))
            painter.drawText(20, 28, '◔  VARJOAIKA')
        y = 48 if themed else 12
        for text, font in self.lines:
            metrics = QFontMetrics(font)
            painter.setFont(font)
            y += metrics.ascent()
            width = metrics.horizontalAdvance(text)
            if self.options['alignment'] == 'center':
                x = (self.width() - width) // 2
            elif self.options['alignment'] == 'right':
                x = self.width() - width - 16
            else:
                x = 16
            painter.setPen(shadow)
            painter.drawText(x + 1, y + 1, text)
            painter.setPen(color)
            painter.drawText(x, y, text)
            y += metrics.height() - metrics.ascent() + 5

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.options['locked']:
            handle = self.windowHandle()
            if handle and handle.startSystemMove():
                return
            self.origin = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.origin = None
        self.save_position()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.owner.open_settings()

    def contextMenuEvent(self, event):
        # Keep the menu dark; the widget itself has no visible controls or frame.
        menu = QMenu(self.owner)
        menu.addAction('Widgetin asetukset…', self.owner.open_settings)
        menu.addAction('Muistutukset…', self.owner.open_reminders)
        menu.addAction('Ilmoitukset ja ääni…', self.owner.open_sound_settings)
        status = menu.addAction(self.owner.time_service.status)
        status.setEnabled(False)
        menu.addAction('Päivitä sää nyt', lambda: self.weather.refresh(force=True))
        menu.addAction('Avaa kalenteri', self.open_calendar)
        menu.addAction('Piilota widget', lambda: self.owner.set_widget_enabled(False))
        menu.addSeparator()
        menu.addAction('Lopeta', QApplication.instance().quit)
        menu.exec(event.globalPos())

    def open_calendar(self):
        self.owner.showNormal()
        self.owner.raise_()
        self.owner.activateWindow()
        self.owner.go_today()

    def save_position(self):
        self.settings.setValue('widget/geometry', self.saveGeometry())

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.isVisible():
            self.save_position()

    def hideEvent(self, event):
        self.save_position()
        super().hideEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.original = load_options(owner.settings)
        self.setWindowTitle('Työpöytäwidgetin asetukset')
        self.resize(650, 820)
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        self.enabled = QCheckBox('Näytä työpöytäwidget')
        self.enabled.setChecked(owner.widget_enabled)
        layout.addWidget(self.enabled)
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItem('Varjokupari · Ubuntu 26.04', 'shadow')
        self.theme.addItem('Pelkkä läpinäkyvä teksti', 'transparent')
        self.theme.setCurrentIndex(self.theme.findData(self.original['theme']))
        form.addRow('Teema', self.theme)
        self.font_picker = QFontComboBox()
        self.font_picker.setCurrentFont(QFont(self.original['font']))
        form.addRow('Fontti', self.font_picker)
        self.controls = {}
        for key, title, minimum, maximum, suffix in (
            ('clock_size', 'Kellon tekstikoko', 8, 160, ' pt'),
            ('date_size', 'Päivämäärän tekstikoko', 8, 100, ' pt'),
            ('year_size', 'Vuosiluvun tekstikoko', 8, 100, ' pt'),
            ('official_size', 'Virallisen päivämäärän tekstikoko', 8, 100, ' pt'),
            ('weather_size', 'Sääennusteen tekstikoko', 8, 40, ' pt'),
            ('opacity', 'Tekstin peittävyys', 15, 100, ' %'),
            ('background_opacity', 'Taustan peittävyys', 0, 100, ' %')):
            control = QSpinBox()
            control.setRange(minimum, maximum)
            control.setSuffix(suffix)
            control.setValue(self.original[key])
            self.controls[key] = control
            form.addRow(title, control)
        self.alignment = QComboBox()
        for title, value in [('Vasemmalle', 'left'), ('Keskelle', 'center'), ('Oikealle', 'right')]:
            self.alignment.addItem(title, value)
        self.alignment.setCurrentIndex(self.alignment.findData(self.original['alignment']))
        form.addRow('Tasaus', self.alignment)
        self.color = self.original['color']
        self.color_button = QPushButton('Valitse tekstin väri…')
        self.color_button.clicked.connect(self.pick_color)
        form.addRow('Tekstin väri', self.color_button)
        layout.addLayout(form)
        self.city = QLineEdit(self.original['weather_city'])
        self.city.setPlaceholderText('Esim. Helsinki, Finland tai kylän nimi')
        form.addRow('Sään paikkakunta', self.city)
        self.city.textChanged.connect(self.preview)
        for key, title in [('agenda', 'Näytä seuraava muistutus'), ('weather_enabled', 'Näytä wttr.in-sää (3 päivää)'),
                           ('weather_auto', 'Hae sijainti automaattisesti IP-osoitteesta'),
                           ('seconds', 'Näytä sekunnit'), ('locked', 'Lukitse sijainti'),
                           ('on_top', 'Pidä muiden ikkunoiden päällä')]:
            control = QCheckBox(title)
            control.setChecked(self.original[key])
            self.controls[key] = control
            layout.addWidget(control)
        startup_widget, startup_calendar = startup_choices()
        self.startup_widget = QCheckBox('Avaa widget kirjautuessa')
        self.startup_widget.setChecked(startup_widget)
        self.startup_calendar = QCheckBox('Avaa kalenteri kirjautuessa')
        self.startup_calendar.setChecked(startup_calendar)
        outer.addWidget(self.startup_widget)
        outer.addWidget(self.startup_calendar)
        reset = QPushButton('Palauta ulkoasun oletukset')
        reset.clicked.connect(self.reset_defaults)
        layout.addWidget(reset)
        info = QLabel('Vedä kellon tekstistä siirtääksesi sitä.\n'
                      'Hiiren oikea painike tai kaksoisnapsautus avaa asetukset.\n'
                      'Automaattinen sääsijainti on IP-osoitteesta arvioitu, ei GPS.\n'
                      'Sää haetaan tunnin välein verkosta palvelusta wttr.in.\n'
                      'Muutokset näkyvät heti; Peruuta palauttaa aiemman ulkoasun.')
        info.setWordWrap(True)
        layout.addWidget(info)
        buttons = QDialogButtonBox()
        buttons.addButton('Tallenna', QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton('Peruuta', QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.theme.currentIndexChanged.connect(self.preview)
        self.font_picker.currentFontChanged.connect(self.preview)
        self.alignment.currentIndexChanged.connect(self.preview)
        for control in self.controls.values():
            if isinstance(control, QSpinBox):
                control.valueChanged.connect(self.preview)
            else:
                control.toggled.connect(self.preview)

    def accept(self):
        try:
            set_autostart(self.startup_widget.isChecked(), self.startup_calendar.isChecked())
        except OSError as error:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, 'Automaattikäynnistys epäonnistui', str(error))
            return
        super().accept()

    def options(self):
        result = {'theme': self.theme.currentData(), 'font': self.font_picker.currentFont().family(), 'color': self.color,
                  'alignment': self.alignment.currentData(), 'weather_city': self.city.text()}
        for key, control in self.controls.items():
            result[key] = control.value() if isinstance(control, QSpinBox) else control.isChecked()
        return result

    def preview(self, *args):
        if self.owner.desktop_widget is not None:
            self.owner.desktop_widget.apply_options(self.options())

    def pick_color(self):
        color = QColorDialog.getColor(QColor(self.color), self, 'Tekstin väri')
        if color.isValid():
            self.color = color.name()
            self.preview()

    def reset_defaults(self):
        self.theme.setCurrentIndex(self.theme.findData(DEFAULTS['theme']))
        self.city.setText(DEFAULTS['weather_city'])
        self.font_picker.setCurrentFont(QFont(DEFAULTS['font']))
        for key, control in self.controls.items():
            if isinstance(control, QSpinBox):
                control.setValue(DEFAULTS[key])
            else:
                control.setChecked(DEFAULTS[key])
        self.alignment.setCurrentIndex(0)
        self.color = DEFAULTS['color']
        self.preview()

    def reject(self):
        if self.owner.desktop_widget is not None:
            self.owner.desktop_widget.apply_options(self.original)
        super().reject()
