# MC-ROBUSTNESS-R4-001 — Tests

## Matrice de sécurité de l'orchestrateur

| Exigence | Preuve automatisée |
|---|---|
| Le profil logiciel ne lance aucun diagnostic matériel | liste fermée inspectée par `test_profiles_are_local_and_exclude_material_and_installation` |
| Le profil build n'installe aucun artefact | sortie contrainte au dossier de qualification ; aucune commande d'installation |
| `full-local` reste local | absence de SSH, cible, Bluetooth, installation et déploiement dans toutes ses phases |
| Outil manquant sans faux succès | simulation : verdict `BLOCKED`, code 2 |
| Test échoué sans faux succès | simulation : verdict `FAIL`, code 1 et log conservé |
| Interruption observable | simulation : phase `INTERRUPTED`, verdict `BLOCKED`, code 130 |
| SHA qualifié identifié | `git_sha` obligatoire dans `summary.json` |
| Exclusions indiquées | liste stable dans sortie console et résumé JSON |
| Temporaires nettoyés | vérification de disparition de `.temporary` après interruption |
| Utilisable après redémarrage | rechargement du module et reconstruction identique des profils sans état persistant |

Résultat ciblé final : **6/6 PASS en 3,330 s**. Ces tests n'appellent aucune
phase réelle de qualification.

## Non-régression

Le profil final a exécuté :

- 195 tests cœur, R0, R1, R2, R3 et R4 : PASS en 85,508 s ;
- 69 tests de déploiement et accès distant entièrement simulés : PASS en
  37,212 s ;
- 5 contrats non matériels de sécurité des diagnostics : PASS en 0,003 s.

Total : **269/269 PASS**, zéro échec attendu. Les propriétés couvertes incluent
`UNKNOWN`, quarantaine des boutons incertains, anti-rejeu, délais HOGP, limites
TLS/HTTP, quota de captures, fermeture des ressources et rollback
PositionAgent.

## Build

- `compileall` sur `src`, `scripts` et `tests`, avec cache redirigé vers le
  temporaire : PASS ;
- `python scripts/generate_api_reference.py --check` : PASS ;
- parse PowerShell 5.1 de 22 scripts sous `scripts/` et `src/`, sans exécution
  de ces scripts : PASS ;
- PositionAgent : `/target:exe /optimize+ /platform:x64 /warn:4
  /warnaserror+`, manifeste et références existants conservés : PASS ;
- builds complémentaires de contrôle PairingTool, MouseWitness et paquet HOGP :
  PASS, sans installation ni signature ajoutée.

## Diagnostics matériels exclus

Sept tests sont exclus par construction :

- `scripts.bluetooth.test_diagnostics` : 3 tests de radio Windows ;
- `scripts.diagnostics.test_inspect_monordinateur.TargetDiagnosticTests` :
  4 tests de cible/session.

Les diagnostics matériels n'ont aucun profil dans `qualify.py`. Leur lancement
reste une opération manuelle distincte, après autorisation explicite, avec les
préconditions de session, radio et cible de leurs procédures. R4 ne les a pas
exécutés.
