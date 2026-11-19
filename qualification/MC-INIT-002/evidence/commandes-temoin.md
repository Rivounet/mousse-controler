# Commandes du témoin — sélection expurgée

Commandes générées localement ; marqueurs non exécutables. Origine exacte : plan_witness.py et plan.local.json conservé localement. Chaque fragment est précédé du préambule UTF-8 du client SSH et du doctor de remote.py. Le plan a été examiné avant accord ; les deux corrections du test de processus sont consignées dans witness-roundtrip.json.

## 01-create-exclusive-directory.ps1

```text
$r='<RACINE_AUTORISÉE>';$s='<RACINE_AUTORISÉE>\staging';$d='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>';$f='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>\witness.txt';$p=$d;while($p){if(Test-Path -LiteralPath $p){if((Get-Item -Force -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point refused'}};$p=Split-Path -Parent $p};if(Test-Path -LiteralPath $d){throw 'Existing test directory: refuse'};$created=@();foreach($p in @($r,$s,$d)){if(-not(Test-Path -LiteralPath $p)){New-Item -ItemType Directory -Path $p -ErrorAction Stop|Out-Null;$created+=@($p)}};[ordered]@{created=$created;test_directory=$d}|ConvertTo-Json -Compress;
```

## 03-hash-remote.ps1

```text
$r='<RACINE_AUTORISÉE>';$s='<RACINE_AUTORISÉE>\staging';$d='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>';$f='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>\witness.txt';$p=$d;while($p){if(Test-Path -LiteralPath $p){if((Get-Item -Force -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point refused'}};$p=Split-Path -Parent $p};if(-not(Test-Path -LiteralPath $f -PathType Leaf)){throw 'Missing witness'};if((Get-Item -LiteralPath $f).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Witness link refused'};$h=(Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLowerInvariant();if($h -ne '1bf9a33ba5c8b4a59dabb33a09541316eb9499b76aaa6b07cb9e74c2df92f99a'){throw 'Hash mismatch: stop, preserve evidence'};$h;
```

## 06-remove-only-witness.ps1

```text
$r='<RACINE_AUTORISÉE>';$s='<RACINE_AUTORISÉE>\staging';$d='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>';$f='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>\witness.txt';$p=$d;while($p){if(Test-Path -LiteralPath $p){if((Get-Item -Force -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point refused'}};$p=Split-Path -Parent $p};if(-not(Test-Path -LiteralPath $f -PathType Leaf)){throw 'Missing witness: inspect before cleanup'};if((Get-Item -LiteralPath $f).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Witness link refused'};$h=(Get-FileHash -Algorithm SHA256 -LiteralPath $f).Hash.ToLowerInvariant();if($h -ne '1bf9a33ba5c8b4a59dabb33a09541316eb9499b76aaa6b07cb9e74c2df92f99a'){throw 'Unexpected file: no deletion'};Remove-Item -LiteralPath $f -ErrorAction Stop;if(Test-Path -LiteralPath $f){throw 'Witness remains'};[ordered]@{witness_absent=$true;directory_exists=(Test-Path -LiteralPath $d)}|ConvertTo-Json -Compress;
```

## 02-upload.sftp

```text
put "<RACINE_AUTORISÉE>\qualification\mc-init-002\witness-plan/witness.txt" "<TÉMOIN_DISTANT_SFTP>"
quit

```

## 04-download.sftp

```text
get "<TÉMOIN_DISTANT_SFTP>" "<RACINE_AUTORISÉE>\qualification\mc-init-002\witness-plan/returned.txt"
quit

```

## 07-start-bounded-process.ps1

```text
$a='-NoProfile -NonInteractive -EncodedCommand <ATTENTE_120_SECONDES_ENCODÉE>';$p=Start-Process -FilePath "$PSHOME\powershell.exe" -ArgumentList $a -WindowStyle Hidden -PassThru;$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id);[ordered]@{pid=$p.Id;creation=$c.CreationDate.ToUniversalTime().ToString('o');start_time=$p.StartTime.ToUniversalTime().ToString('o');command=$c.CommandLine;executable=$c.ExecutablePath}|ConvertTo-Json -Compress;
```

## 08-stop-process.TEMPLATE.ps1

