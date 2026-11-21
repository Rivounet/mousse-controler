# Mousse-controler

Mousse-controler pilote la souris de **MonOrdinateur** depuis
**mini-pc-backend** par Bluetooth LE HID (HOGP). Un agent Windows visible sur
la cible publie la position réelle et les captures explicitement demandées par
un canal LAN HTTPS/HMAC sortant ; il ne reçoit aucune commande souris.

## État courant vérifié — 21 novembre 2026

- GitHub `main` : `0817823eb2e7a5e8d477ed3e382ef128611fd5b9`.
- Programme de robustesse R0–R5 : fusionné par les PR #13 à #18.
- R5 était ciblé : C-13 et C-14 sont corrigés ; C-09, C-11, C-12 et C-17
  restent différés, sans priorité automatique.
- PR #11 : audit indépendant toujours ouvert en Draft et non fusionné.
- Qualification locale finale R5 : `full-local` PASS, 271/271 tests sur le SHA
  final de branche `8c15c82f69371eb395aa0d760bbaee41a7c1e1a8`.
- Aucun GitHub Actions ni service CI externe. La qualification officielle est
  locale sous Windows.
- Les correctifs R1–R5 n'ont pas été requalifiés matériellement. La version du
  clone et des processus installés n'a pas été vérifiée pendant R6.

L'état détaillé, les commits de fusion, la matrice C-01 à C-17 et les réserves
sont centralisés dans [Robustesse R0–R6](docs/ROBUSTESSE.md).

## Architecture en bref

```text
mini-pc-backend : API → actions/séquences → contrôle de position → HOGP BLE
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
