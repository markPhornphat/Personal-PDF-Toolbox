import base64
import hashlib
import json
import os
import sys
import tomllib
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
ASSET = "PDF-Toolbox-Setup-x64.exe"


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    folder = Path(sys.argv[1]).resolve()
    setup = folder / ASSET
    artifact = json.loads((folder / "release-build.json").read_text(encoding="utf-8"))
    config = artifact["config"]
    if (
        artifact["version"] != version
        or config["repository"] != os.environ["PDF_TOOLBOX_RELEASE_REPOSITORY"]
    ):
        raise ValueError("Build metadata does not match the release version or repository.")
    if config["require_authenticode"]:
        sys.path.insert(0, str(ROOT / "src"))
        from pdf_toolbox.updater import verify_authenticode

        verify_authenticode(setup)
    private = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(os.environ["PDF_TOOLBOX_SIGNING_KEY"], validate=True)
    )
    if private.public_key().public_bytes_raw() != base64.b64decode(
        config["public_key"], validate=True
    ):
        raise ValueError(
            "The signing key does not match the verification key embedded in the build."
        )
    with setup.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    data = {
        "schema_version": 1,
        "app_id": "pdf-toolbox",
        "repository": config["repository"],
        "version": version,
        "tag": f"v{version}",
        "platform": "win32",
        "architecture": "x64",
        "installer_filename": ASSET,
        "installer_size": setup.stat().st_size,
        "sha256": digest,
        "release_date": date.today().isoformat(),
        "minimum_windows_build": 17763,
    }
    encoded = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()
    (folder / "update-manifest.json").write_bytes(encoded)
    (folder / "update-manifest.sig").write_bytes(private.sign(encoded))
    (folder / "SHA256SUMS.txt").write_text(f"{digest}  {ASSET}\n", encoding="ascii")


if __name__ == "__main__":
    main()
