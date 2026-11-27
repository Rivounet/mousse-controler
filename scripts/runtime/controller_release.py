"""Prepare and verify immutable local controller releases from exact Git commits."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

SCHEMA = "mousse-controller-release-v1"
SELECTION = ["scripts/runtime", "src/mousse_controler"]
MARKER = ".mousse-release.json"


class QualificationError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return (json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n").encode("utf-8")


def _no_links(path: Path) -> Path:
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise QualificationError("FILESYSTEM_LINK_REFUSED")
    return path


def _artifact_tools():
    remote_scripts = Path(__file__).resolve().parents[1] / "remote"
    if not remote_scripts.is_dir():
        raise QualificationError("ARTIFACT_TOOLS_UNAVAILABLE")
    sys.path.insert(0, str(remote_scripts))
    try:
        from artifacts import prepare, verify
        from remote import QualificationError as ArtifactError
    except ImportError as exc:
        raise QualificationError("ARTIFACT_TOOLS_UNAVAILABLE") from exc
    return prepare, verify, ArtifactError


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _contained(root: Path, path: Path) -> Path:
    root = root.resolve()
    path = path.resolve()
    if path == root or root not in path.parents:
        raise QualificationError("RELEASE_PATH_OUTSIDE_ROOT")
    return path


def _release_manifest(artifact: dict[str, object]) -> dict[str, object]:
    release_id = f"{artifact['git_sha']}-{artifact['archive_sha256']}"
    return {
        "schema": SCHEMA,
        "release_id": release_id,
        "git_sha": artifact["git_sha"],
        "artifact_sha256": artifact["archive_sha256"],
        "files": artifact["files"],
    }


def verify_release(
    release: Path,
    expected_release_id: str | None = None,
) -> dict[str, object]:
    release = _no_links(release)
    marker = release / MARKER
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise QualificationError("INVALID_RELEASE_MANIFEST") from exc
    if set(value) != {"schema", "release_id", "git_sha", "artifact_sha256", "files"}:
        raise QualificationError("INVALID_RELEASE_MANIFEST")
    identity = release.name if expected_release_id is None else expected_release_id
    if value["schema"] != SCHEMA or value["release_id"] != identity:
        raise QualificationError("INVALID_RELEASE_IDENTITY")
    entries = value["files"]
    if not isinstance(entries, list) or not entries:
        raise QualificationError("INVALID_RELEASE_MANIFEST")
    expected = {MARKER}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "size", "sha256", "git_mode"}:
            raise QualificationError("INVALID_RELEASE_MANIFEST")
        relative = Path(str(entry["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise QualificationError("INVALID_RELEASE_PATH")
        target = release / relative
        _contained(release, target)
        if not target.is_file() or target.is_symlink():
            raise QualificationError("RELEASE_FILE_MISSING")
        payload = target.read_bytes()
        if len(payload) != entry["size"] or _digest(payload) != entry["sha256"]:
            raise QualificationError("RELEASE_FILE_HASH_MISMATCH")
        expected.add(relative.as_posix())
    actual = {
        path.relative_to(release).as_posix()
        for path in release.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise QualificationError("RELEASE_CONTENT_MISMATCH")
    required = {
        "scripts/runtime/Start-MousseController.ps1",
        "scripts/runtime/controller_release.py",
        "src/mousse_controler/app.py",
    }
    if not required.issubset(expected):
        raise QualificationError("RELEASE_RUNTIME_INCOMPLETE")
    return value


def prepare_release(repository: Path, git_sha: str, releases_root: Path) -> dict[str, object]:
    releases_root = _no_links(releases_root)
    if not releases_root.is_dir():
        raise QualificationError("RELEASES_ROOT_MUST_EXIST")
    prepare, verify, artifact_error = _artifact_tools()
    try:
        archive, artifact = prepare(repository, git_sha, SELECTION)
        files = verify(archive, artifact)
    except artifact_error as exc:
        raise QualificationError(str(exc)) from exc
    manifest = _release_manifest(artifact)
    target = _contained(releases_root, releases_root / str(manifest["release_id"]))
    if any(len(str(target / Path(str(entry["path"])))) > 240 for entry in manifest["files"]):
        raise QualificationError("RELEASE_PATH_BUDGET_EXCEEDED")
    if target.exists():
        existing = verify_release(target)
        if existing != manifest:
            raise QualificationError("EXISTING_RELEASE_CONFLICT")
        return {"status": "REUSED", "release": str(target), **manifest}

    staging = _contained(releases_root, releases_root / f".staging-{uuid.uuid4().hex}")
    staging.mkdir(exist_ok=False)
    try:
        for name, payload in files.items():
            destination = _contained(staging, staging / Path(name))
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as output:
                output.write(payload)
        with (staging / MARKER).open("xb") as output:
            output.write(_canonical(manifest))
        verify_release(staging, expected_release_id=str(manifest["release_id"]))
        staging.replace(target)
        verify_release(target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return {"status": "PREPARED", "release": str(target), **manifest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("--repository", type=Path, required=True)
    build.add_argument("--ref", required=True)
    build.add_argument("--releases-root", type=Path, required=True)
    check = commands.add_parser("verify")
    check.add_argument("--release", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_release(args.repository, args.ref, args.releases_root)
        else:
            manifest = verify_release(args.release)
            result = {"status": "VERIFIED", "release": str(args.release.resolve()), **manifest}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (QualificationError, OSError, TypeError, ValueError) as exc:
        error = str(exc) if isinstance(exc, QualificationError) else type(exc).__name__
        print(json.dumps({"status": "FAIL", "error": error}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
