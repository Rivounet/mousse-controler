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

À compléter après le commit qualifié. Aucun diagnostic matériel, accès distant,
HID, capture réelle, installation ou déploiement n'est exécuté.

