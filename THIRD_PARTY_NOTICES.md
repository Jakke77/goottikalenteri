# Distribution licensing

Goottikalenteri's original Python source, build scripts and original SVG icon are
Copyright (c) 2026 Jakke77 and licensed under MIT (see LICENSE).

The AppImage includes independently licensed third-party components. MIT does not
replace those licenses. The GPL edition of PyQt6 is used; distribution of the combined
application must comply with GPLv3. Recipients retain MIT rights to the original
Goottikalenteri source. This is not a proprietary or MIT-only binary distribution.
The source of Goottikalenteri and its build instructions is provided in this repository
and in the release source ZIP. The AppImage also includes that source ZIP.

Main components:

| Component | Version in this build | License | Source |
| --- | --- | --- | --- |
| PyQt6 | 6.11.0 | GPLv3 | https://pypi.org/project/PyQt6/6.11.0/#files |
| Qt | 6.11.2 | LGPLv3 / GPLv3, with third-party notices | https://download.qt.io/archive/qt/6.11/6.11.2/submodules/ |
| PyQt6-sip | 13.13.0 | BSD-2-Clause | https://pypi.org/project/PyQt6-sip/13.13.0/#files |
| CPython | See build-info.json (Python 3.12) | PSF license | https://www.python.org/downloads/release/python-31214/ |
| PyInstaller bootloader | 6.22.3 | GPLv2-or-later with bootloader exception | https://github.com/pyinstaller/pyinstaller/tree/v6.22.3 |
| AppImage runtime | SHA-256 156f4bdbde9c52d01814600013e0a273f0118dc2de98975f3c8c63427ec79074 | MIT | https://github.com/AppImage/type2-runtime |

PyInstaller also collects supporting system shared libraries. Their package names,
versions and source-package names are recorded in `system-libraries.json`; installed
Ubuntu copyright/license notices are copied into `licenses/system/` inside the AppImage.
The release `build-info.json` identifies the interpreter, Qt and packaging tool versions
and the binary's maximum required GLIBC symbol version. System-library corresponding
sources are available from the indicated Ubuntu source packages at https://archive.ubuntu.com/ubuntu/pool/
(and https://launchpad.net/ubuntu/+source/). Preserve all third-party notices when
redistributing. The Qt libraries are dynamically loaded and remain replaceable in an
extracted AppImage/AppDir.

The binary has been smoke-tested offscreen. Actual GNOME/Wayland behavior and a
clean Ubuntu 26.04/26.10 installation still need platform testing.
