# Inventaire R5

## HOGP — matrice de dépendances

| Composant | Rôle observé | Consommateurs prouvés | Classement | Décision |
|---|---|---|---|---|
| `src/hogp-powershell/hogp.ps1` | serveur GATT/HOGP WinRT en stdio | `Build-HogpPackage.ps1`, MSIX actif, tests transport | Actif | Conserver sans modification |
| `packaging/hogp/AppxManifest.xml` | identité MSIX, alias `mousse-hogp-packaged.exe`, capacité Bluetooth | build MSIX actif | Actif | Conserver sans modification |
| `scripts/build/Build-HogpPackage.ps1` | fabrique le MSIX depuis PowerShell et le manifeste | profil/build et procédures | Actif | Conserver |
| `src/mousse_controler/transport.py` | lance et borne l'alias MSIX | runtime, tests R0/R2 | Actif | Conserver |
| `src/hogp/main.cpp` + projet VCX | ancienne implémentation WinRT native | aucun build, package ou test actif trouvé | Historique ; usage manuel incertain | Conserver avec réserve |
| `src/hogp-launcher/main.cpp` + projet VCX | lance l'alias packagé | aucune référence de build active trouvée | Historique/diagnostic incertain | Conserver avec réserve |
| documents HOGP historiques | preuves et procédures passées | traçabilité | Historique | Intacts |

Les recherches couvrent les sources, scripts, tests, packaging et documents.
L'absence de référence automatisée ne prouve pas l'absence d'un consommateur
manuel ; aucune suppression ou archive n'est donc réalisée.

## Séquenceurs

| Moteur | Responsabilité | État/contrôle | Consommateurs |
|---|---|---|---|
| `SequenceRunner` | zones, trajectoires, arrivée mesurée, attente entre cibles | `SequenceState`, pause/reprise/skip/stop | commandes historiques de séquence |
| `ActionExecutor` | primitives souris, séquences d'actions, retry, captures, journal et anti-rejeu | `ActionState`, pause/reprise/cancel/continue/stop | API d'actions moderne |

Les recouvrements sont la pause, la reprise, l'attente interruptible et l'arrêt.
Les unités de travail, états publics, persistance et garanties d'échec diffèrent.
Une convergence immédiate déplacerait la complexité et risquerait R1 ; aucun
troisième moteur ni fusion n'est introduit.

## Responsabilités concentrées

- `actions.py` : registre persistant, événements, contrôle de file, exécution,
  captures, politique d'erreur et validation sémantique.
- `PositionAgent.cs` : topologie/curseur, client HTTPS/HMAC/TLS, capture,
  surveillance de reconnexion HOGP et cycle de vie du processus.
- persistance actions et captures : contrats, index et récupérations différents ;
  aucune fusion proposée.
- utilitaires PowerShell : répétitions techniques dispersées, mais leurs
  privilèges, cibles et transactions diffèrent ; aucune primitive extraite.
