# Reprise — Mousse-controler

**Dernière vérification documentaire : 21 novembre 2026.**

## Références GitHub vérifiées

- `main` : `0817823eb2e7a5e8d477ed3e382ef128611fd5b9`.
- PR #10 et #12–#18 : fusionnées.
- PR #11 : ouverte, Draft, non fusionnée, tête
  `42adb2976edac4048cfc2150ce247dc7c2951a74`.
- R0–R5 : PR #13 à #18, commits et qualifications détaillés dans
  [ROBUSTESSE.md](ROBUSTESSE.md).

Une PR fusionnée ne prouve ni la synchronisation d'un clone ni la version d'un
processus en cours.

## État des machines pendant R6

| Élément | État vérifié |
|---|---|
| GitHub `main` | `0817823eb2e7a5e8d477ed3e382ef128611fd5b9` |
| Clone local mini-PC | Non vérifié pendant R6 |
| Contrôleur Python en exécution | Version non vérifiée pendant R6 |
| MSIX HOGP installé | Version non vérifiée pendant R6 |
| PositionAgent installé | Version non vérifiée pendant R6 |
| Synchronisation R0–R5 | Non effectuée dans ces lots |
| Qualification matérielle post-correctifs | Non effectuée |

Ne pas remplacer ces inconnues par les derniers états matériels historiques.
MC-HID-EXEC-001 et MC-MOUSE-ACTIONS-001 ont démontré antérieurement le HOGP,
l'appairage, les fonctions souris, les captures autorisées et la reprise, avec
leurs réserves propres ; ils ne prouvent pas que les binaires actuellement
installés correspondent à `main`.

## Reprise sûre

1. Vérifier l'identité de l'hôte et l'état Git sans mutation.
2. Comparer les SHA local, GitHub et artefacts/processus installés.
3. Lire [ROBUSTESSE.md](ROBUSTESSE.md), [DECISIONS.md](DECISIONS.md) et les
   rapports du lot concerné.
4. Pour du logiciel seulement, utiliser les profils locaux décrits dans
   [TESTS.md](TESTS.md).
5. Avant toute opération cible, obtenir l'autorisation requise, annoncer la
   prise de souris/capture éventuelle et préparer le rollback.

## Réserves à conserver

- correctifs R1–R5 non requalifiés matériellement et sept diagnostics exclus ;
- libération physique des boutons potentiellement incertaine après défaillance ;
- annulation WinRT best-effort et récupération limitée après panne ;
- quota capture non atomique entre processus indépendants ;
- aucune garantie de reproductibilité binaire bit-à-bit ;
- roulette horizontale absente du descripteur actuel ;
- mesure LAN aller simple absolue indisponible sans horloges synchronisées ;
- reprise GATT transitoire possible avant retour à l'état abonné.

## Prochaine action

La PR R6 doit rester Draft jusqu'à revue. Aucun chantier applicatif,
déploiement, synchronisation ou essai matériel ne découle automatiquement de
cette clôture documentaire.
