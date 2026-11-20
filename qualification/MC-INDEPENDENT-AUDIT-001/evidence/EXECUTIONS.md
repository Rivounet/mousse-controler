# MC-INDEPENDENT-AUDIT-001 — Exécutions logicielles

Toutes les commandes ont été lancées sur le commit
`d19db664bc1e7d83ab1d289f89373f9e327a482b`, dans le worktree dédié. Aucun
rapport HID, aucune capture d'écran et aucun accès à la machine cible n'ont été
effectués. Les chemins locaux sont remplacés par des marqueurs.

## Suites exécutées

| Commande normalisée | Résultat |
|---|---|
| `PYTHONPATH=src python -B -m unittest discover -s tests -v` | 114 tests, PASS, 4,152 s |
| `MC_TEST_TMP=<SHORT_TMP> python -B -m unittest discover -s scripts/remote -p 'test_*.py' -v` | 69 tests, PASS, 37,761 s |
| `python -B -m unittest scripts.bluetooth.test_pairability scripts.diagnostics.test_inspect_monordinateur.GattProbeSafetyTests -v` | 5 tests, PASS, 0,010 s |
| `python -B scripts/generate_api_reference.py --check` | PASS, référence courante |
| `Build-PositionAgent.ps1 -OutputDirectory <TEMP_OUTSIDE_REPOSITORY>` | PASS avec `/warnaserror+`; SHA-256 du binaire temporaire `AA0F3FEBCB8C9BE2FCE1145E6C541E5CA369BA321608F71082C329415D83EE2C` |
| Analyseur PowerShell sur tous les `.ps1` hors `qualification/` | PASS, aucune erreur syntaxique |

Total logiciel exécuté : **188 tests PASS sur 195 tests définis**. Les sept
tests non exécutés lancent des diagnostics réels de la radio Bluetooth ou de la
session graphique sur Windows. Ils ont été exclus pour conserver une exécution
strictement isolée et sans intervention matérielle.

Le binaire temporaire et son répertoire ont été supprimés après la compilation.
Le worktree était propre après les tests, avant l'ajout de ce livrable.

## Premiers essais non concluants

Ces essais sont consignés pour ne pas masquer les prérequis du harnais :

- La découverte directe de `tests/` sans `PYTHONPATH=src` a chargé 24 tests et
  produit 9 erreurs d'import `mousse_controler`. La relance avec le chemin source
  explicite a réussi. La commande officielle à la racine passe normalement par
  `test_all.py`, qui ajoute lui-même ce chemin.
- La première exécution de `scripts/remote` sans chemin temporaire court a lancé
  69 tests et produit 23 erreurs `WINDOWS_PATH_BUDGET_EXCEEDED`. La relance avec
  le prérequis documenté `MC_TEST_TMP=<SHORT_TMP>` a réussi intégralement.
- Le module Python `coverage` n'est pas installé; aucune mesure de couverture
  instrumentée n'est donc annoncée.

## Reproductions ciblées en mémoire

### Timeout HOGP non appliqué

Un faux processus dont `stdout.readline()` attend un événement a été injecté
dans `NativeHogpTransport`. Avec `startup_timeout=0.01`, le thread de démarrage
était toujours vivant après 0,1 s :

```text
{'startup_timeout_seconds': 0.01,
 'still_blocked_after_seconds': 0.1,
 'thread_alive': True}
```

### Bouton incertain avec poursuite

Le double simulé enregistre le rapport bouton puis lève une erreur, ce qui
représente une perte d'accusé après émission. Une action `press(left)` avec
`error_policy=continue` donne :

```text
{'state': 'UNKNOWN',
 'controller_stopped': False,
 'controller_buttons': 1,
 'transport_buttons': 1}
```

La fermeture de l'exécuteur a ensuite été appelée pour libérer le double.

### Fermeture avec action en file

Une attente active suivie d'une seconde attente en file, puis `close()`, donne :

```text
{'first': 'CANCELLED', 'queued': 'ACCEPTED'}
```

Le test est entièrement en mémoire et utilise `SimulatedHidTransport`.
