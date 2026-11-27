# Architecture des tests

La suite par défaut est strictement non matérielle. Elle ne contacte aucune
machine distante, n'émet aucun rapport HID, ne capture pas l'écran et
n'installe aucun artefact.

## Niveaux

| Répertoire | Responsabilité | Budget de phase |
|---|---|---:|
| `unit/` | logique pure, états, contrôleurs et persistance en mémoire/temporaire | inclus dans `fast` |
| `contract/` | contrats API, packaging et invariants statiques des frontières | inclus dans `fast` |
| `qualification/` | comportement fail-closed de l'orchestrateur et des suites | inclus dans `fast` |
| `integration/` | processus, sockets, TLS, PowerShell, fichiers, concurrence et rollback | 10 minutes |
| `system/` | application composée avec adaptateurs matériels simulés | inclus dans `integration` |
| `support/` | doubles, horloges et synchronisation partagés ; aucun test découvert | — |

Les diagnostics matériels restent sous `scripts/bluetooth` et
`scripts/diagnostics`, hors de ces niveaux. Leur exécution exige toujours une
autorisation distincte.

## Commandes de développement

```powershell
python -B scripts/qualification/run_software_tests.py --tier fast
python -B scripts/qualification/run_software_tests.py --tier integration
```

Ces commandes acceptent un arbre de travail en cours. La qualification
officielle exige au contraire un commit propre :

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

`software`, `build` et `full-local` restent des profils compatibles. L'ancien
`run_r0_software_tests.py` est conservé comme redirection temporaire vers la
suite complète.

## Règles

- un test appartient à un seul niveau ;
- aucun skip ou `expectedFailure` silencieux dans une qualification officielle ;
- préférer événements, barrières et horloges contrôlées aux délais arbitraires ;
- conserver zéro boucle de micro-polling `time.sleep` de 10 ms ou moins ;
- réserver les assertions sur le texte source aux invariants réellement
  statiques ; tester le comportement dès qu'une frontière est exécutable ;
- conserver sorties, certificats, dépôts et états dans des répertoires
  temporaires dédiés ;
- ne jamais transformer une preuve simulée en revendication matérielle.

`scripts/qualification/measure_test_architecture.py` vérifie l'attribution
directe des modules aux tests et produit les métriques de dette. Cette
attribution ne remplace pas une mesure d'exécution de lignes ou de branches.
