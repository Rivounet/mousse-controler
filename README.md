# Mousse-controler

Mousse-controler pilote la souris de **MonOrdinateur** depuis
**mini-pc-backend** par Bluetooth LE HID (HOGP). Un agent Windows visible sur
la cible publie la position réelle et les captures explicitement demandées par
un canal LAN HTTPS/HMAC sortant ; il ne reçoit aucune commande souris.

## État courant vérifié — 27 novembre 2026

- Référence locale `origin/main` : `ff94a765da0a6f0f01276366662eed180e8fad61`.
- La validation fonctionnelle de la PR #26 reste la dernière preuve matérielle
  publiée ; aucune nouvelle action HID ou capture n'est incluse dans le chantier
  d'architecture.
- L'audit du 27 novembre a constaté que la tâche contrôleur exécutait un
  worktree modifié, donc non reproductible par un SHA. Ce runtime reste actif
  mais n'est plus considéré comme une release qualifiée.
- Le chantier `MC-ARCHITECTURE-CONVERGENCE-001` introduit une couche
  applicative, un coordinateur exclusif des opérations, un feedback atomique et
  des releases contrôleur immuables. Son activation reste distincte de sa
  qualification et de sa publication.
- Aucun GitHub Actions ni service CI externe. La qualification officielle reste
  locale sous Windows.

L'état détaillé, les commits de fusion, la matrice C-01 à C-17 et les réserves
sont centralisés dans [Robustesse R0–R6](docs/ROBUSTESSE.md).

## Architecture en bref

```text
mini-pc-backend : API → service applicatif → coordinateur exclusif
                         ├─ actions/séquences → contrôleur → HOGP BLE
                         └─ requêtes d'état ← feedback position/topologie atomique
                                                                    │
MonOrdinateur : pile HID Windows native ←───────────────────────────┘
       agent visible : position/capture → HTTPS + HMAC → mini-pc-backend
```

Le moteur HOGP actif est PowerShell/WinRT dans un MSIX. Les sources C++ HOGP
sont historiques et conservées faute de preuve d'absence totale d'usage. Le
descripteur actuel expose cinq boutons et une roulette verticale ; la roulette
horizontale n'est pas disponible.

## Qualification officielle

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

Les profils fermés `software`, `build` et `full-local` ne déclenchent ni HID,
ni capture réelle, ni accès distant, ni installation ou déploiement. Les sept
diagnostics matériels sont séparés et exigent une autorisation explicite.

## Documentation

- [État de robustesse et matrice des constats](docs/ROBUSTESSE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Décisions](docs/DECISIONS.md)
- [Planning](docs/PLANNING.md)
- [Roadmap](docs/ROADMAP.md)
- [Reprise](docs/REPRISE.md)
- [Tests](docs/TESTS.md)
- [Référence API générée](docs/API-REFERENCE.md)

Les rapports historiques et audits restent les preuves détaillées. Les mandats
complets restent dans le chat. Une fusion, une synchronisation des machines ou
un déploiement nécessitent toujours une décision explicite.
