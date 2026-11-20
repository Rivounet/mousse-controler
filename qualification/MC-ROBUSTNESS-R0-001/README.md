# MC-ROBUSTNESS-R0-001 — baseline et caractérisation

Date de qualification : 2026-11-20

SHA de référence : `f09ceaa99bc3417f1b2c4f7126467c7b7afae108`

Branche : `test/mc-robustness-r0-001`

## Verdict R0

**PASS_WITH_RESERVATIONS** pour le lot R0 uniquement.

Le socle logiciel de référence est reproductible et les situations de panne
demandées disposent de caractérisations isolées. Les défauts connus sont
volontairement encore présents : R0 ne les corrige pas. Ils sont rendus visibles
par des tests nommés `current_defect`, et non présentés comme des propriétés
souhaitables.

## Périmètre exécuté

- tests Python unitaires, contrats et intégrations simulées ;
- doubles de processus HOGP, transport, client HTTP, stockage et cycle de vie ;
- serveurs HTTP locaux éphémères sur `127.0.0.1` sans TLS réel ;
- compilation éphémère des trois artefacts C# puis suppression des binaires ;
- analyse syntaxique des scripts PowerShell ;
- aucune modification du code applicatif.

## Périmètre explicitement non exécuté

- aucun rapport HID, mouvement, clic ou défilement réel ;
- aucune capture d'écran réelle ;
- aucun accès Bluetooth, radio, session Windows interactive ou tâche planifiée ;
- aucun accès SSH ni contact avec `MonOrdinateur` ;
- aucun démarrage, arrêt ou remplacement de composant de production ;
- aucune mise à jour/rollback réel de `PositionAgent`.

## Exécution reproductible

Depuis la racine du dépôt, avec Python 3.12 :

```powershell
python -B scripts/qualification/run_r0_software_tests.py
```

Cette commande exclut par construction les 7 tests de diagnostic matériel et
annonce cette exclusion avant l'exécution. Voir [BASELINE.md](BASELINE.md),
[DEFECT-MATRIX.md](DEFECT-MATRIX.md), [R1-R5-CRITERIA.md](R1-R5-CRITERIA.md)
et [evidence/TEST-RESULTS.md](evidence/TEST-RESULTS.md).
