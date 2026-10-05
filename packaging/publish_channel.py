#!/usr/bin/env python3
"""Prepare the public package download branch after successful checks."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]

def publish(package, directory):
    package, directory = Path(package), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output(['dpkg-deb','--field',str(package),'Version'],text=True).strip()
    filename = f'varjoaika_{version}_all.deb'
    shutil.copyfile(package, directory / filename)
    shutil.copyfile(ROOT / 'packaging/install_user.py', directory / 'install-user.py')
    shutil.copyfile(ROOT / 'docs/USER_INSTALL.md', directory / 'USER_INSTALL.md')
    (directory / 'channel.json').write_text(json.dumps(dict(package='varjoaika',version=version,
        filename=filename,size=package.stat().st_size,sha256=hashlib.sha256(package.read_bytes()).hexdigest()),indent=2)+'\n')

if __name__ == '__main__': publish(sys.argv[1],sys.argv[2])
