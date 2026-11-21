# Tests R5

## Baseline

Commande :

```powershell
python -B scripts/qualification/qualify.py --profile software
```

Résultat : **PASS**, 269/269 tests, 127,843 s, base
`c5d8ef6bdb06b0fb6295b946d0be578956e35d93`.

## Tests ciblés

```powershell
python -B -m unittest tests.test_trajectory.GeometryTests tests.test_api_catalog -v
```

Résultat : **15/15 PASS**, 9,277 s.

Couverture ajoutée : polygones très fins, concaves, coordonnées négatives,
grandes coordonnées, sommets colinéaires, quasi-dégénérescence, 50 graines par
famille, double exécution reproductible ; doublons de commandes, actions et
événements refusés avant mutation. Les tests existants couvrent génération de
référence, recherche/découverte, authentification et tolérance des paramètres
inconnus.

## Qualification finale

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

Résultat : **PASS** au SHA qualifié
`9c3b06df809f3fe21d4724cfa5326b5df177ca7f`, 271/271 tests logiciels et les
quatre contrôles de build PASS, en 133,546 s.

| Phase | Résultat | Durée |
|---|---:|---:|
| Tests logiciels | 271/271 PASS | 127,063 s |
| Compilation Python | PASS | 0,937 s |
| Référence API | PASS | 0,531 s |
| Syntaxe PowerShell | PASS | 0,969 s |
| Build PositionAgent | PASS | 2,250 s |

PositionAgent : 28 672 octets, SHA-256
`36322f018f8448786767e7df1d1af3cac595cef329afb10c66c2cd78ffa38628`.
Le binaire est un artefact local non installé.

Environnement : Windows 11 `10.0.26300`, Python 3.12.10, PowerShell 7.6.9,
Windows PowerShell 5.1.26100.10068 et Git 2.54.0.windows.1. Sept diagnostics
matériels ainsi que Bluetooth/HID/capture/SSH/installation/déploiement sont
exclus.

