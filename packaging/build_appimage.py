#!/usr/bin/env python3
"""Build a self-contained x86_64 AppImage with checked official tooling.

Use Python with requirements-build.txt installed. Requires curl-free HTTPS access,
readelf, mksquashfs and an x86_64 Linux host. Build on Ubuntu 26.04 for that baseline.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOL_URL = 'https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage'
TOOL_SHA = 'ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0'
RUNTIME_URL = 'https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64'
RUNTIME_SHA = '156f4bdbde9c52d01814600013e0a273f0118dc2de98975f3c8c63427ec79074'

def run(arguments, **kwargs):
    subprocess.run([str(value) for value in arguments], check=True, **kwargs)

def fetch(url, destination, checksum):
    if not destination.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'Goottikalenteri-build'})
        with urllib.request.urlopen(request, timeout=120) as response, destination.open('wb') as target:
            shutil.copyfileobj(response, target)
    actual = hashlib.sha256(destination.read_bytes()).hexdigest()
    if actual != checksum:
        raise RuntimeError(f'Checksum mismatch for {destination}; upstream continuous assets may have changed. '
                           'Review and update the pinned URL/hash together before rebuilding.')
    destination.chmod(0o755)

def source_zip(destination):
    files = ['.gitignore', 'LICENSE', 'README.md', 'THIRD_PARTY_NOTICES.md',
             'requirements.txt', 'requirements-build.txt', 'calendar_model.py',
             'main.py', 'instance.py', 'time_service.py', 'storage.py', 'ui.py', 'widget.py', 'self_test.py',
             'goottikalenteri.desktop', 'goottikalenteri-widget.desktop']
    files += [str(path.relative_to(ROOT)) for directory in ('tests', 'packaging', 'previews', '.github')
              for path in (ROOT / directory).rglob('*')
              if path.is_file() and '__pycache__' not in path.parts]
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            archive.write(ROOT / name, Path('goottikalenteri') / name)

def system_notices(bundle, docs):
    records = {}
    maximum = (0, 0)
    for binary in bundle.rglob('*'):
        if not binary.is_file() or binary.is_symlink():
            continue
        with binary.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        versions = subprocess.run(['readelf', '--version-info', str(binary)],
                                  capture_output=True, text=True, check=True).stdout
        for number in re.findall(r'Name: GLIBC_(\d+\.\d+)', versions):
            maximum = max(maximum, tuple(map(int, number.split('.'))))
        original = Path('/usr/lib/x86_64-linux-gnu') / binary.name
        if not original.exists():
            continue
        query = subprocess.run(['dpkg-query', '-S', str(original)], capture_output=True, text=True)
        if query.returncode:
            continue
        package = query.stdout.split(': /')[0].strip()
        if package in records:
            continue
        metadata = subprocess.run(['dpkg-query', '-W', '-f=${Package}\t${Version}\t${source:Package}\t${source:Version}',
                                   package], capture_output=True, text=True, check=True).stdout.split('\t')
        records[package] = metadata
        copyright_file = Path('/usr/share/doc') / package.split(':')[0] / 'copyright'
        if copyright_file.exists():
            destination = docs / 'licenses' / 'system' / package.replace(':', '_')
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(copyright_file, destination / 'copyright')
    (docs / 'system-libraries.json').write_text(json.dumps(records, indent=2) + '\n')
    return '.'.join(map(str, maximum))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', default='0.2.3')
    parser.add_argument('--variant', choices=('calendar', 'widget', 'both'), default='both')
    parser.add_argument('--skip-freeze', action='store_true', help='Reuse an existing frozen bundle')
    parser.add_argument('--frozen-dir', type=Path)
    parser.add_argument('--tool-file', type=Path)
    parser.add_argument('--runtime-file', type=Path)
    args = parser.parse_args()
    if platform.machine() != 'x86_64':
        raise RuntimeError('This build targets x86_64 only.')
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?', args.version):
        raise ValueError('Expected a semantic version, e.g. 0.1.0.')
    output = ROOT / 'release-assets'
    work = ROOT / 'build' / 'appimage'
    output.mkdir(exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    bundle = args.frozen_dir or ROOT / 'dist' / 'goottikalenteri'
    if not args.skip_freeze:
        run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
             '--name', 'goottikalenteri', '--distpath', bundle.parent, '--workpath', work / 'freeze',
             '--specpath', work, '--copy-metadata', 'PyQt6', '--copy-metadata', 'PyQt6-Qt6',
             '--copy-metadata', 'PyQt6-sip', ROOT / 'main.py'], cwd=ROOT)
    appdir = work / 'Goottikalenteri.AppDir'
    if appdir.exists():
        shutil.rmtree(appdir)
    appdir.mkdir()
    shutil.copytree(bundle, appdir / 'usr' / 'bin', symlinks=True)

    for name in ('goottikalenteri.desktop', 'goottikalenteri.svg'):
        shutil.copyfile(ROOT / 'packaging' / name, appdir / name)
    (appdir / '.DirIcon').symlink_to('goottikalenteri.svg')
    docs = appdir / 'usr' / 'share' / 'doc' / 'goottikalenteri'
    docs.mkdir(parents=True)
    shutil.copytree(ROOT / 'packaging' / 'licenses', docs / 'licenses' / 'bundled-runtime')
    for name in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        shutil.copyfile(ROOT / name, docs / name)
    for distribution in ('PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'PyInstaller'):
        metadata = importlib.metadata.distribution(distribution)
        for item in metadata.files or []:
            if 'license' in str(item).lower() or Path(item).name.upper() in ('COPYING', 'COPYRIGHT'):
                source = Path(metadata.locate_file(item))
                if source.is_file():
                    destination = docs / 'licenses' / distribution / Path(item).name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
    info = {'version': args.version, 'architecture': 'x86_64', 'python': platform.python_version(),
            'packages': {name: importlib.metadata.version(name) for name in
                         ('PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'PyInstaller')},
            'minimum_glibc_symbols': system_notices(appdir, docs),
            'appimagetool_sha256': TOOL_SHA, 'runtime_sha256': RUNTIME_SHA}
    info_path = output / 'build-info.json'
    info_path.write_text(json.dumps(info, indent=2) + '\n')
    shutil.copyfile(info_path, docs / 'build-info.json')
    sources = output / f'Goottikalenteri-{args.version}-source.zip'
    source_zip(sources)
    shutil.copyfile(sources, docs / sources.name)
    tool = args.tool_file or work / 'appimagetool.AppImage'
    runtime = args.runtime_file or work / 'runtime-x86_64'
    fetch(TOOL_URL, tool, TOOL_SHA)
    fetch(RUNTIME_URL, runtime, RUNTIME_SHA)
    extracted = work / 'tool'
    extracted.mkdir(exist_ok=True)
    run([tool.resolve(), '--appimage-extract'], cwd=extracted)
    images = []
    variants = ('calendar', 'widget') if args.variant == 'both' else (args.variant,)
    for variant in variants:
        launcher = appdir / 'AppRun'
        launcher.write_text('#!/bin/sh\n'
                            f'export GOOTTI_LAUNCH_MODE={variant}\n'
                            'app_dir=${APPDIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}\n'
                            'exec "$app_dir/usr/bin/goottikalenteri" "$@"\n')
        launcher.chmod(0o755)
        desktop = (ROOT / 'packaging' / 'goottikalenteri.desktop').read_text()
        if variant == 'widget':
            desktop = desktop.replace('Name=Goottikalenteri', 'Name=Goottikalenteri-widget')
            desktop = desktop.replace('Exec=goottikalenteri', 'Exec=goottikalenteri --widget-only')
        (appdir / 'goottikalenteri.desktop').write_text(desktop)
        name = 'Goottikalenteri' if variant == 'calendar' else 'Goottikalenteri-widget'
        image = output / f'{name}-{args.version}-x86_64.AppImage'
        env = dict(os.environ, ARCH='x86_64', VERSION=args.version)
        run([extracted / 'squashfs-root' / 'AppRun', '--runtime-file', runtime.resolve(),
             '--no-appstream', '--mksquashfs-opt', '-processors', '--mksquashfs-opt', '2',
             appdir, image], env=env)
        image.chmod(0o755)
        checked = subprocess.run([str(image), '--appimage-extract-and-run', '--self-test'],
                                 env=dict(os.environ, QT_QPA_PLATFORM='offscreen'),
                                 capture_output=True, text=True, check=True)
        print(checked.stdout, end='')
        print(checked.stderr, end='', file=sys.stderr)
        if f'Launcher mode: {variant}' not in checked.stdout:
            raise RuntimeError(f'Wrong launch mode in {image.name}')
        images.append(image)
    assets = images + [sources, info_path]
    (output / 'SHA256SUMS').write_text(''.join(
        f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in assets))
    print('AppImages built and tested: ' + ', '.join(map(str, images)))

if __name__ == '__main__':
    main()
