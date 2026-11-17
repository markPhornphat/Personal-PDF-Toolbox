import hashlib
import io
import json
from threading import Event

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pdf_toolbox.pdf import Cancelled
from pdf_toolbox.updater import ASSET, MANIFEST, SIGNATURE, Config, GitHub, UpdateError


@pytest.mark.parametrize("variant", ["good", "interrupted", "wrong_hash", "cancelled", "draft"])
def test_signed_update_check_and_download(tmp_path, monkeypatch, variant):
    key = Ed25519PrivateKey.generate()
    config = Config("owner/repo", key.public_key().public_bytes_raw(), False)
    content = b"simulated test installer"
    metadata = {
        "schema_version": 1,
        "app_id": "pdf-toolbox",
        "version": "1.0.1",
        "tag": "v1.0.1",
        "repository": config.repository,
        "platform": "win32",
        "architecture": "x64",
        "installer_filename": ASSET,
        "installer_size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "release_date": "2026-11-17",
    }
    manifest = json.dumps(metadata).encode()
    release_json = json.dumps(
        {
            "tag_name": "v1.0.1",
            "draft": variant == "draft",
            "prerelease": False,
            "body": "<img src='https://example.com/untrusted'>",
            "assets": [
                {"name": name, "id": identifier, "state": "uploaded", "size": size}
                for identifier, name, size in [
                    (1, MANIFEST, len(manifest)),
                    (2, SIGNATURE, 64),
                    (3, ASSET, len(content)),
                ]
            ],
        }
    ).encode()
    installer = content if variant != "wrong_hash" else b"Z" * len(content)

    class Interrupted(io.BytesIO):
        def read(self, _):
            raise ConnectionError("simulated connection interruption")

    client = GitHub(config)
    monkeypatch.setattr(
        client,
        "request",
        lambda path, _: {
            "latest": io.BytesIO(release_json),
            "assets/1": io.BytesIO(manifest),
            "assets/2": io.BytesIO(key.sign(manifest)),
            "assets/3": Interrupted(installer)
            if variant == "interrupted"
            else io.BytesIO(installer),
        }[path],
    )
    release = client.check("1.0.0")
    if variant == "draft":
        assert release is None
        return
    assert release.manifest.version == "1.0.1"
    assert release.notes.startswith("<img")
    cancelled = Event()
    if variant == "cancelled":
        cancelled.set()
    expected = {"cancelled": Cancelled, "wrong_hash": UpdateError, "interrupted": ConnectionError}
    if variant in expected:
        with pytest.raises(expected[variant]):
            client.download(release, tmp_path, cancelled, lambda *_: None)
        assert list(tmp_path.iterdir()) == []
    else:
        progress = []
        downloaded = client.download(
            release, tmp_path, cancelled, lambda *data: progress.append(data)
        )
        assert downloaded.read_bytes() == content
        assert progress[-1] == (len(content), len(content))
