"""Real non-root deb install, startup modes, upgrade, self-test and removal."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'packaging'))
sys.path.insert(0,str(ROOT))
from build_deb import build
from install_user import install, remove, MARKER
from startup import set_autostart, startup_choices, startup_text
assert os.geteuid() != 0
with tempfile.TemporaryDirectory(prefix='varjo deb test ') as tmp:
    root = Path(tmp)
    data,config,binary = root/'data',root/'config',root/'bin'
    kwargs = dict(data_dir=data,config_dir=config,bin_dir=binary)
    original = data/'applications/varjoaika.desktop'
    original.parent.mkdir(parents=True)
    original.write_text('Original launcher\n')
    package = build(root/'dist','0.6.0')
    with patch('install_user.dependency_check',side_effect=ValueError('Missing Qt')):
        try:install(package,python=sys.executable,**kwargs)
        except ValueError:pass
        else:raise AssertionError('Missing Qt accepted')
    assert original.read_text() == 'Original launcher\n'
    assert not (data/'varjoaika').exists()
    current = install(package,python=sys.executable,autostart_widget=True,autostart_calendar=True,**kwargs)
    assert current.is_symlink()
    assert (current/'assets/huuhkaja.wav').is_file()
    assert '--calendar' in original.read_text()
    assert '--widget-only' in (data/'applications/varjoaika-widget.desktop').read_text()
    assert '--both' in (config/'autostart/varjoaika-widget.desktop').read_text()
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen',XDG_DATA_HOME=str(data),XDG_CONFIG_HOME=str(config))
    subprocess.run([str(binary/'varjoaika'),'--self-test','--both'],env=env,check=True,timeout=20)
    old = current.resolve()
    next_package = build(root/'dist','0.6.1')
    install(next_package,python=sys.executable,**kwargs)
    assert current.resolve() != old and old.is_dir()
    assert '--both' in (config/'autostart/varjoaika-widget.desktop').read_text()
    with patch.dict(os.environ, {'XDG_CONFIG_HOME':str(config)}):
        assert startup_choices() == (True,True)
        set_autostart(False,True)
        assert startup_choices() == (False,True)
        set_autostart(True,False)
        assert startup_choices() == (True,False)
        set_autostart(False,False)
        assert startup_choices() == (False,False)
    # Simulate a settings save through the installed current symlink, then upgrade.
    code='from startup import set_autostart; set_autostart(True,True)'
    subprocess.run([sys.executable,'-c',code],cwd=current,env=env,check=True)
    text=(config/'autostart/varjoaika-widget.desktop').read_text()
    assert str(binary / 'varjoaika') in text and MARKER in text, text
    install(next_package,python=sys.executable,**kwargs)
    assert '--both' in (config/'autostart/varjoaika-widget.desktop').read_text()
    remove(**kwargs)
    assert not current.is_symlink()
    assert original.read_text() == 'Original launcher\n'
    assert not (data/'applications/varjoaika-widget.desktop').exists()
    assert not (config/'autostart/varjoaika-widget.desktop').exists()
    assert old.is_dir()
print('Deb/rootless OK: real extraction, dependencies, launchers, startup modes, upgrade, installed GUI, preserved backups and uninstall')
