"""Read-only MC-INIT-002 foundation. No remote write operation is implemented."""
from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import hashlib
import json
import ntpath
from pathlib import Path
import re
import subprocess
import sys
import time


class QualificationError(Exception):
    pass


class NotImplementedOperation(QualificationError):
    pass


@dataclass(frozen=True)
class Result:
    code: int
    stdout: str
    stderr: str
    elapsed_seconds: float


def run_process(argv, *, timeout=20, input_bytes=None):
    """No shell; separate UTF-8 streams; timeout kills/reaps the local client only."""
    start = time.monotonic()
    try:
        result = subprocess.run(argv, input=input_bytes, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise QualificationError('CLIENT_TIMEOUT: remote completion is not guaranteed') from exc
    except OSError as exc:
        raise QualificationError('CLIENT_START_FAILED') from exc
    try:
        stdout = result.stdout.decode('utf-8', errors='strict')
        stderr = result.stderr.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise QualificationError('INVALID_UTF8: raw output must stay local') from exc
    return Result(result.returncode, stdout, stderr, round(time.monotonic() - start, 3))


def validate_root(root):
    """Narrow Windows path grammar; no UNC, drive root, ADS, quotes or traversal."""
    if not isinstance(root, str) or not re.fullmatch(r'[A-Za-z]:\\[A-Za-z0-9 _-]+(?:\\[A-Za-z0-9 _-]+)*', root):
        raise QualificationError('UNSAFE_ROOT')
    parts = root[3:].split('\\')
    if any(part.endswith((' ', '.')) or re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$', part) for part in parts):
        raise QualificationError('UNSAFE_ROOT')
    if parts[-1].casefold() != 'mousse-controler':
        raise QualificationError('DEDICATED_ROOT_REQUIRED')
    return ntpath.normpath(root)


def child_path(root, relative):
    root = validate_root(root)
    if not re.fullmatch(r'[A-Za-z0-9_-]+(?:\\[A-Za-z0-9_-]+)*', relative):
        raise QualificationError('UNAUTHORIZED_PATH')
    result = ntpath.join(root, relative)
    if ntpath.commonpath([root, result]).casefold() != root.casefold():
        raise QualificationError('UNAUTHORIZED_PATH')
    return result


@dataclass(frozen=True)
class Config:
    host: str
    expected_computer: str
    root: str
    timeout: float = 20

    def __post_init__(self):
        for value in (self.host, self.expected_computer):
            if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,62}', value):
                raise QualificationError('INVALID_HOST_ALIAS')
        validate_root(self.root)
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (float, int)) or not 0.5 <= self.timeout <= 60:
            raise QualificationError('INVALID_TIMEOUT')


PREFIX = "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false);$OutputEncoding=[Console]::OutputEncoding;"


class Client:
    def __init__(self, config, runner=run_process):
        self.config = config
        self.runner = runner

    def ssh(self, script, *, timeout=None):
        # EncodedCommand avoids cmd.exe quoting and never executes arbitrary CLI text.
        script = PREFIX + script
        encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        command = 'powershell.exe -NoProfile -NonInteractive -EncodedCommand ' + encoded
        if len(command) > 7500:
            raise QualificationError('REMOTE_COMMAND_TOO_LONG')
        argv = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
                '-o', 'PasswordAuthentication=no', '-o', 'KbdInteractiveAuthentication=no',
                '-o', 'PreferredAuthentications=publickey',
                '-o', 'ConnectionAttempts=1', '-o', 'ConnectTimeout=8', self.config.host, command]
        return self.runner(argv, timeout=self.config.timeout if timeout is None else timeout)

    def doctor(self):
        root = validate_root(self.config.root)
        # Root grammar excludes quote/metacharacter injection. No script is copied remotely.
        script = (
            f"$r='{root}';$p=$r;$links=$false;while($p){{if(Test-Path -LiteralPath $p){{if((Get-Item -Force -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){{$links=$true}}}};$p=Split-Path -Parent $p}};"
            "$parent=Split-Path -Parent $r;$acl=Get-Acl -LiteralPath $parent;"
            "$a=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);"
            "$g=Get-Command git -ErrorAction SilentlyContinue;$v=$null;if($g){$v=(& git --version)};"
            "[ordered]@{computer=$env:COMPUTERNAME;ps_version=$PSVersionTable.PSVersion.ToString();"
            "administrator=$a;root_exists=(Test-Path -LiteralPath $r);parent_exists=(Test-Path -LiteralPath $parent);"
            "ancestor_reparse_point=[bool]$links;parent_acl_readable=($null -ne $acl);"
            "write_access_tested=$false;git_version=$v;utf8='été — témoin'}|ConvertTo-Json -Compress;exit 0"
        )
        result = self.ssh(script)
        if result.code != 0:
            raise QualificationError(f'SSH_DOCTOR_FAILED:{result.code}')
        try:
            data = json.loads(result.stdout.lstrip('\ufeff'))
        except (ValueError, TypeError) as exc:
            raise QualificationError('INVALID_DOCTOR_JSON') from exc
        required = {'computer', 'ps_version', 'administrator', 'root_exists', 'parent_exists',
                    'ancestor_reparse_point', 'parent_acl_readable', 'write_access_tested', 'git_version', 'utf8'}
        if not isinstance(data, dict) or set(data) != required:
            raise QualificationError('INVALID_DOCTOR_SCHEMA')
        if not isinstance(data['computer'], str) or data['computer'].casefold() != self.config.expected_computer.casefold():
            raise QualificationError('HOST_IDENTITY_MISMATCH')
        if data['utf8'] != 'été — témoin':
            raise QualificationError('UTF8_PROBE_FAILED')
        for field in ['administrator', 'root_exists', 'parent_exists', 'ancestor_reparse_point', 'parent_acl_readable', 'write_access_tested']:
            if type(data[field]) is not bool:
                raise QualificationError('INVALID_DOCTOR_SCHEMA')
        if data['ancestor_reparse_point'] or not data['parent_exists'] or not data['parent_acl_readable']:
            raise QualificationError('UNSAFE_REMOTE_ROOT')
        return data

    def status(self):
        data = self.doctor()
        return {'environment': data, 'application_status': 'NON_EXÉCUTÉ',
                'active_sha': None, 'note': 'No runtime health or process ownership implemented'}

    def probe(self, kind):
        # Only bounded, read-only qualification probes are accepted.
        self.doctor()
        scripts = {
            'streams': "[Console]::Out.WriteLine('été stdout');[Console]::Error.WriteLine('échec stderr');exit 37",
            'timeout': 'Start-Sleep -Seconds 4;exit 0',
        }
        if kind not in scripts:
            raise QualificationError('UNKNOWN_PROBE')
        return self.ssh(scripts[kind], timeout=1 if kind == 'timeout' else None)

    def sftp_listing(self):
        self.doctor()
        argv = ['sftp', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
                '-o', 'PasswordAuthentication=no', '-o', 'KbdInteractiveAuthentication=no',
                '-o', 'PreferredAuthentications=publickey',
                '-o', 'ConnectionAttempts=1', '-o', 'ConnectTimeout=8', '-b', '-', self.config.host]
        # Pwd only; do not list personal files or write known_hosts.
        result = self.runner(argv, timeout=self.config.timeout, input_bytes=b'pwd\nquit\n')
        if result.code != 0:
            raise QualificationError(f'SFTP_READ_FAILED:{result.code}')
        return result  # May contain a private path: keep raw result local.


