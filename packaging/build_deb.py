#!/usr/bin/env python3
"""Build a Varjoaika Ubuntu .deb without root privileges."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.6.0'
FILES = ('main.py','calendar_model.py','storage.py','instance.py','time_service.py',
         'weather.py','ui.py','widget.py','reminders.py','reminder_ui.py','sound.py',
         'startup.py','theme.py','install.py','self_test.py')


def build(output, version=VERSION):
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+~:-]{0,100}', version):
        raise ValueError('Virheellinen pakettiversio')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        stage = Path(directory)
        app = stage / 'usr/share/varjoaika'
        app.mkdir(parents=True)
        for name in FILES:
            shutil.copyfile(ROOT / name, app / name)
        shutil.copytree(ROOT / 'assets', app / 'assets', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copyfile(ROOT / 'packaging/goottikalenteri.svg', app / 'assets/icon.svg')
        for path in app.rglob('*'):
            if path.is_file(): path.chmod(0o644)
        docs = stage / 'usr/share/doc/varjoaika'
        docs.mkdir(parents=True)
        for name in ('LICENSE','THIRD_PARTY_NOTICES.md','README.md'):
            shutil.copyfile(ROOT / name, docs / name)
        shutil.copyfile(ROOT / 'docs/USER_INSTALL.md', docs / 'USER_INSTALL.md')
        binary = stage / 'usr/bin'
        binary.mkdir(parents=True)
        (binary / 'varjoaika').write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/share/varjoaika/main.py "$@"\n')
        (binary / 'varjoaika').chmod(0o755)
        desktop = stage / 'usr/share/applications'
        desktop.mkdir(parents=True)
        for name, title, mode in [('varjoaika.desktop','Varjoaika','--calendar'),
                                  ('varjoaika-widget.desktop','Varjoaika-widget','--widget-only')]:
            (desktop / name).write_text('[Desktop Entry]\nType=Application\nName=' + title +
                '\nExec=varjoaika ' + mode + '\nIcon=/usr/share/varjoaika/assets/icon.svg\n'
                'Terminal=false\nCategories=Office;Calendar;\nStartupNotify=true\n')
        control = stage / 'DEBIAN'
        control.mkdir()
        (control / 'control').write_text('Package: varjoaika\nVersion: ' + version + '\nArchitecture: all\n'
            'Maintainer: Jakke77 <Jakke77@users.noreply.github.com>\nSection: utils\nPriority: optional\n'
            'Depends: python3 (>= 3.10), python3-pyqt6 (>= 6.6), python3-pyqt6.qtmultimedia (>= 6.6)\n'
            'Recommends: libnotify-bin\nHomepage: https://github.com/Jakke77/goottikalenteri\n'
            'Description: Shadow Time calendar, reminders and desktop widget\n'
            ' Fictional 13-month calendar with persistent notes and timed reminders.\n'
            ' Shadow Copper desktop widget and configurable owl notification sound.\n')
        # Root install never edits user data or starts a GUI via a maintainer script.
        target = output / f'varjoaika_{version}_all.deb'
        subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(target)],check=True)
        return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT / 'dist')
    parser.add_argument('--version',default=VERSION)
    args = parser.parse_args()
    print(build(args.output,args.version))
