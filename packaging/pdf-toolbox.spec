from pathlib import Path

root = Path(SPECPATH).parent
metadata = root / "build" / "metadata"
runtime = root / ".venv" / "Lib" / "site-packages"

data = [
    (str(metadata / "VERSION"), "."),
    (str(root / "THIRD_PARTY_LICENSES.md"), "."),
    (str(root / "USER_GUIDE.md"), "."),
    (str(root / "USER_GUIDE_TH.md"), "."),
    (str(root / "resources" / "fonts"), "resources/fonts"),
    (str(root / "resources" / "paper-dog.png"), "resources"),
    (str(root / "resources" / "pdf-toolbox.ico"), "resources"),
]
if (metadata / "update-config.json").is_file():
    data.append((str(metadata / "update-config.json"), "."))
for name in ("pyside6_essentials", "shiboken6", "pypdf-", "pypdfium2", "pillow-", "cryptography",
             "cffi-", "pycparser-", "pywin32_ctypes", "pywin32-"):
    for package in runtime.glob(f"{name}*.dist-info"):
        for license_dir in package.glob("licenses"):
            data.append((str(license_dir), f"licenses/{package.name}"))
for folder in ("pypdfium2_raw", "pypdfium2"):
    data.extend((str(file), f"licenses/{folder}")
                for file in (runtime / folder).glob("*LICENSE*") if file.is_file())
if (metadata / "license-python.txt").is_file():
    data.append((str(metadata / "license-python.txt"), "licenses"))

analysis = Analysis(
    [str(root / "src" / "main.py")],
    pathex=[str(root / "src")],
    datas=data,
    hiddenimports=["win32ctypes.core.ctypes._authentication", "win32ctypes.core.cffi._authentication",
                   "pythoncom", "pywintypes", "win32com.client", "win32com.server", "win32file"],
)
# Qt imports the Windows system ICU API. A different ICU DLL can have the same
# name on the build machine's PATH while exposing versioned, incompatible symbols.
analysis.binaries = [
    entry for entry in analysis.binaries
    if Path(entry[0]).name.lower() not in {"icu.dll", "icuuc.dll", "icuin.dll"}
]
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, [], exclude_binaries=True, name="PDF Toolbox",
    console=False, upx=False, version=str(metadata / "win-version.txt"),
    icon=str(root / "resources" / "pdf-toolbox.ico"),
)
bundle = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False, name="PDF Toolbox")