def sync_plan(config, repository, sha, *, dry_run):
    if not dry_run:
        raise NotImplementedOperation('REMOTE_WRITES_NOT_IMPLEMENTED')
    if not re.fullmatch(r'[0-9a-f]{40}', sha or ''):
        raise QualificationError('FULL_COMMIT_SHA_REQUIRED')
    if not (repository / '.git').exists():
        raise QualificationError('LOCAL_REPOSITORY_REQUIRED')
    result = run_process(['git', '-C', str(repository), 'rev-parse', '--verify', sha + '^{commit}'])
    if result.code or result.stdout.strip() != sha:
        raise QualificationError('UNKNOWN_COMMIT')
    dirty = run_process(['git', '-C', str(repository), 'status', '--porcelain=v1', '--untracked-files=all'])
    if dirty.code or dirty.stdout:
        raise QualificationError('LOCAL_REPOSITORY_NOT_CLEAN')
    return {'mode': 'PLAN_ONLY', 'sha': sha, 'remote_contacted': False,
            'remote_checks': 'NON_EXÉCUTÉ', 'artifact_created': False,
            'target': child_path(config.root, 'staging\\' + sha),
            'steps': ['doctor', 'check remote source state if present', 'build immutable artifact and manifest',
                      'transfer after authorization', 'verify remote artifact hash'],
            'execution': 'NON_IMPLEMENTED'}


def verify_transfer(result, payload, expected_sha256):
    """Local foundation for future transfer: never accept partial/error output."""
    if result.code != 0:
        raise QualificationError(f'TRANSFER_FAILED:{result.code}')
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256 or ''):
        raise QualificationError('INVALID_SHA256')
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise QualificationError('TRANSFER_HASH_MISMATCH')
    return {'integrity': 'PASS', 'bytes': len(payload)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True, help='Local configuration; never commit real paths')
    sub = parser.add_subparsers(dest='operation', required=True)
    for name in ['doctor', 'status', 'logs', 'stop', 'deploy', 'rollback']:
        sub.add_parser(name)
    sync = sub.add_parser('sync')
    sync.add_argument('--dry-run', action='store_true')
    sync.add_argument('--ref', required=True)
    sync.add_argument('--repository', type=Path, required=True)
    test = sub.add_parser('test')
    test.add_argument('--probe', choices=['streams', 'timeout', 'sftp'], required=True)
    args = parser.parse_args(argv)
    try:
        config = Config(**json.loads(args.config.read_text(encoding='utf-8-sig')))
        client = Client(config)
        if args.operation in ['logs', 'stop', 'deploy', 'rollback']:
            raise NotImplementedOperation('NON_IMPLEMENTED: no remote operation attempted')
        if args.operation == 'sync':
            data = sync_plan(config, args.repository, args.ref, dry_run=args.dry_run)
        elif args.operation in ['doctor', 'status']:
            data = getattr(client, args.operation)()
        else:
            result = client.sftp_listing() if args.probe == 'sftp' else client.probe(args.probe)
            data = {'code': result.code, 'stdout': result.stdout, 'stderr': result.stderr,
                    'elapsed_seconds': result.elapsed_seconds, 'raw_output_keep_local': True}
            print(json.dumps(data, ensure_ascii=False))
            return result.code
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except NotImplementedOperation as exc:
        print(json.dumps({'status': 'NON_EXÉCUTÉ', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 3
    except (QualificationError, ValueError, TypeError, OSError) as exc:
        # Do not emit file names, config contents or arbitrary remote output on failure.
        error = str(exc) if isinstance(exc, QualificationError) else type(exc).__name__
        print(json.dumps({'status': 'FAIL', 'error': error}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
