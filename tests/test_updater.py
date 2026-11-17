import hashlib
import json
from urllib.error import HTTPError

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pdf_toolbox.updater import (
    ASSET,
    Config,
    GitHub,
    Redirects,
    UpdateError,
    verify_manifest,
    verify_file,
)


def test_public_repo_without_releases_reports_no_public_release(monkeypatch):
    client = GitHub(Config("owner/repo", bytes(32), private=False))

    def latest_not_found(request, *, timeout):
        assert request.full_url.endswith("/releases/latest")
        assert request.get_header("Authorization") is None
        raise HTTPError(request.full_url, 404, "Not found", {}, None)

    monkeypatch.setattr(client.client, "open", latest_not_found)
    with pytest.raises(UpdateError, match="No public update release was found"):
        client.check("0.1.4")


def test_manifest_rejects_tampering_mismatch_and_non_upgrade(tmp_path):
    key = Ed25519PrivateKey.generate()
    config = Config("owner/repo", key.public_key().public_bytes_raw(), False)
    content = b"installer"
    payload = {
        "schema_version": 1,
        "app_id": "pdf-toolbox",
        "version": "1.1.0",
        "tag": "v1.1.0",
        "repository": "owner/repo",
        "platform": "win32",
        "architecture": "x64",
        "installer_filename": ASSET,
        "installer_size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "release_date": "2026-11-17",
    }
    raw = json.dumps(payload).encode()
    signature = key.sign(raw)
    manifest = verify_manifest(config, raw, signature, "v1.1.0", "1.0.0")
    path = tmp_path / ASSET
    path.write_bytes(content)
    verify_file(path, manifest)
    path.write_bytes(b"tampering")
    with pytest.raises(UpdateError):
        verify_file(path, manifest)
    for body, sig, tag, installed in [
        (raw + b" ", signature, "v1.1.0", "1.0.0"),
        (raw, signature, "v1.1.0", "1.1.0"),
        (raw, signature, "v1.2.0", "1.0.0"),
    ]:
        with pytest.raises(UpdateError):
            verify_manifest(config, body, sig, tag, installed)
    for attribute, value in [
        ("repository", "other/repo"),
        ("architecture", "arm64"),
        ("app_id", "other"),
        ("installer_filename", "malware.exe"),
    ]:
        changed = json.dumps({**payload, attribute: value}).encode()
        with pytest.raises(UpdateError):
            verify_manifest(config, changed, key.sign(changed), "v1.1.0", "1.0.0")


def test_redirect_allowlist_strips_auth():
    from urllib.request import Request

    request = Request(
        "https://api.github.com/repos/owner/repo/releases/assets/123",
        headers={"Authorization": "Bearer abc", "Accept": "application/octet-stream"},
    )
    redirect = Redirects().redirect_request(
        request, None, 302, "", {}, "https://release-assets.githubusercontent.com/some/path"
    )
    assert redirect.get_header("Authorization") is None
    for url in (
        "http://release-assets.githubusercontent.com/path",
        "https://example.com/update",
        "https://release-assets.githubusercontent.com:444",
    ):
        with pytest.raises(UpdateError):
            Redirects().redirect_request(request, None, 302, "", {}, url)
