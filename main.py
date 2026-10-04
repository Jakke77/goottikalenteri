#!/usr/bin/env python3
"""Launch with python3 main.py [--data-file /path/to/events.json]."""
import argparse
import os
import sys
from pathlib import Path
from PyQt6.QtCore import QLockFile, QStandardPaths
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication, QMessageBox
from storage import EventStore
from ui import CalendarWindow, STYLE


def main():
    parser = argparse.ArgumentParser(description='Goottikalenteri: fictional 13 × 30 calendar')
    parser.add_argument('--data-file', type=Path, help='Override the local events.json path')
    parser.add_argument('--widget-only', action='store_true',
                        help='Show only the transparent desktop clock')
    parser.add_argument('--self-test', action='store_true',
                        help='Run an isolated offscreen packaging smoke test')
    args = parser.parse_args()
    if args.self_test:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication([sys.argv[0]])
    app.setApplicationName('Goottikalenteri')
    app.setOrganizationName('Goottikalenteri')
    app.setDesktopFileName('goottikalenteri')
    app.setStyle('Fusion')
    palette = QPalette()
    for role, color in [(QPalette.ColorRole.Window, '#090b10'),
                        (QPalette.ColorRole.WindowText, '#dbe6ef'),
                        (QPalette.ColorRole.Base, '#111721'),
                        (QPalette.ColorRole.AlternateBase, '#141a24'),
                        (QPalette.ColorRole.Text, '#dbe6ef'),
                        (QPalette.ColorRole.Button, '#141a24'),
                        (QPalette.ColorRole.ButtonText, '#dbe6ef'),
                        (QPalette.ColorRole.Highlight, '#14577a'),
                        (QPalette.ColorRole.HighlightedText, '#ffffff')]:
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setFont(QFont('DejaVu Sans', 10))
    app.setStyleSheet(STYLE)
    if args.self_test:
        from self_test import run
        return run(app)
    path = args.data_file or Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'events.json'
    path = path.expanduser().resolve()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(path) + '.lock')
        if not lock.tryLock(0):
            raise OSError('Tiedosto on käytössä toisessa ikkunassa tai sen lukitseminen epäonnistui.')
        store = EventStore(path)
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, 'Tietojen avaaminen epäonnistui',
                             f'{path}\n\n{error}\n\nAlkuperäistä tiedostoa ei muutettu.')
        return 1
    window = CalendarWindow(store)
    window.widget_only = args.widget_only
    if args.widget_only:
        app.setQuitOnLastWindowClosed(False)
        window.set_widget_enabled(True)
    else:
        window.show()
    try:
        return app.exec()
    finally:
        lock.unlock()

if __name__ == '__main__':
    sys.exit(main())
