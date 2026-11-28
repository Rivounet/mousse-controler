# Mousse-controler

Mousse-controler pilote la souris d'un **PC cible Windows** depuis
**mini-pc-backend** par Bluetooth LE HID (HOGP). Un agent Windows visible sur
la cible publie la position réelle et les captures explicitement demandées par
un canal LAN HTTPS/HMAC sortant ; il ne reçoit aucune commande souris.

## État courant — 28 novembre 2026

- Base de fusion actuelle : `origin/main` au commit
  `6b6de0caf2c354b9855922439c6449b272246161` (PR #41). La branche de correction
  HOGP native reste distincte tant que sa qualification et sa revue ne sont pas
  terminées.
- Les preuves matérielles réalisées avec `MonOrdinateur` sont historiques et ne
  qualifient pas la nouvelle cible `DESKTOP-NPIHO8K`.
- L'audit du 27 novembre a constaté que la tâche contrôleur exécutait un
  worktree modifié, donc non reproductible par un SHA. Ce runtime a depuis été
  remplacé par une release immuable vérifiée ; les preuves sont publiées dans
  la PR #27.
- La convergence introduit une couche applicative, un coordinateur exclusif des
  opérations, un feedback atomique et des releases contrôleur immuables. La
  correction en cours sépare en plus télémétrie, propriété HID Windows et plan
  de contrôle PnP. Qualification, activation et publication restent trois
  décisions et preuves distinctes.
- Aucun GitHub Actions ni service CI externe. La qualification officielle reste
  locale sous Windows.
- La qualification like-prod emploie une instance HOGP, une configuration et des
  tâches dédiées. La production `mini-pc-backend` reste préservée et une release
  active plus ancienne que `main` n'est jamais assimilée au SHA à qualifier.

L'état détaillé, les commits de fusion, la matrice C-01 à C-17 et les réserves
sont centralisés dans [Robustesse R0–R6](docs/ROBUSTESSE.md).

## Architecture en bref

```text
mini-pc-backend : API → service applicatif → coordinateur exclusif
                         ├─ actions/séquences → contrôleur → HOGP BLE
                         └─ requêtes d'état ← feedback position/topologie atomique
                                                                    │
PC cible Windows : pile HID Windows native ←────────────────────────┘
       agent visible : position/capture → HTTPS + HMAC → mini-pc-backend
       runtime contrôle HOGP : état Bluetooth/PnP → HTTPS + HMAC → backend
```

Le « runtime contrôle HOGP » est `HogpControlAgent.exe`, code applicatif
qualificatif déployé sur la cible. Il est distinct de PositionAgent et de tout
agent Codex : il ne transporte aucune commande souris, n'ouvre aucune session
GATT et ne peut exécuter que les reprises PnP explicitement autorisées et liées
aux identités enrôlées.

Le moteur HOGP actif est PowerShell/WinRT dans un MSIX. Les sources C++ HOGP
sont historiques et conservées faute de preuve d'absence totale d'usage. Le
descripteur actuel expose cinq boutons et une roulette verticale ; la roulette
horizontale n'est pas disponible.

Chaque émission HOGP exige exactement un abonné actif dont l'identité WinRT
hachée correspond à la configuration ; l'envoi utilise la notification ciblée,
jamais une diffusion à tous les abonnés. L'identité brute n'est pas journalisée.

## Qualification officielle

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

Les profils fermés `software`, `build` et `full-local` ne déclenchent ni HID,
ni capture réelle, ni accès distant, ni installation ou déploiement. Les sept
diagnostics matériels sont séparés et exigent une autorisation explicite.
Une qualification matérielle exige en plus deux baux frais portant le même
`run_id` et le même SHA : rôle `backend` sur `mini-pc-backend`, rôle `target`
sur la cible, avec désignation croisée des deux machines.

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
