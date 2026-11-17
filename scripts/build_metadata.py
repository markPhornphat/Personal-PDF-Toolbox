import base64
import json
import os
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def main():
    metadata = ROOT / "build" / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    parts = tuple(map(int, VERSION.split(".")))
    if len(parts) != 3 or not all(0 <= part <= 65535 for part in parts):
        raise ValueError("Use a stable version with three Windows-compatible numbers.")
    (metadata / "VERSION").write_text(VERSION, encoding="utf-8")
    number = (*parts, 0)
    (metadata / "win-version.txt").write_text(
        f"""VSVersionInfo(
    ffi=FixedFileInfo(filevers={number}, prodvers={number}, mask=0x3F,
        flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('FileDescription', 'PDF Toolbox'),
        StringStruct('FileVersion', '{VERSION}'),
        StringStruct('ProductName', 'PDF Toolbox'),
        StringStruct('ProductVersion', '{VERSION}')
    ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)""",
        encoding="utf-8",
    )
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copyfile(python_license, metadata / "license-python.txt")
    config_path = metadata / "update-config.json"
    key = os.environ.get("PDF_TOOLBOX_UPDATE_PUBLIC_KEY")
    if key:
        if len(base64.b64decode(key, validate=True)) != 32:
            raise ValueError("The Ed25519 public key must be 32 bytes.")
        repository = os.environ["PDF_TOOLBOX_RELEASE_REPOSITORY"]
        config = {
            "repository": repository,
            "source_repository": os.environ.get(
                "PDF_TOOLBOX_SOURCE_REPOSITORY", "markPhornphat/Personal-PDF-Toolbox"
            ),
            "private": os.environ.get("PDF_TOOLBOX_RELEASE_PRIVATE", "true") != "false",
            "require_authenticode": os.environ.get("PDF_TOOLBOX_REQUIRE_AUTHENTICODE") == "true",
            "public_key": key,
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
    else:
        config_path.unlink(missing_ok=True)
    print(VERSION)


if __name__ == "__main__":
    main()
