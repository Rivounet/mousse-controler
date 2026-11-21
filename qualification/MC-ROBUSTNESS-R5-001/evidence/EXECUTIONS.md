# Exécutions R5

## Identité et baseline

- base distante vérifiée : `c5d8ef6bdb06b0fb6295b946d0be578956e35d93` ;
- branche : `refactor/mc-robustness-r5-001` ;
- état initial : propre ;
- baseline `software` : PASS, 269/269, 127,843 s ;
- environnement : Windows 11 `10.0.26300`, Python 3.12.10,
  PowerShell 7.6.9, Windows PowerShell 5.1.26100.10068, Git 2.54.0.windows.1.

## Reproductions

```text
C13 failed seeds: [4, 5, 7, 8, 13, 14, 15]
C14 overwritten before validation: True
```

Le polygone est `[(0,0),(16383,1),(16382,1)]`. La reproduction C-14 remplace
la description de `move` dans un processus Python isolé ; aucun fichier ni état
persistant n'est affecté.

## Tests ciblés après correction

```text
Ran 15 tests in 9.277s
OK
```

## Qualification finale

```text
profile: full-local
verdict: PASS
git_sha: 9c3b06df809f3fe21d4724cfa5326b5df177ca7f
software: 271/271 PASS (127.063 s)
python-compilation: PASS (0.937 s)
api-reference-check: PASS (0.531 s)
powershell-syntax: PASS (0.969 s)
position-agent-build: PASS (2.250 s)
total: 133.546 s
PositionAgent.exe: 28672 bytes
PositionAgent.exe sha256: 36322f018f8448786767e7df1d1af3cac595cef329afb10c66c2cd78ffa38628
```

Le commit suivant ne modifie que ces résultats documentaires ; le SHA ci-dessus
est le commit exact contenant le code, les tests et la documentation qualifiés.
Aucun diagnostic matériel, accès distant, HID, capture réelle, installation ou
déploiement n'a été exécuté.
