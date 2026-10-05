#!/usr/bin/env python3
"""Install user launchers; never uses sudo or changes calendar data."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def desktop_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def main():
    parser = argparse.ArgumentParser(description='Varjoajan käyttäjäkohtaiset käynnistimet')
    parser.add_argument('--python', type=Path, default=Path(sys.executable), help='Python with PyQt6 and QtMultimedia')
    args = parser.parse_args()
    runtime = args.python.expanduser().absolute()
    root = Path(__file__).resolve().parent
    result = subprocess.run([str(runtime), '-c', 'from PyQt6.QtWidgets import QApplication; from PyQt6.QtMultimedia import QMediaPlayer'], capture_output=True, text=True)
    if result.returncode:
        print('Valitulta Pythonilta puuttuu PyQt6 tai Qt Multimedia.\n'
              'Asenna python3-pyqt6 ja python3-pyqt6.qtmultimedia tai käytä PyQt6-virtuaaliympäristöä.\n'
              'Aja sitten install.py --python /polku/.venv/bin/python', file=sys.stderr)
        return 1
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    directory = data / 'applications'
    directory.mkdir(parents=True, exist_ok=True)
    command = desktop_quote(runtime) + ' ' + desktop_quote(root / 'main.py')
    for name, title, mode in [('varjoaika.desktop', 'Varjoaika', '--calendar'),
                              ('varjoaika-widget.desktop', 'Varjoaika-widget', '--widget-only')]:
        path = directory / name
        text = ('[Desktop Entry]\nType=Application\nName=' + title + '\nComment=Kalenteri ja huhuilun muistutukset\nExec=' + command + ' ' + mode +
                '\nIcon=' + str(root / 'packaging/goottikalenteri.svg') + '\nTerminal=false\nCategories=Office;Calendar;\n')
        if path.exists() and path.read_text() != text:
            import shutil
            backup = path.with_suffix('.desktop.bak')
            if backup.exists():
                from datetime import datetime
                backup = path.with_suffix('.desktop.' + datetime.now().strftime('%Y%m%d%H%M%S%f') + '.bak')
            shutil.copy2(path, backup)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(text, encoding='utf-8')
        temporary.replace(path)
        print('Käynnistin:', path)
    print('Pidä lähdekoodihakemisto ja valittu Python paikallaan. Asetukset ja muistiinpanot säilyvät.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
