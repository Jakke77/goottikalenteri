#!/usr/bin/env python3
"""Install this .deb's application payload into the user's home; never run dpkg -i."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

APP = 'varjoaika'
PAYLOAD = ('usr', 'share', APP)
DOCS = ('usr', 'share', 'doc', APP)
MARKER = '# Varjoaika user installation\n'
REQUIRED = ('main.py', 'calendar_model.py', 'widget.py', 'reminders.py', 'startup.py', 'sound.py', 'assets/huuhkaja.wav', 'assets/icon.svg')


def atomic(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(text)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def locations(data_dir=None, config_dir=None, bin_dir=None):
    home = Path.home()
    data = data_dir or Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share')))
    config = config_dir or Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config')))
    binary = bin_dir or home / '.local/bin'
    return tuple(Path(p).absolute() for p in (data, config, binary))


def dependency_check(python):
    # Test actual shared-library imports too, not just whether packages are listed.
    probe = ('import sys; assert sys.version_info >= (3, 10); from PyQt6.QtCore import QT_VERSION_STR; '
             'from PyQt6 import QtWidgets, QtNetwork, QtMultimedia; '
             'assert tuple(map(int, QT_VERSION_STR.split(".")[:2])) >= (6, 6)')
    try:
        subprocess.run([str(python), '-c', probe], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, timeout=20)
    except (OSError, subprocess.SubprocessError):
        raise ValueError('Qt-riippuvuudet puuttuvat tai eivät lataudu. Asenna tarvittaessa kerran:\n'
                         'sudo apt install python3-pyqt6 python3-pyqt6.qtmultimedia\n'
                         'Tai valitse toimiva virtuaaliympäristö: --python /polku/venv/bin/python') from None


def metadata(package):
    values = {}
    for field in ('Package', 'Version', 'Architecture'):
        values[field] = subprocess.check_output(['dpkg-deb', '--field', str(package), field],
                                               text=True, timeout=15).strip()
    if values['Package'] != APP or values['Architecture'] != 'all':
        raise ValueError('Valitse Varjoaikan architecture all -paketti')
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+~:-]{0,100}', values['Version']):
        raise ValueError('Virheellinen pakettiversio')
    if package.stat().st_size > 25_000_000:
        raise ValueError('Paketti on liian suuri')
    return values['Version'], hashlib.sha256(package.read_bytes()).hexdigest()


def extract_payload(package, directory):
    process = subprocess.Popen(['dpkg-deb', '--fsys-tarfile', str(package)],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    count = total = 0
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for member in archive:
                count += 1
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isdir() or member.isfile()):
                    raise ValueError('Paketti sisältää turvattoman polun tai linkin')
                if count > 500 or member.size < 0:
                    raise ValueError('Paketti sisältää liikaa tiedostoja')
                total += member.size
                if total > 25_000_000:
                    raise ValueError('Purettu paketti on liian suuri')
                parts = path.parts
                if parts[:3] == PAYLOAD:
                    relative = parts[3:]
                elif parts[:4] == DOCS:
                    relative = ('docs',) + parts[4:]
                else:
                    continue
                target = directory.joinpath(*relative)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(0o644)
        process.stdout.close()
        if process.wait(timeout=15):
            raise ValueError('Deb-paketin purku epäonnistui')
        if not all((directory / name).is_file() for name in REQUIRED):
            raise ValueError('Paketista puuttuu sovelluksen tiedostoja')
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.kill()
        process.wait()


def desktop_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def launcher_files(current, binary):
    command = binary / APP
    script = '#!/bin/sh\n' + MARKER + 'exec ' + shlex.quote(str(command.parent / (APP + '-python'))) + ' ' + shlex.quote(str(current / 'main.py')) + ' "$@"\n'
    desktop = ('[Desktop Entry]\n' + MARKER + 'Type=Application\nName=Varjoaika\n'
               'Comment=Kalenteri ja muistutukset\nExec=' + desktop_quote(command) + ' --calendar\n'
               'Path=' + str(current) + '\nIcon=' + str(current / 'assets/icon.svg') + '\n'
               'Terminal=false\nCategories=Utility;\nStartupNotify=false\n')
    widget_desktop = desktop.replace('Name=Varjoaika\n', 'Name=Varjoaika-widget\n').replace(' --calendar\n', ' --widget-only\n')
    return command, script, desktop, widget_desktop


def install(package, *, python=None, autostart_widget=False, autostart_calendar=False, data_dir=None, config_dir=None, bin_dir=None):
    if os.geteuid() == 0:
        raise ValueError('Aja käyttäjäasennus tavallisena käyttäjänä ilman sudoa')
    # Keep the venv's path; resolving its symlink would lose its installed dependencies.
    python = Path(python or sys.executable).absolute()
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError('Python-tulkkia ei löydy')
    dependency_check(python)
    package = Path(package).resolve(strict=True)
    version, digest = metadata(package)
    data, config, binary = locations(data_dir, config_dir, bin_dir)
    base = data / APP
    releases = base / 'releases'
    releases.mkdir(parents=True, exist_ok=True)
    with (base / 'install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = base / 'current'
        if current.is_symlink():
            if current.resolve().parent != releases.resolve():
                raise ValueError('current-linkki ei kuulu tämän asentimen julkaisuihin')
        elif current.exists():
            raise ValueError('Kohteessa on jo muu current-hakemisto; mitään ei korvattu')
        target = releases / (version + '-' + digest[:16])
        with tempfile.TemporaryDirectory(prefix='.unpack-', dir=releases) as tmp:
            stage = Path(tmp) / 'app'
            stage.mkdir()
            extract_payload(package, stage)
            atomic(stage / 'user-install.json', json.dumps(dict(
                version=version, sha256=digest, launcher=str(binary / APP))) + '\n')
            if target.exists():
                try:
                    previous = json.loads((target / 'user-install.json').read_text())
                except (OSError, ValueError):
                    raise ValueError('Kohteessa on jo asentimelle tuntematon julkaisu') from None
                if previous.get('sha256') != digest or not all((target / name).is_file() for name in REQUIRED):
                    raise ValueError('Aiempi julkaisu on vaurioitunut; mitään ei korvattu')
            else:
                os.replace(stage, target)
        command, script, desktop, widget_desktop = launcher_files(current, binary)
        autostart_path = config / 'autostart' / (APP + '-widget.desktop')
        paths = {command: (script, 0o755),
                 command.with_name(APP + '-python'): ('#!/bin/sh\n' + MARKER + 'exec ' + shlex.quote(str(python)) + ' "$@"\n', 0o755),
                 data / 'applications' / (APP + '.desktop'): (desktop, 0o644),
                 data / 'applications' / (APP + '-widget.desktop'): (widget_desktop, 0o644)}
        previous_startup = autostart_path.read_text() if autostart_path.is_file() else ''
        active_startup = previous_startup and 'Hidden=true' not in previous_startup and 'X-GNOME-Autostart-enabled=false' not in previous_startup
        widget_start = autostart_widget or (active_startup and ('--both' in previous_startup or '--calendar' not in previous_startup))
        calendar_start = autostart_calendar or (active_startup and ('--both' in previous_startup or '--calendar' in previous_startup))
        if widget_start or calendar_start:
            mode = '--both' if widget_start and calendar_start else ('--widget-only' if widget_start else '--calendar')
            startup = desktop.replace(' --calendar\n', ' ' + mode + '\n')
            paths[autostart_path] = (startup, 0o644)
        # Back up pre-existing launchers once; every version uses the stable current link.
        receipt_path = base / 'installation.json'
        try:
            old = json.loads(receipt_path.read_text())
        except (OSError, ValueError):
            old = {}
        backups = old.get('backups', {})
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        for path, (content, mode) in paths.items():
            if path.exists() and MARKER.encode() not in path.read_bytes():
                tag = hashlib.sha256(str(path).encode()).hexdigest()[:12]
                backup = base / 'backups' / (path.name + '-' + tag + '-' + stamp)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
                backups[str(path)] = str(backup)
            atomic(path, content, mode)
        next_link = base / ('.current-' + stamp)
        try:
            next_link.symlink_to(target.relative_to(base), target_is_directory=True)
            os.replace(next_link, current)
        finally:
            next_link.unlink(missing_ok=True)
        receipt = dict(version=version, sha256=digest, python=str(python), backups=backups,
                       files=[str(path) for path in paths])
        atomic(receipt_path, json.dumps(receipt, indent=2) + '\n')
        return current


def remove(*, data_dir=None, config_dir=None, bin_dir=None):
    if os.geteuid() == 0:
        raise ValueError('Aja poisto tavallisena käyttäjänä ilman sudoa')
    data, config, binary = locations(data_dir, config_dir, bin_dir)
    base = data / APP
    try:
        receipt = json.loads((base / 'installation.json').read_text())
    except (OSError, ValueError):
        raise ValueError('Käyttäjäasennusta ei löydy') from None
    allowed = {binary / APP, binary / (APP + '-python'),
               data / 'applications' / (APP + '.desktop'), data / 'applications' / (APP + '-widget.desktop'), config / 'autostart' / (APP + '-widget.desktop')}
    for path in allowed:
        if not path.is_file() or MARKER.encode() not in path.read_bytes():
            continue
        backup = receipt.get('backups', {}).get(str(path))
        if backup and Path(backup).is_file() and Path(backup).resolve().parent == (base / 'backups').resolve():
            shutil.copy2(backup, path)
        else:
            path.unlink()
    current = base / 'current'
    if current.is_symlink() and current.resolve().parent == (base / 'releases').resolve():
        current.unlink()
    # Keep old releases/backups for recovery; calendar data and settings are untouched.
    atomic(base / 'installation.json', json.dumps(dict(receipt, removed=True), indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description='Asenna kalenteri deb-paketista omalle käyttäjälle ilman sudoa')
    parser.add_argument('package', nargs='?', type=Path)
    parser.add_argument('--python', type=Path, help='Qt-riippuvuudet sisältävä Python-tulkki')
    parser.add_argument('--autostart-widget', action='store_true', help='Avaa widget kirjautuessa')
    parser.add_argument('--autostart-calendar', action='store_true', help='Avaa kalenteri kirjautuessa')
    parser.add_argument('--remove', action='store_true', help='Poista käyttäjäkäynnistimet, säilytä asetukset')
    args = parser.parse_args()
    try:
        if args.remove:
            remove()
            print('Käyttäjäasennuksen käynnistimet poistettu. Asetukset ja varmuuskopiot säilyvät.')
        elif args.package:
            current = install(args.package, python=args.python, autostart_widget=args.autostart_widget, autostart_calendar=args.autostart_calendar)
            print('Käyttäjäasennus valmis: ' + str(current))
            print('Avaa Varjoaika sovellusvalikosta. Päivityksen jälkeen sulje ja avaa widget uudelleen.')
        else:
            parser.error('Anna .deb-paketti tai --remove')
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
        parser.exit(1, str(exc) + '\n')

if __name__ == '__main__':
    main()
