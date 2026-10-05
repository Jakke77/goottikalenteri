"""One user-session autostart entry for either or both views. No root access."""
import os
import json
from pathlib import Path
import sys


def autostart_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'autostart' / 'varjoaika-widget.desktop'


def startup_choices():
    path = autostart_path()
    if not path.exists():
        return False, False
    text = path.read_text(encoding='utf-8')
    if 'X-GNOME-Autostart-enabled=false' in text or 'Hidden=true' in text:
        return False, False
    if '--both' in text:
        return True, True
    if '--calendar' in text:
        return False, True
    return True, False


def desktop_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def startup_text(widget, calendar, command=None):
    if command is None:
        command = desktop_quote(sys.executable)
        if not getattr(sys, 'frozen', False):
            # Preserve a rootless installer's stable current symlink across updates.
            command += ' ' + desktop_quote(Path(__file__).absolute().with_name('main.py'))
        receipt = Path(__file__).absolute().with_name('user-install.json')
        if receipt.exists():
            launcher = json.loads(receipt.read_text())['launcher']
            command = desktop_quote(launcher)
        if os.environ.get('APPIMAGE'):
            command = desktop_quote(os.environ['APPIMAGE'])
    mode = '--both' if widget and calendar else ('--widget-only' if widget else '--calendar')
    marker = '# Varjoaika user installation\n' if Path(__file__).absolute().with_name('user-install.json').exists() else ''
    return ('[Desktop Entry]\n' + marker + 'Type=Application\nName=Varjoaika\nExec=' + command + ' ' + mode +
            '\nTerminal=false\nX-GNOME-Autostart-enabled=true\n')


def set_autostart(widget, calendar=False):
    path = autostart_path()
    if not widget and not calendar:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(startup_text(widget, calendar), encoding='utf-8')
    temporary.replace(path)
