# Baseline R0

## Référence Git

| Élément | Valeur |
|---|---|
| Dépôt distant | `Rivounet/mousse-controler` |
| `origin/main` qualifié | `f09ceaa99bc3417f1b2c4f7126467c7b7afae108` |
| Commit | `Merge pull request #12 from Rivounet/docs/mc-audit-consolidation-20261120` |
| Branche R0 | `test/mc-robustness-r0-001` |
| État initial | propre, créé depuis `origin/main` |

Le clone de travail actif sur une autre branche n'a pas été réinitialisé ni
écrasé. R0 a été réalisé dans un worktree isolé.

## Outillage observé

| Outil | Version/disponibilité |
|---|---|
| Git | 2.54.0.windows.1 |
| Python | 3.12.10 |
| PowerShell | 7.6.9 Core |
| Système | Windows 10.0.26300, Win32NT |
| CLI `dotnet` | absent du `PATH` |
| .NET Framework Full | 4.8.10008, release 534296 |
| Roslyn `csc.exe` | présent, 4.1400.26.42407 |
| Windows SDK | références 10.0.26100.0 attendues par les scripts de build |

Le projet Python n'a pas de manifeste de dépendances externe : le contrôleur et
les tests R0 utilisent la bibliothèque standard. Les builds C# utilisent les
références Windows/.NET Framework déjà déclarées dans les scripts existants.

## Commandes de référence

```powershell
$env:PYTHONPATH = 'src'
python -B -m unittest discover -s tests -v

$env:MC_TEST_TMP = '<répertoire temporaire court et isolé>'
python -B -m unittest discover -s scripts/remote -p test_*.py -v

python -B -m unittest `
  scripts.bluetooth.test_pairability `
  scripts.diagnostics.test_inspect_monordinateur.GattProbeSafetyTests -v
```

Commande agrégée R0 :

```powershell
python -B scripts/qualification/run_r0_software_tests.py
```

## Résultats avant ajout R0

| Classe | Exécutés | Résultat | Nature |
|---|---:|---|---|
| `tests/` | 114 | PASS | unités, contrats, intégrations locales simulées |
| `scripts/remote/` | 69 | PASS | déploiement/rollback/SSH simulés, sans réseau distant |
| contrats non matériels ciblés | 5 | PASS | pairabilité simulée et garde-fous textuels GATT |
| **Total logiciel** | **188** | **PASS** | aucune interaction matérielle |
| diagnostics matériels | 7 | NON EXÉCUTÉS | exclus intentionnellement |

Les 7 exclusions sont : les 3 tests de `scripts.bluetooth.test_diagnostics`,
qui lancent les diagnostics radio Windows, et les 4
`TargetDiagnosticTests` de `scripts.diagnostics.test_inspect_monordinateur`,
qui lancent l'inspection cible/session. Les 3 `GattProbeSafetyTests` purement
textuels sont inclus dans les 5 contrats non matériels.

## Build et analyse statique

- 21 scripts PowerShell analysés : 0 erreur de syntaxe.
- `PositionAgent.exe` compilé en temporaire : 28 672 octets,
  SHA-256 `4257859BAF6A6AD280AE7125D8AE93996E6355CC7DA718525F26F37BCF9E9318`.
- `PairingTool.exe` compilé en temporaire : 14 336 octets,
  SHA-256 `F2709DAF120C92FD40B560DF40016BC55974D9FA8686AE4A72E58BE4A6DF7F04`.
- `MouseWitness.exe` compilé en temporaire : 7 680 octets,
  SHA-256 `D031585DF0CA1BE290C9996FBB742B754C15A021535613D75C917A276E61A7BF`.
- Répertoire de build temporaire supprimé après vérification ; aucun artefact
  construit n'est livré ni activé.

## Contrats publics à préserver

- API loopback authentifiée, enveloppe avec TTL et anti-rejeu ;
- TLS/HMAC et séquences monotones pour le retour de position/capture ;
- DPAPI pour les secrets de configuration ;
- HOGP et descripteur actuellement appairé inchangés ;
- états d'action, journal et registre `.ids` conservés ensemble ;
- cible passive : aucun mécanisme d'injection de souris dans `PositionAgent` ;
- identifiant accepté non rejoué pendant la fenêtre contractuelle de 30 jours ;
- arrêt d'urgence prioritaire et absence de rapport après arrêt comme propriété
  cible, avec réserves R1 documentées dans la matrice.
