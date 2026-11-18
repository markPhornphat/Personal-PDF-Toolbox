# Third-party licenses

PDF Toolbox uses the following runtime dependencies. The packaged application includes available notices from the installed wheels under `_internal/licenses`. The exact resolved versions and distribution hashes are in `uv.lock`.

| Component | License or notice | Upstream |
| --- | --- | --- |
| CPython | PSF license and bundled notices | [Python license](https://docs.python.org/3/license.html) |
| PySide6 Essentials, Shiboken and Qt | LGPL-3.0 or GPL options. Native Qt libraries are bundled dynamically. | [Qt licensing](https://doc.qt.io/qtforpython-6/commercial/index.html) |
| pypdf | BSD-3-Clause | [pypdf](https://pypi.org/project/pypdf/) |
| pypdfium2 / PDFium | Apache-2.0 or BSD-3-Clause for bindings. PDFium and nested dependencies have their own bundled notices. | [pypdfium2](https://pypi.org/project/pypdfium2/) |
| Pillow | MIT-CMU and bundled dependency notices | [Pillow](https://pypi.org/project/Pillow/) |
| cryptography | Apache-2.0 or BSD-3-Clause, with OpenSSL notices | [cryptography](https://pypi.org/project/cryptography/) |
| cffi / pycparser | MIT / BSD-3-Clause | [cffi](https://pypi.org/project/cffi/) and [pycparser](https://pypi.org/project/pycparser/) |
| pywin32-ctypes | BSD-3-Clause | [pywin32-ctypes](https://pypi.org/project/pywin32-ctypes/) |
| pywin32 | Installed win32, win32com and Pythonwin copyright/license notices are bundled under `licenses/pywin32`. Distribution metadata identifies PSF licensing; consult the included component notices. | [pywin32](https://github.com/mhammond/pywin32) |
| PyInstaller bootloader | GPL with bootloader exception | [PyInstaller license](https://pyinstaller.org/en/stable/license.html) |
| Inno Setup | Inno Setup license | [Inno Setup license](https://jrsoftware.org/files/is/license.txt) |
| Noto Sans Thai | SIL Open Font License 1.1. Font and license are bundled together. | [Font source](https://github.com/google/fonts/tree/main/ofl/notosansthai) |
| Nunito | SIL Open Font License 1.1. Font and license are bundled together. | [Font source](https://github.com/google/fonts/tree/main/ofl/nunito) |

Obtain the corresponding dynamically linked Qt and bindings source from Qt's [official download archive](https://download.qt.io/official_releases/qt/6.10/6.10.2/) and [Qt for Python source repository](https://code.qt.io/cgit/pyside/pyside-setup.git/). Qt libraries can be replaced in the one-directory installation subject to ABI compatibility. Use this license inventory and the bundled notices when preparing distribution.
