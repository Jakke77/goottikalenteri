"""Transparent, movable desktop clock and its separate settings dialog."""
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt6.QtWidgets import (QApplication, QWidget, QDialog, QCheckBox,
    QDialogButtonBox, QVBoxLayout, QFormLayout, QFontComboBox, QSpinBox,
    QComboBox, QPushButton, QColorDialog, QMenu, QLabel)
from calendar_model import from_gregorian, MONTH_NAMES, weekday, WEEKDAY_NAMES

DEFAULTS = {
    'font': 'DejaVu Sans', 'clock_size': 40, 'date_size': 15, 'year_size': 13,
    'opacity': 100, 'color': '#25c5ff', 'seconds': True, 'locked': False,
    'on_top': False, 'alignment': 'left',
}

def load_options(settings):
    return {name: settings.value('widget/' + name, default, type=type(default))
            for name, default in DEFAULTS.items()}

class DesktopWidget(QWidget):
    def __init__(self, owner, settings):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.owner, self.settings = owner, settings
        self.setWindowTitle('Goottikalenteri-widget')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        # Override the application's opaque global QWidget stylesheet.
        self.setStyleSheet('background: transparent; border: none;')
        self.lines = []
        self.origin = None
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
        self.options = dict(options)
        visible = self.isVisible()
        position = self.pos()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.options['on_top'])
        self.setCursor(Qt.CursorShape.ArrowCursor if self.options['locked']
                       else Qt.CursorShape.SizeAllCursor)
        self.update_clock()
        if visible:
            self.show()
            self.move(position)

    def update_clock(self):
        now = datetime.now()
        clock = now.strftime('%H:%M:%S' if self.options['seconds'] else '%H:%M')
        try:
            fictional = from_gregorian(now.date())
            date_text = (f'{WEEKDAY_NAMES[weekday(fictional)]} · Päivä {fictional.day}\n'
                         f'{fictional.month}. {MONTH_NAMES[fictional.month]}')
            year_text = f'Vuosi {fictional.year:04d}'
        except ValueError:
            date_text, year_text = 'Ennen ajanlaskun alkua', ''
        self.lines = []
        for text, key in ((clock, 'clock_size'), (date_text, 'date_size'),
                          (year_text, 'year_size')):
            font = QFont(self.options['font'], self.options[key])
            if key == 'clock_size':
                font.setBold(True)
            for line in text.splitlines():
                self.lines.append((line, font))
        width = max((QFontMetrics(font).horizontalAdvance(text)
                     for text, font in self.lines), default=100) + 32
        height = sum(QFontMetrics(font).height() + 5 for _, font in self.lines) + 24
        self.setFixedSize(width, height)
        self.setAccessibleName(clock + ' · ' + date_text.replace('\n', ' · ') + ' · ' + year_text)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        color = QColor(self.options['color'])
        color.setAlpha(round(255 * self.options['opacity'] / 100))
        shadow = QColor(0, 0, 0, round(180 * self.options['opacity'] / 100))
        y = 12
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
        self.resize(470, 520)
        layout = QVBoxLayout(self)
        self.enabled = QCheckBox('Näytä läpinäkyvä työpöytäkello')
        self.enabled.setChecked(owner.widget_enabled)
        layout.addWidget(self.enabled)
        form = QFormLayout()
        self.font_picker = QFontComboBox()
        self.font_picker.setCurrentFont(QFont(self.original['font']))
        form.addRow('Fontti', self.font_picker)
        self.controls = {}
        for key, title, minimum, maximum, suffix in (
            ('clock_size', 'Kellon tekstikoko', 8, 160, ' pt'),
            ('date_size', 'Päivämäärän tekstikoko', 8, 100, ' pt'),
            ('year_size', 'Vuosiluvun tekstikoko', 8, 100, ' pt'),
            ('opacity', 'Tekstin peittävyys', 15, 100, ' %')):
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
        for key, title in [('seconds', 'Näytä sekunnit'), ('locked', 'Lukitse sijainti'),
                           ('on_top', 'Pidä muiden ikkunoiden päällä')]:
            control = QCheckBox(title)
            control.setChecked(self.original[key])
            self.controls[key] = control
            layout.addWidget(control)
        reset = QPushButton('Palauta ulkoasun oletukset')
        reset.clicked.connect(self.reset_defaults)
        layout.addWidget(reset)
        info = QLabel('Vedä kellon tekstistä siirtääksesi sitä.\n'
                      'Hiiren oikea painike tai kaksoisnapsautus avaa asetukset.\n'
                      'Muutokset näkyvät heti; Peruuta palauttaa aiemman ulkoasun.')
        info.setWordWrap(True)
        layout.addWidget(info)
        buttons = QDialogButtonBox()
        buttons.addButton('Tallenna', QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton('Peruuta', QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.font_picker.currentFontChanged.connect(self.preview)
        self.alignment.currentIndexChanged.connect(self.preview)
        for control in self.controls.values():
            if isinstance(control, QSpinBox):
                control.valueChanged.connect(self.preview)
            else:
                control.toggled.connect(self.preview)

    def options(self):
        result = {'font': self.font_picker.currentFont().family(), 'color': self.color,
                  'alignment': self.alignment.currentData()}
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
