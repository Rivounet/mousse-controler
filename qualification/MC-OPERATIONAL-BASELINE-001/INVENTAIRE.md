# Inventaire opérationnel

## GitHub

| Élément | Observation |
|---|---|
| Dépôt | `Rivounet/mousse-controler` |
| Branche officielle | `main` |
| SHA | `440ab39a042ddd5254cc93a75e2d91123b362b4a` |
| Origine | fusion de la PR #19 |

## mini-pc-backend

| Élément | Observation passive |
|---|---|
| Système | Windows 26H2, build 26300.10075, AMD64 |
| Matériel déclaré | Intel Jasper Lake Client Platform |
| Clone | `C:\Projets\Mousse-controler\source` |
| Branche / HEAD | `feat/mc-api-catalog-001` / `34b2612…` |
| Arbre | propre |
| `origin/main` local | `0817823…`, non actualisé pendant l'audit |
| Python | 3.12.10 |
| PowerShell | 7.6.9 ; Windows PowerShell 5.1.26100.10068 |
| Processus correspondants | aucun visible |
| Registre de processus | 0 entrée |
| État d'activation | `stable`, Git SHA historique `c23dab3…`, aucun processus associé |
| Tâches planifiées | `BLOCKED` par les droits/CIM du contexte |
| MSIX HOGP | alias présent ; métadonnées installées `BLOCKED` |
| Bluetooth | adaptateur et entrée `MONORDINATEUR` présents passivement ; état radio non affirmé |
| États anti-rejeu/capture | aucun candidat trouvé sous `state/` et `runtime/` |
| Journaux | un journal ancien, dernière écriture le 19 novembre 2026 |

### Artefacts accessibles

| Artefact | Taille | SHA-256 | Interprétation |
|---|---:|---|---|
| `source/out/Release/mousse-hogp.exe` | 51 576 | `B87D433501F51608298542237E0DED7F331137C7E2741EEA9E5E64CB967C27FF` | moteur C++ historique référencé par la configuration |
| `source/out/HogpPackage/MousseControler.Hogp.msix` | 190 501 | `907AFB9E458C7DA5C2B5555581065A310CD8EBC39BC9BB5EAE2CA508A0B12042` | paquet source présent, installation non prouvée |
| `source/out/PositionAgent/PositionAgent.exe` | 22 016 | `C19B14127CBE1504C74DC53C653494471D2E6827E79D2557A68541D866DC1071` | ancien build local, non prouvé installé |
| `source/out/PositionAgent-MC-MOUSE-ACTIONS-001/PositionAgent.exe` | 28 672 | `9877A601C5FC53F54612324277B14FC9785E68A4217C4FB044329200E74DF0EF` | build local plus récent, non prouvé installé |

Le répertoire `runtime/MC-HID-EXEC-001` contient uniquement des configurations
et secrets protégés ; aucun exécutable n'y a été observé. Les secrets et valeurs
réseau n'ont pas été lus ni publiés.

## MonOrdinateur

| Élément demandé | État |
|---|---|
| Version Windows | `BLOCKED` |
| PositionAgent chemin/version/SHA | `BLOCKED` |
| Tâche planifiée | `BLOCKED` |
| Processus et session | `BLOCKED` |
| Configuration | `BLOCKED` |
| Installation et sauvegardes | `BLOCKED` |
| `RECOVERY_REQUIRED` | `BLOCKED` |

Le canal exact documenté a été tenté en lecture seule avec `whoami`. La sandbox
a refusé la connexion. Aucune approbation supplémentaire n'a été demandée.

