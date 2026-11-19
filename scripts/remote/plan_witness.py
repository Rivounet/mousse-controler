"""Generate LOCAL witness/command files for review. Never invokes SSH or SFTP."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import uuid

from remote import Config, QualificationError, child_path


def build_plan(config, local_directory, token):
    if not isinstance(token, str) or len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
        raise QualificationError('INVALID_WITNESS_TOKEN')
    local = str(local_directory.resolve())
    if any(c in local for c in '\r\n"'):
        raise QualificationError('UNSAFE_LOCAL_SFTP_PATH')
    root = config.root
    staging = child_path(root, 'staging')
    test_dir = child_path(root, 'staging\\MC-INIT-002-' + token)
    remote_file = test_dir + '\\witness.txt'
    payload = ('MC-INIT-002 | ' + token + ' | témoin UTF-8\n').encode('utf-8')
    digest = hashlib.sha256(payload).hexdigest()
    # Every remote file action rechecks all ancestors for junctions/symlinks.
    guard = (f"$r='{root}';$s='{staging}';$d='{test_dir}';$f='{remote_file}';"
             "$p=$d;while($p){if(Test-Path -LiteralPath $p){if((Get-Item -Force -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point refused'}};$p=Split-Path -Parent $p};")
    scripts = {
        '01-create-exclusive-directory.ps1': guard +
            "if(Test-Path -LiteralPath $d){throw 'Existing test directory: refuse'};"
            "$created=@();foreach($p in @($r,$s,$d)){if(-not(Test-Path -LiteralPath $p)){New-Item -ItemType Directory -Path $p -ErrorAction Stop|Out-Null;$created+=@($p)}};"
            "[ordered]@{created=$created;test_directory=$d}|ConvertTo-Json -Compress;",
        '03-hash-remote.ps1': guard +
            "if(-not(Test-Path -LiteralPath $f -PathType Leaf)){throw 'Missing witness'};"
            "if((Get-Item -LiteralPath $f).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Witness link refused'};"
            f"$h=(Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLowerInvariant();if($h -ne '{digest}'){{throw 'Hash mismatch: stop, preserve evidence'}};$h;",
        '06-remove-only-witness.ps1': guard +
            "if(-not(Test-Path -LiteralPath $f -PathType Leaf)){throw 'Missing witness: inspect before cleanup'};"
            "if((Get-Item -LiteralPath $f).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Witness link refused'};"
            f"$h=(Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLowerInvariant();if($h -ne '{digest}'){{throw 'Unexpected file: no deletion'}};"
            "Remove-Item -LiteralPath $f -ErrorAction Stop;if(Test-Path -LiteralPath $f){throw 'Witness remains'};"
            "[ordered]@{witness_absent=$true;directory_exists=(Test-Path -LiteralPath $d)}|ConvertTo-Json -Compress;",
    }
    sftp_path = '/' + remote_file.replace('\\', '/')
    scripts['02-upload.sftp'] = f'put "{local}/witness.txt" "{sftp_path}"\nquit\n'
    scripts['04-download.sftp'] = f'get "{sftp_path}" "{local}/returned.txt"\nquit\n'
    # No automatic directory deletion: the created list must be reviewed first.
    sleeper = "$ErrorActionPreference='Stop';Start-Sleep -Seconds 120 # MC-INIT-002-" + token
    encoded = base64.b64encode(sleeper.encode('utf-16-le')).decode('ascii')
    scripts['07-start-bounded-process.ps1'] = (
        f"$a='-NoProfile -NonInteractive -EncodedCommand {encoded}';"
        "$p=Start-Process -FilePath \"$PSHOME\\powershell.exe\" -ArgumentList $a -WindowStyle Hidden -PassThru;"
        "$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id);"
        "[ordered]@{pid=$p.Id;creation=$c.CreationDate.ToUniversalTime().ToString('o');start_time=$p.StartTime.ToUniversalTime().ToString('o');command=$c.CommandLine;"
        "executable=$c.ExecutablePath}|ConvertTo-Json -Compress;"
    )
    scripts['08-stop-process.TEMPLATE.ps1'] = (
        "# Fill exclusively from the reviewed result of 07. Never guess a PID.\n"
        "$ExpectedPid=0;$ExpectedCreation='';$ExpectedStartTime='';$ExpectedCommand='';$ExpectedExecutable='';\n"
        "if($ExpectedPid -le 0 -or -not $ExpectedCreation -or -not $ExpectedStartTime -or -not $ExpectedCommand -or -not $ExpectedExecutable){throw 'Incomplete process identity'};"
        "$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$ExpectedPid);"
        "if($null -eq $c){'ALREADY_EXITED';exit 0};"
        "if($c.CreationDate.ToUniversalTime().ToString('o') -cne $ExpectedCreation -or $c.CommandLine -cne $ExpectedCommand -or $c.ExecutablePath -ine $ExpectedExecutable){throw 'Process identity mismatch: no stop'};"
        "$p=Get-Process -Id $ExpectedPid -ErrorAction Stop;"
        "if($p.StartTime.ToUniversalTime().ToString('o') -cne $ExpectedStartTime){throw 'PID reused'};"
        "$p.Kill();[void]$p.WaitForExit(5000);if(-not $p.HasExited){throw 'Process remains'};'STOPPED';"
    )
    scripts['09-cleanup-empty-created.TEMPLATE.ps1'] = (
        "# Fill only with the exact created list returned by 01. Empty by default.\n"
        "$CreatedPaths=@();\n" + guard +
        "$allowed=@($r,$s,$d);foreach($p in $CreatedPaths){if($p -cnotin $allowed){throw 'Unapproved cleanup path'}};"
        "foreach($p in @($d,$s,$r)){if($p -cin $CreatedPaths){"
        "if(-not(Test-Path -LiteralPath $p)){continue};"
        "if((Get-Item -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Cleanup link refused'};"
        "if(@(Get-ChildItem -LiteralPath $p -Force).Count -ne 0){throw 'Nonempty directory: preserve'};"
        "[IO.Directory]::Delete($p,$false)}};'EMPTY_CREATED_DIRECTORIES_ONLY';"
    )
    return {'token': token, 'root': root, 'staging': staging, 'directory': test_dir,
            'remote_witness': remote_file, 'sha256': digest,
            'status': 'REQUIRES_EXPLICIT_AUTHORIZATION', 'scripts': scripts}, payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = Config(**json.loads(args.config.read_text(encoding='utf-8-sig')))
    plan, payload = build_plan(config, args.output, uuid.uuid4().hex)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'witness.txt').write_bytes(payload)
    for name, script in plan['scripts'].items():
        (args.output / name).write_text(script + '\n', encoding='utf-8')
    (args.output / 'plan.local.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in plan.items() if k != 'scripts'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
