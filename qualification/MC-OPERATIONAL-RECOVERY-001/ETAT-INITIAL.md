# État initial

| Élément | Observation avant modification |
|---|---|
| GitHub `main` | `a2c25423faebecee4fa882d36e982d1d93c7e425` |
| Clone opérationnel | branche `feat/mc-api-catalog-001`, SHA `34b2612bef260db382251601c103886dd76dd12a` |
| Arbre du clone | propre |
| `origin/main` local | `0817823eb2e7a5e8d477ed3e382ef128611fd5b9` |
| Processus applicatifs visibles | aucun |
| Configuration contrôleur | moteur C++ historique |
| MSIX installé | PowerShell/WinRT 1.0.0.2, signé et vérifié lors de la baseline 002 |
| Persistances modernes attendues | journal, `.ids`, index et captures absents |
| Tâches planifiées | `BLOCKED` dans le contexte de sécurité disponible |
| PositionAgent cible | `BLOCKED` depuis la sandbox |

Les répertoires `runtime`, `state`, `logs`, `releases`, `staging` et
`source/out` ont été inventoriés avant toute écriture. Aucun processus Mousse,
HOGP, PositionAgent ou Python applicatif n'était visible.

La récupération Git a ensuite actualisé uniquement les références distantes.
Le clone opérationnel n'a subi ni checkout, ni reset, ni changement de branche.
