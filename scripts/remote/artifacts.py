"""Deterministic, explicitly selected Git artifacts. No network operations."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

from remote import QualificationError


MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
SHA = re.compile(r'[0-9a-f]{40}')
HASH = re.compile(r'[0-9a-f]{64}')


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def no_links(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise QualificationError('PATH_TRAVERSAL_REFUSED')
    for item in [path, *path.parents]:
        if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
            raise QualificationError('FILESYSTEM_LINK_REFUSED')
    return path


def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or not re.fullmatch(r'[A-Za-z0-9_./-]+', name):
        raise QualificationError('UNSAFE_ARTIFACT_PATH')
    path = PurePosixPath(name)
    if path.is_absolute() or name != path.as_posix() or any(p in ('', '.', '..') for p in name.split('/')):
        raise QualificationError('UNSAFE_ARTIFACT_PATH')
    for part in path.parts:
        if part.endswith('.') or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part):
            raise QualificationError('UNSAFE_WINDOWS_ARTIFACT_PATH')
        low = part.lower()
        if low in {'.git', '.env', '.ssh', '.aws', '.codex', 'node_modules', '__pycache__'} or low.startswith('.env.'):
            raise QualificationError('FORBIDDEN_ARTIFACT_FILE')
        if low.endswith(('.pem', '.key', '.pfx', '.p12', '.kdbx')) or low in {'id_rsa', 'id_ed25519', 'credentials', 'secrets.json', 'config.local.json'}:
            raise QualificationError('FORBIDDEN_ARTIFACT_FILE')
    return name


def git(repo, *args):
    try:
        result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationError('GIT_CLIENT_FAILED') from exc
    if result.returncode:
        raise QualificationError('GIT_COMMAND_FAILED')
    return result.stdout


def validate_selection(include):
    if not include or len(set(include)) != len(include):
        raise QualificationError('EXPLICIT_UNIQUE_SELECTION_REQUIRED')
    return sorted(safe_name(p.rstrip('/')) for p in include)


def selected(name, include):
    return any(name == prefix or name.startswith(prefix + '/') for prefix in include)


def make_archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, files[name])
    return buffer.getvalue()


def prepare(repo, sha, include):
    repo = Path(repo)
    if not SHA.fullmatch(sha or ''):
        raise QualificationError('FULL_COMMIT_SHA_REQUIRED')
    if git(repo, 'rev-parse', '--verify', sha + '^{commit}').decode().strip() != sha:
        raise QualificationError('UNKNOWN_COMMIT')
    if git(repo, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise QualificationError('LOCAL_REPOSITORY_NOT_CLEAN')
    include = validate_selection(include)
    files, modes, folded = {}, {}, set()
    total = 0
    for entry in git(repo, 'ls-tree', '-r', '-z', '--full-tree', sha).split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        try:
            name = raw_name.decode('utf-8', errors='strict')
        except UnicodeDecodeError as exc:
            raise QualificationError('NON_UTF8_GIT_PATH') from exc
        if not selected(name, include):
            continue
        safe_name(name)
        mode, kind, oid = metadata.decode('ascii').split()
        if kind != 'blob' or mode not in ('100644', '100755'):
            raise QualificationError('SYMLINK_OR_SUBMODULE_REFUSED')
        if name.casefold() in folded:
            raise QualificationError('WINDOWS_CASE_COLLISION')
        folded.add(name.casefold())
        size = int(git(repo, 'cat-file', '-s', oid))
        total += size
        if size > MAX_FILE or total > MAX_TOTAL:
            raise QualificationError('ARTIFACT_SIZE_LIMIT')
        payload = git(repo, 'cat-file', 'blob', oid)
        if len(payload) != size:
            raise QualificationError('INCOMPLETE_GIT_BLOB')
        # This is defense in depth, not a complete secret detector.
        if re.search(rb'(?m)^-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----\r?$', payload) or re.search(rb'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})', payload):
            raise QualificationError('SUSPECTED_SECRET_IN_ARTIFACT')
        files[name] = payload
        modes[name] = mode
    if not files or any(not any(selected(name, [prefix]) for name in files) for prefix in include):
        raise QualificationError('EMPTY_OR_MISSING_SELECTION')
    archive = make_archive(files)
    manifest = {'schema': 1, 'git_sha': sha, 'archive_sha256': digest(archive),
                'selection': include, 'files': [{'path': name, 'size': len(files[name]),
                                                'sha256': digest(files[name]), 'git_mode': modes[name]}
                                               for name in sorted(files)]}
    # Reject a repository changing while Git objects were read (no working-tree bytes used).
    if git(repo, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise QualificationError('LOCAL_REPOSITORY_CHANGED')
    return archive, manifest


def verify(archive, manifest):
    try:
        if set(manifest) != {'schema', 'git_sha', 'archive_sha256', 'selection', 'files'} or manifest['schema'] != 1:
            raise QualificationError('INVALID_MANIFEST')
        if not SHA.fullmatch(manifest['git_sha']) or not HASH.fullmatch(manifest['archive_sha256']):
            raise QualificationError('INVALID_MANIFEST')
        if digest(archive) != manifest['archive_sha256']:
            raise QualificationError('ARTIFACT_HASH_MISMATCH')
        include = validate_selection(manifest['selection'])
        if include != manifest['selection'] or not manifest['files']:
            raise QualificationError('INVALID_MANIFEST')
        expected, folded = {}, set()
        for entry in manifest['files']:
            if set(entry) != {'path', 'size', 'sha256', 'git_mode'}:
                raise QualificationError('INVALID_MANIFEST')
            name = safe_name(entry['path'])
            if not selected(name, include) or name.casefold() in folded:
                raise QualificationError('INVALID_MANIFEST_SELECTION')
            if type(entry['size']) is not int or not 0 <= entry['size'] <= MAX_FILE or not HASH.fullmatch(entry['sha256']) or entry['git_mode'] not in ('100644','100755'):
                raise QualificationError('INVALID_MANIFEST')
            folded.add(name.casefold())
            expected[name] = entry
        if list(expected) != sorted(expected) or sum(e['size'] for e in expected.values()) > MAX_TOTAL:
            raise QualificationError('INVALID_MANIFEST')
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            infos = zipped.infolist()
            if [i.filename for i in infos] != list(expected):
                raise QualificationError('ARTIFACT_CONTENT_MISMATCH')
            files = {}
            for info in infos:
                entry = expected[info.filename]
                if info.file_size != entry['size'] or info.compress_type != zipfile.ZIP_STORED or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG:
                    raise QualificationError('INVALID_ARCHIVE_ENTRY')
                value = zipped.read(info)
                if digest(value) != entry['sha256']:
                    raise QualificationError('FILE_HASH_MISMATCH')
                files[info.filename] = value
        if make_archive(files) != archive:
            raise QualificationError('NON_CANONICAL_ARCHIVE')
        return files
    except (TypeError, ValueError, KeyError, zipfile.BadZipFile, OSError) as exc:
        raise QualificationError('INVALID_ARTIFACT') from exc


def write_bundle(directory, archive, manifest):
    verify(archive, manifest)
    directory = no_links(directory)
    expected = {'artifact.zip': archive, 'manifest.json': canonical(manifest)}
    if directory.exists():
        if directory.is_symlink() or (hasattr(directory,'is_junction') and directory.is_junction()):
            raise QualificationError('BUNDLE_LINK_REFUSED')
        if {p.name for p in directory.iterdir()} != set(expected) or any(not (directory/name).is_file() or (directory/name).is_symlink() or (directory/name).read_bytes() != value for name,value in expected.items()):
            raise QualificationError('EXISTING_BUNDLE_CONFLICT')
        return 'REUSED_IDENTICAL'
    directory.mkdir(parents=False, exist_ok=False)
    # Exclusive writes: interrupted bundles remain visible and are never auto-overwritten.
    for name, value in expected.items():
        with (directory/name).open('xb') as output:
            output.write(value)
    return 'PREPARED_LOCAL'


def load_bundle(directory):
    directory = no_links(directory)
    for path in [directory, directory/'artifact.zip', directory/'manifest.json']:
        if path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction()):
            raise QualificationError('BUNDLE_LINK_REFUSED')
    try:
        if {p.name for p in directory.iterdir()} != {'artifact.zip','manifest.json'}:
            raise QualificationError('INCOMPLETE_OR_UNEXPECTED_BUNDLE')
        archive = (directory/'artifact.zip').read_bytes()
        manifest = json.loads((directory/'manifest.json').read_bytes())
    except (OSError, ValueError) as exc:
        raise QualificationError('INCOMPLETE_BUNDLE') from exc
    verify(archive, manifest)
    return archive, manifest
