"""Shadow Copper palette, symbolic lunar decoration and month atmosphere."""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget, QPushButton

MONTH_MOTIFS = (
    ('Hiljaiset varjot', '#ce967c'), ('Hopeinen halla', '#b1bccc'),
    ('Jään alla', '#93a9ba'), ('Korpin siiven alla', '#b79a87'),
    ('Unohdetut polut', '#b28c82'), ('Kivien hiljaisuus', '#a9a69b'),
    ('Yön syvä hengitys', '#9e95bf'), ('Kuparinen kuu', '#db826c'),
    ('Valon viimeinen kaari', '#bd97a5'), ('Lehtien viimeinen tanssi', '#c29d75'),
    ('Hiljainen kuiskaus', '#b7bdbe'), ('Sumun verhossa', '#a6aaa7'),
    ('Sielujen tähtikehä', '#c4adc2'),
)

STYLE = '''
QWidget { background: #0e0d13; color: #e9d9d0; font-size: 14px; }
QLabel#title { color: #dbad94; font-size: 30px; font-weight: bold; }
QLabel#muted { color: #b19b94; }
QLabel#section { color: #d9a98f; font-weight: bold; }
QPushButton { background: #1c171e; border: 1px solid #57413f; border-radius: 9px; padding: 9px 13px; }
QPushButton:hover { background: #302028; border-color: #d2997c; }
QPushButton:focus { border: 2px solid #e9b89b; }
QPushButton:pressed, QPushButton:checked { background: #342229; border: 2px solid #c28b73; }
QPushButton:disabled { color: #756668; border-color: #342b32; }
QPushButton[isToday="true"] { background: #3a252a; border: 2px solid #e7ad8c; }
QPushButton[hasNote="true"] { color: #f0c7ad; }
QPushButton[hasReminder="true"] { border-color: #c5927f; }
QTextEdit, QLineEdit, QSpinBox, QTimeEdit { background: #18151d; border: 1px solid #69504c;
 border-radius: 6px; padding: 8px; selection-background-color: #79534d; }
QComboBox { background: #1c171e; border: 1px solid #69504c; border-radius: 6px; padding: 8px; }
QComboBox QAbstractItemView { background: #1c171e; color: #e9d9d0; selection-background-color: #79534d; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #18151d; width: 12px; }
QScrollBar::handle:vertical { background: #674744; min-height: 24px; }
QToolTip { background: #211921; color: #f0d6c6; border: 1px solid #c18c76; }
QListWidget { background: #15121a; border: 1px solid #57413f; border-radius: 8px; padding: 8px; }
QListWidget::item { padding: 10px; border-bottom: 1px solid #352730; }
QListWidget::item:selected { background: #3a252f; color: #ffe0c9; }
'''


def paint_moon(painter, rect, day, accent):
    """Symbolic phase of the fictional 30-day cycle, not an astronomy claim."""
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(accent), 1.2))
    painter.setBrush(QColor('#201922'))
    painter.drawEllipse(rect)
    if day != 0:
        painter.setClipPath(_ellipse_path(rect))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(accent))
        if day == 15:
            painter.drawEllipse(rect)
        else:
            # Crescent is a symbolic illustration, consistent with the existing phase labels.
            painter.drawEllipse(rect)
            painter.setBrush(QColor('#201922'))
            shift = rect.width() * (day / 15 if day < 15 else (day - 30) / 15)
            painter.drawEllipse(rect.translated(shift, 0))
    painter.restore()


def _ellipse_path(rect):
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.addEllipse(rect)
    return path


class LunarBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(76)
        self.day, self.month = 0, 0
        self.setStyleSheet('background: transparent;')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = MONTH_MOTIFS[self.month][1]
        gradient = QRadialGradient(self.width() * .5, 40, self.width() * .7)
        gradient.setColorAt(0, QColor('#30212b'))
        gradient.setColorAt(1, QColor('#100e15'))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gradient)
        p.drawRoundedRect(QRectF(self.rect()), 14, 14)
        for index, day in enumerate((0, 4, 8, 12, 15, 19, 22, 26, 29)):
            x = 22 + index * (self.width() - 80) / 8
            paint_moon(p, QRectF(x, 18, 34, 34), day, accent if abs(day - self.day) < 3 else '#715951')
        p.end()


class DayButton(QPushButton):
    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        paint_moon(p, QRectF(self.width() - 25, 9, 14, 14),
                   self.property('moonDay') or 0, self.property('moonAccent') or '#9a7869')
        p.end()