```text
# Fill exclusively from the reviewed result of 07. Never guess a PID.
$ExpectedPid=0;$ExpectedCreation='';$ExpectedStartTime='';$ExpectedCommand='';$ExpectedExecutable='';
if($ExpectedPid -le 0 -or -not $ExpectedCreation -or -not $ExpectedStartTime -or -not $ExpectedCommand -or -not $ExpectedExecutable){throw 'Incomplete process identity'};$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$ExpectedPid);if($null -eq $c){'ALREADY_EXITED';exit 0};if($c.CreationDate.ToUniversalTime().ToString('o') -cne $ExpectedCreation -or $c.CommandLine -cne $ExpectedCommand -or $c.ExecutablePath -ine $ExpectedExecutable){throw 'Process identity mismatch: no stop'};$p=Get-Process -Id $ExpectedPid -ErrorAction Stop;if($p.StartTime.ToUniversalTime().ToString('o') -cne $ExpectedStartTime){throw 'PID reused'};$p.Kill();[void]$p.WaitForExit(5000);if(-not $p.HasExited){throw 'Process remains'};'STOPPED';
```

## 09-cleanup-empty-created.TEMPLATE.ps1

```text
# Fill only with the exact created list returned by 01. Empty by default.
$CreatedPaths=@();
$r='<RACINE_AUTORISÉE>';$s='<RACINE_AUTORISÉE>\staging';$d='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>';$f='<RACINE_AUTORISÉE>\staging\MC-INIT-002-<ID_TÉMOIN>\witness.txt';$p=$d;while($p){if(Test-Path -LiteralPath $p){if((Get-Item -Force -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point refused'}};$p=Split-Path -Parent $p};$allowed=@($r,$s,$d);foreach($p in $CreatedPaths){if($p -cnotin $allowed){throw 'Unapproved cleanup path'}};foreach($p in @($d,$s,$r)){if($p -cin $CreatedPaths){if(-not(Test-Path -LiteralPath $p)){continue};if((Get-Item -LiteralPath $p).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Cleanup link refused'};if(@(Get-ChildItem -LiteralPath $p -Force).Count -ne 0){throw 'Nonempty directory: preserve'};[IO.Directory]::Delete($p,$false)}};'EMPTY_CREATED_DIRECTORIES_ONLY';
```

Le contenu décodé du processus final est une attente Start-Sleep de 120 secondes avec un commentaire identifiant le témoin ; aucun Bluetooth ni port ouvert. Le modèle de stop exige les valeurs du processus créé. Pour le dernier essai, lancement, contrôle ALIVE, stop et contrôle ABSENT sont exécutés dans le même appel SSH, comme ci-dessous.

```text
$identity=(&{$a='-NoProfile -NonInteractive -EncodedCommand <ATTENTE_120_SECONDES_ENCODÉE>';$p=Start-Process -FilePath "$PSHOME\powershell.exe" -ArgumentList $a -WindowStyle Hidden -PassThru;$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.Id);[ordered]@{pid=$p.Id;creation=$c.CreationDate.ToUniversalTime().ToString('o');start_time=$p.StartTime.ToUniversalTime().ToString('o');command=$c.CommandLine;executable=$c.ExecutablePath}|ConvertTo-Json -Compress;}|ConvertFrom-Json);Start-Sleep -Milliseconds 200;$live=Get-Process -Id $identity.pid -ErrorAction Stop;if($live.HasExited){throw 'Process not alive'};'ALIVE_CONFIRMED';# Fill exclusively from the reviewed result of 07. Never guess a PID.
$ExpectedPid=[int]$identity.pid;$ExpectedCreation=$identity.creation;$ExpectedStartTime=$identity.start_time;$ExpectedCommand=$identity.command;$ExpectedExecutable=$identity.executable;
if($ExpectedPid -le 0 -or -not $ExpectedCreation -or -not $ExpectedStartTime -or -not $ExpectedCommand -or -not $ExpectedExecutable){throw 'Incomplete process identity'};$c=Get-CimInstance Win32_Process -Filter ('ProcessId='+$ExpectedPid);if($null -eq $c){'ALREADY_EXITED';exit 0};if($c.CreationDate.ToUniversalTime().ToString('o') -cne $ExpectedCreation -or $c.CommandLine -cne $ExpectedCommand -or $c.ExecutablePath -ine $ExpectedExecutable){throw 'Process identity mismatch: no stop'};$p=Get-Process -Id $ExpectedPid -ErrorAction Stop;if($p.StartTime.ToUniversalTime().ToString('o') -cne $ExpectedStartTime){throw 'PID reused'};$p.Kill();[void]$p.WaitForExit(5000);if(-not $p.HasExited){throw 'Process remains'};'STOPPED';if(Get-Process -Id $ExpectedPid -ErrorAction SilentlyContinue){throw 'Process remains'};'ABSENT_CONFIRMED';
```
