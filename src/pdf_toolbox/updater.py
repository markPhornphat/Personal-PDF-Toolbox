"""The only component allowed to use the network."""

import base64
import hashlib
import hmac
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import mkdtemp
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .pdf import check_cancelled

ASSET = "PDF-Toolbox-Setup-x64.exe"
MANIFEST = "update-manifest.json"
SIGNATURE = "update-manifest.sig"
API = "https://api.github.com"
ASSET_HOSTS = {"release-assets.githubusercontent.com", "objects.githubusercontent.com"}
MAX_INSTALLER = 512 * 1024 * 1024
MIN_WINDOWS_BUILD = 17763


class UpdateError(ValueError):
    pass


def version_tuple(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(
        r"(0|[1-9][0-9]{0,8})(\.(0|[1-9][0-9]{0,8})){2}", value
    ):
        raise UpdateError("The release does not have a valid stable version.")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


@dataclass(frozen=True)
class Config:
    repository: str
    key: bytes
    private: bool = True
    source_repository: str = "markPhornphat/Personal-PDF-Toolbox"
    require_authenticode: bool = False

    @classmethod
    def load(cls, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        repository = data["repository"]
        if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repository):
            raise UpdateError("The update repository is not configured.")
        key = base64.b64decode(data["public_key"], validate=True)
        if len(key) != 32 or type(data["private"]) is not bool:
            raise UpdateError("The update verification key is not configured.")
        require_authenticode = data.get("require_authenticode", False)
        if type(require_authenticode) is not bool:
            raise UpdateError("The Windows publisher policy is invalid.")
        return cls(
            repository,
            key,
            data["private"],
            data.get("source_repository", repository),
            require_authenticode,
        )


@dataclass(frozen=True)
class Manifest:
    version: str
    size: int
    sha256: str
    date: str


@dataclass(frozen=True)
class Release:
    manifest: Manifest
    asset_id: int
    notes: str


def verify_manifest(config, raw, signature, tag, installed) -> Manifest:
    try:
        Ed25519PublicKey.from_public_bytes(config.key).verify(signature, raw)
        data = json.loads(raw)
        expected = {
            "schema_version": 1,
            "app_id": "pdf-toolbox",
            "repository": config.repository,
            "tag": tag,
            "platform": "win32",
            "architecture": "x64",
            "installer_filename": ASSET,
        }
        if any(data.get(key) != value for key, value in expected.items()):
            raise ValueError
        version = data["version"]
        if tag != f"v{version}" or version_tuple(version) <= version_tuple(installed):
            raise ValueError
        size, digest = data["installer_size"], data["sha256"]
        if type(size) is not int or not 0 < size <= MAX_INSTALLER:
            raise ValueError
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError
        released = date.fromisoformat(data["release_date"]).isoformat()
        build = data.get("minimum_windows_build", MIN_WINDOWS_BUILD)
        if type(build) is not int or build < MIN_WINDOWS_BUILD:
            raise ValueError
        if sys.platform == "win32" and sys.getwindowsversion().build < build:
            raise ValueError
        return Manifest(version, size, digest, released)
    except (InvalidSignature, ValueError, KeyError, TypeError, AttributeError):
        raise UpdateError("The release information could not be verified.") from None


def verify_file(path: Path, manifest: Manifest, require_authenticode: bool = False) -> None:
    if path.name != ASSET or path.stat().st_size != manifest.size:
        raise UpdateError("The installer size does not match the signed release.")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if not hmac.compare_digest(digest, manifest.sha256):
        raise UpdateError("The installer checksum does not match the signed release.")
    if require_authenticode:
        verify_authenticode(path)


def verify_authenticode(path: Path) -> None:
    """Verify Windows publisher trust using only local certificates and cached data."""
    import ctypes
    from ctypes import wintypes
    from uuid import UUID

    if sys.platform != "win32":
        raise UpdateError("Windows publisher trust verification requires Windows.")

    class FileInfo(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("filepath", wintypes.LPCWSTR),
            ("handle", wintypes.HANDLE),
            ("known_subject", ctypes.c_void_p),
        ]

    class TrustData(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("policy", ctypes.c_void_p),
            ("client", ctypes.c_void_p),
            ("ui", wintypes.DWORD),
            ("revocation", wintypes.DWORD),
            ("choice", wintypes.DWORD),
            ("file", ctypes.POINTER(FileInfo)),
            ("state_action", wintypes.DWORD),
            ("state", wintypes.HANDLE),
            ("url", wintypes.LPCWSTR),
            ("flags", wintypes.DWORD),
            ("ui_context", wintypes.DWORD),
            ("signature_settings", ctypes.c_void_p),
        ]

    action = (ctypes.c_ubyte * 16).from_buffer_copy(
        UUID("00aac56b-cd44-11d0-8cc2-00c04fc295ee").bytes_le
    )
    file = FileInfo(ctypes.sizeof(FileInfo), str(path), None, None)
    data = TrustData()
    data.size = ctypes.sizeof(TrustData)
    data.ui = 2  # WTD_UI_NONE
    data.choice = 1  # WTD_CHOICE_FILE
    data.flags = 0x1000  # WTD_CACHE_ONLY_URL_RETRIEVAL
    data.file = ctypes.pointer(file)
    verify = ctypes.WinDLL("wintrust.dll").WinVerifyTrust
    verify.argtypes = [wintypes.HWND, ctypes.c_void_p, ctypes.POINTER(TrustData)]
    verify.restype = wintypes.LONG
    if verify(None, ctypes.byref(action), ctypes.byref(data)) != 0:
        raise UpdateError("Windows could not verify the installer publisher.")


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urlsplit(newurl)
        try:
            allowed = (
                url.scheme == "https"
                and url.hostname in ASSET_HOSTS
                and url.port in (None, 443)
                and url.username is None
                and req.get_header("Accept") == "application/octet-stream"
            )
        except ValueError:
            allowed = False
        if not allowed:
            raise UpdateError("GitHub returned an unexpected download redirect.")
        return Request(
            newurl, headers={"Accept": "application/octet-stream", "User-Agent": "PDF-Toolbox"}
        )


class GitHub:
    def __init__(self, config: Config, credential: str = ""):
        if config.private and not credential:
            raise UpdateError("Private updates need a GitHub credential in Settings.")
        self.config = config
        self.credential = credential if config.private else ""
        self.client = build_opener(Redirects())

    def request(self, path, accept):
        headers = {
            "Accept": accept,
            "User-Agent": "PDF-Toolbox",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.credential:
            headers["Authorization"] = f"Bearer {self.credential}"
        request = Request(f"{API}/repos/{self.config.repository}/releases/{path}", headers=headers)
        try:
            return self.client.open(request, timeout=12)
        except HTTPError as error:
            error.close()
            if error.code in {403, 429} and (
                error.headers.get("X-RateLimit-Remaining") == "0" or error.code == 429
            ):
                raise UpdateError(
                    "GitHub’s update check limit was reached. Try again later."
                ) from None
            if error.code in {401, 403, 404}:
                raise UpdateError(
                    "The release is unavailable. Check the repository and credential."
                ) from None
            raise UpdateError("GitHub could not serve this update. Try again later.") from None
        except (URLError, TimeoutError):
            raise UpdateError("GitHub could not be reached. Try again when online.") from None

    def small(self, path, limit, accept="application/octet-stream"):
        with self.request(path, accept) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise UpdateError("GitHub returned unexpectedly large release information.")
        return data

    def check(self, installed: str) -> Release | None:
        raw = self.small("latest", 1_048_576, "application/vnd.github+json")
        try:
            release = json.loads(raw)
            if release["draft"] or release["prerelease"]:
                return None
            tag = release["tag_name"]
            if not tag.startswith("v"):
                raise ValueError
            if version_tuple(tag[1:]) <= version_tuple(installed):
                return None
            assets = {asset["name"]: asset for asset in release["assets"]}

            def identifier(name):
                asset = assets[name]
                if type(asset["id"]) is not int or asset["id"] <= 0 or asset["state"] != "uploaded":
                    raise ValueError
                return asset["id"]

            manifest_id, signature_id, installer_id = map(identifier, (MANIFEST, SIGNATURE, ASSET))
            notes = str(release.get("body") or "")[:12000]
        except (ValueError, KeyError, AttributeError, TypeError):
            raise UpdateError(
                "The GitHub release metadata or required assets are invalid."
            ) from None
        manifest = verify_manifest(
            self.config,
            self.small(f"assets/{manifest_id}", 8192),
            self.small(f"assets/{signature_id}", 64),
            tag,
            installed,
        )
        if assets[ASSET].get("size") != manifest.size:
            raise UpdateError("GitHub lists a different installer size than the signed release.")
        return Release(manifest, installer_id, notes)

    def download(self, release, directory, cancelled, progress) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(directory).free < release.manifest.size + 8 * 1024 * 1024:
            raise UpdateError("Free some disk space before downloading the installer.")
        folder = Path(mkdtemp(prefix="update-", dir=directory))
        path = folder / ASSET
        try:
            with self.request(f"assets/{release.asset_id}", "application/octet-stream") as response:
                with path.open("xb") as stream:
                    written = 0
                    while chunk := response.read(256 * 1024):
                        check_cancelled(cancelled)
                        written += len(chunk)
                        if written > release.manifest.size:
                            raise UpdateError("The installer is larger than the signed release.")
                        stream.write(chunk)
                        progress(written, release.manifest.size)
            check_cancelled(cancelled)
            verify_file(path, release.manifest, self.config.require_authenticode)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return path


class Credentials:
    def __init__(self, repository):
        self.target = f"PDF Toolbox/GitHub/{repository}"

    def read(self) -> str:
        from win32ctypes.pywin32 import pywintypes, win32cred

        try:
            entry = win32cred.CredRead(self.target, win32cred.CRED_TYPE_GENERIC)
        except pywintypes.error as error:
            if error.winerror == 1168:
                return ""
            raise UpdateError(
                "Windows Credential Manager could not read the update token."
            ) from None
        return entry["CredentialBlob"].decode("utf-16-le")

    def save(self, token: str) -> None:
        from win32ctypes.pywin32 import pywintypes, win32cred

        try:
            if token:
                win32cred.CredWrite(
                    {
                        "Type": win32cred.CRED_TYPE_GENERIC,
                        "TargetName": self.target,
                        "CredentialBlob": token,
                        "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                        "UserName": "GitHub",
                    }
                )
            else:
                win32cred.CredDelete(self.target, win32cred.CRED_TYPE_GENERIC)
        except pywintypes.error as error:
            if token or error.winerror != 1168:
                raise UpdateError("Windows Credential Manager could not save the change.") from None
