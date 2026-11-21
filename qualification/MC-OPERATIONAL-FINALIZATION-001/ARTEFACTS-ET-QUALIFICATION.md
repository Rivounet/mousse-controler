# Artefacts et qualification

## Qualification finale

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

| Élément | Résultat |
|---|---|
| SHA qualifié | `0706aa9a86a2a5c2777a099ead1d0cec4b50ebb3` |
| Verdict | `PASS` |
| Tests | 274 réussis |
| Compilation Python | PASS |
| Référence API | PASS |
| Analyse PowerShell | PASS, 22 scripts, aucun exécuté |
| Build PositionAgent | PASS |
| Durée | 136,0 s |
| Diagnostics matériels exclus | 7 |

## Artefacts de staging

| Artefact | Taille | SHA-256 | État |
|---|---:|---|---|
| `PositionAgent.exe` | 28 672 | `CF85521832957E382A684EA41742C4EF1BFB5A5762454A7BC2D09A70FE1EEC70` | construit, non installé |
| MSIX HOGP 1.0.0.3 | 187 032 | `49EC264ED631CFC882608BAFB98A28D6BF83B09BD1693D29E074470852AABEC3` | construit, non signé |
| MSIX 1.0.0.2 rollback | 190 501 | `907AFB9E458C7DA5C2B5555581065A310CD8EBC39BC9BB5EAE2CA508A0B12042` | signature valide |
| configuration proposée | 1 422 | `ADB7730DC464D63FD43871780EA6DE3861F440CB324AE38965DBD95782FE0783` | validée, sensible, hors Git |

Les artefacts et configurations sensibles restent sous
`staging/MC-OPERATIONAL-FINALIZATION-001/`. Aucun binaire ni secret n'est publié
dans la PR. Le manifeste local du dossier porte le SHA-256
`5B639BCC4D761DFC4B3C554665800978ECED9724C3026C359965D92E722EF931`.
