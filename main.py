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
from instance import server_name, request_mode, start_server


def main():
    parser = argparse.ArgumentParser(description='Varjoaika: fictional 13 × 30 calendar')
    parser.add_argument('--data-file', type=Path, help='Override the local events.json path')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--widget-only', dest='launch_mode', action='store_const',
                       const='widget', help='Show only the transparent desktop clock')
    modes.add_argument('--calendar', dest='launch_mode', action='store_const',
                       const='calendar', help='Show the calendar window')
    parser.set_defaults(launch_mode=os.environ.get('GOOTTI_LAUNCH_MODE', 'calendar'))
    parser.add_argument('--self-test', action='store_true',
                        help='Run an isolated offscreen packaging smoke test')
    args = parser.parse_args()
    if args.self_test:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication([sys.argv[0]])
    # Keep storage/settings identity stable across the visible rebranding.
    app.setApplicationName('Goottikalenteri')
    app.setApplicationDisplayName('Varjoaika')
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
        result = run(app)
        print(f'Launcher mode: {args.launch_mode}')
        return result
    path = args.data_file or Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation)) / 'events.json'
    path = path.expanduser().resolve()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(path) + '.lock')
        if not lock.tryLock(0):
            if request_mode(server_name(path), args.launch_mode):
                return 0
            raise OSError('Tiedosto on käytössä toisessa ikkunassa tai sen lukitseminen epäonnistui.')
        store = EventStore(path)
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, 'Tietojen avaaminen epäonnistui',
                             f'{path}\n\n{error}\n\nAlkuperäistä tiedostoa ei muutettu.')
        return 1
    window = CalendarWindow(store, restore_widget=False)

    def show_mode(mode):
        if mode == 'widget':
            window.widget_only = True
            app.setQuitOnLastWindowClosed(False)
            window.set_widget_enabled(True, persist=False)
        else:
            window.showNormal()
            window.raise_()
            window.activateWindow()

    try:
        server = start_server(server_name(path), window, show_mode)
    except OSError as error:
        lock.unlock()
        QMessageBox.critical(None, 'Käynnistys epäonnistui', str(error))
        return 1
    show_mode(args.launch_mode)
    try:
        return app.exec()
    finally:
        window.time_service.shutdown()
        server.close()
        lock.unlock()

if __name__ == '__main__':
    sys.exit(main())
