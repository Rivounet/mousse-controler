# Qualification locale

## Tentative initiale

La première exécution sur la base officielle a produit `FAIL` après 271 tests
réussis : `python-compilation` dépassait la limite de chemin Windows lorsque le
cache de bytecode était placé sous le répertoire profond de qualification.

Le défaut a été corrigé sans modifier l'application. Les 7 tests ciblés de
l'orchestrateur ont ensuite réussi.

## Qualification finale

Commande :

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

| Élément | Résultat |
|---|---|
| SHA qualifié | `6f2f5c16974711e0af59d8a86251eefdd8721b3f` |
| Verdict | `PASS` |
| Tests logiciels | 272 réussis, 0 échec attendu |
| Compilation Python | PASS |
| Référence API | PASS, à jour |
| Syntaxe PowerShell | PASS, 22 scripts analysés, aucun exécuté |
| Build PositionAgent | PASS |
| Durée totale | 137,859 s |
| Diagnostics matériels exclus | 7 |

Sont également exclus par construction : Bluetooth/HID réels, capture, SSH,
installation et déploiement. Aucun GitHub Actions ou service CI externe n'a été
utilisé.
