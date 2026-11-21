# MC-ROBUSTNESS-R4-001 — Rapport de qualification locale

## Verdict

**PASS** pour le code du commit qualifié
`72546bdd22ccbd269cacf112ffb3a82d30d38b64`.

Le profil `full-local` a terminé en **131,750 s** avec 269/269 tests
logiciels réussis, les quatre contrôles de build réussis et sept diagnostics
matériels exclus. Aucun accès Bluetooth, HID, capture, SSH, installation,
déploiement ou accès à `MonOrdinateur` n'a eu lieu.

## Environnement qualifié

| Élément | Version |
|---|---|
| Windows | Windows 11, noyau `10.0.26300` x64 |
| Python | 3.12.10 ; minimum du profil `>=3.12` |
| PowerShell | 7.6.9 pour l'orchestration/build |
| Windows PowerShell | 5.1.26100.10068 pour l'analyse syntaxique |
| Git | 2.54.0.windows.1 |
| Roslyn C# | 4.14.0-3.26424.7 (`a528c90a`) |
| Windows SDK | 10.0.26100.0, découvert localement |

Les dépendances Python applicatives sont limitées à la bibliothèque standard.
La suite exécute les imports nécessaires. La version Python 3.12 déjà retenue
par les procédures du projet est vérifiée explicitement par l'orchestrateur.

## Profils

| Profil | Contenu | Opérations exclues par construction |
|---|---|---|
| `software` | Suite R0 à R4, intégration simulée, loopback, sécurité, anti-rejeu, mise à jour/rollback simulés | matériel, capture réelle, SSH, installation, déploiement |
| `build` | compilation Python, contrôle de la référence API, parse PowerShell, compilation PositionAgent | exécution des scripts analysés, installation et activation des artefacts |
| `full-local` | `software` puis `build` | mêmes exclusions ; reste strictement local |
| diagnostics matériels | scripts existants, hors orchestrateur R4 | jamais lancé par les trois profils locaux |

Commandes depuis la racine :

```powershell
python -B scripts/qualification/qualify.py --profile software
python -B scripts/qualification/qualify.py --profile build
python -B scripts/qualification/qualify.py --profile full-local
```

Chaque exécution conserve un `summary.json` et un log par phase sous
`out/qualification/<horodatage UTC>/`. Une phase échouée renvoie 1 ; un outil
obligatoire manquant ou une interruption renvoie un verdict non favorable et
une sortie non nulle. Les temporaires sont supprimés, les logs et artefacts de
qualification sont conservés sans être installés.

## Résultats

| Phase finale | Résultat | Durée |
|---|---:|---:|
| Tests logiciels | PASS, 269/269 | 125,219 s |
| Compilation Python | PASS | 0,922 s |
| Référence API `--check` | PASS | 0,547 s |
| Parse de 22 scripts PowerShell | PASS | 0,890 s |
| Build PositionAgent | PASS | 2,235 s |
| Total `full-local` | **PASS** | **131,750 s** |

Le binaire `PositionAgent.exe` produit mesure 28 672 octets et porte le
SHA-256 `072437c98910b0f0736c961d75689623e0c724ac61d000609d422a896aacffa4`.
Il n'a pas été installé. La qualification ne prétend pas que deux builds sont
identiques bit à bit ; l'empreinte décrit uniquement l'artefact de cette
exécution.

## Statuts indépendants

| Statut | État R4 |
|---|---|
| Code développé | Oui, sur branche dédiée |
| Tests logiciels réussis | Oui, sur `72546bd…` |
| Build qualifié | Oui, localement et sans installation |
| PR fusionnée | Non |
| Code synchronisé sur les machines | Non vérifié, non revendiqué |
| Déploiement effectué | Non |
| Qualification matérielle réalisée | Non ; explicitement exclue de R4 |

## Réserves

- Les sept diagnostics de radio et de session cible restent matériels et ne
  sont pas retestés.
- Un délai de démarrage de processus trop court était réutilisé par un test de
  timeout de commande. Deux exécutions `full-local` ont correctement échoué et
  rendu ce défaut visible. Le test de démarrage conserve son budget strict de
  300 ms ; les tests de commande disposent désormais d'un budget de création de
  processus distinct de 1,5 s. Aucun délai applicatif n'a été modifié.
- Le résultat couvre l'environnement Windows décrit, pas toutes les versions de
  Visual Studio ou du SDK Windows.
- Aucun workflow GitHub Actions, runner hébergé ou service CI externe n'est
  créé. GitHub conserve uniquement la branche, la PR et ces preuves expurgées.

## Conclusion

C-10 est traité par des profils fermés, des exclusions observables et des tests
de sûreté de l'orchestrateur. C-15 est traité par la découverte contrôlée de
Roslyn, du SDK Windows, des contrats WinRT et des outils MSIX. La production
reste inchangée.

