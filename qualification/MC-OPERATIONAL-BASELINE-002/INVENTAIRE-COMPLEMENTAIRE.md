# Inventaire complémentaire

## Préconditions

| Élément | Observation |
|---|---|
| GitHub `main` | `fe4def1dd6f5a895a81ec60e52b480bb5fbc9421` |
| Clone mini-PC | `feat/mc-api-catalog-001` / `34b2612bef260db382251601c103886dd76dd12a` |
| Arbre Git | propre |
| `origin/main` local | `0817823eb2e7a5e8d477ed3e382ef128611fd5b9` |
| Contexte | Windows, session 4, jeton non administrateur |
| Processus applicatifs correspondants | aucun visible par `Get-Process` |

## Tâches planifiées

| Méthode passive | Résultat |
|---|---|
| `Get-ScheduledTask` | `BLOCKED`, ressource CIM indisponible |
| `schtasks /Query` | `BLOCKED`, requête refusée dans le contexte |
| COM `Schedule.Service` | `BLOCKED`, accès refusé |
| registre `TaskCache` | `BLOCKED`, accès registre refusé |

Les contrats sources mentionnent notamment la tâche mini-PC
`MousseControler-HOGP`, interactive et déclenchée à l'ouverture de session, et
des tâches PositionAgent côté cible. Ce sont des noms attendus, pas des tâches
observées. Aucune tâche n'a été démarrée.

## MSIX HOGP installé

| Élément | Observation vérifiée |
|---|---|
| Identité | `Rivounet.MousseControler.Hogp` |
| Version | `1.0.0.2` |
| Éditeur | `CN=MousseControler` |
| État | entrée AppModel utilisateur et répertoire WindowsApps présents |
| Manifeste | `AppxManifest.xml`, SHA-256 `7957EAC971A387D61B256F14E7D5FD1FABE23D46FB61FDF361754C1B96F44245` |
| Alias | `mousse-hogp-packaged.exe` |
| Exécutable déclaré | `powershell.exe`, SHA-256 `D8F182560210D43BAAF767D482AD1DC1207372522E91413B9D5E515A875E552D` |
| Script installé | `hogp.ps1`, SHA-256 `488E7053819C94CFDDB0E9C92A4678A198456BF345AFB5C17C609DF000E8E572` |
| MSIX local correspondant | 190 501 octets, SHA-256 `907AFB9E458C7DA5C2B5555581065A310CD8EBC39BC9BB5EAE2CA508A0B12042` |

Les trois empreintes internes du MSIX local correspondent aux trois fichiers
installés. Cette concordance ne prouve pas que le package est actif.

## Persistance mini-PC

| Élément | Chemin attendu ou observé | État |
|---|---|---|
| Journal actions | `runtime/MC-HID-EXEC-001/action-journal.jsonl` par défaut | absent |
| Registre durable | `runtime/MC-HID-EXEC-001/action-journal.jsonl.ids` | absent |
| Répertoire captures | `runtime/MC-HID-EXEC-001/captures/` par défaut | absent |
| Index captures | `runtime/MC-HID-EXEC-001/captures/.capture-index.json` | absent |
| Images conservées | sous le répertoire captures configuré | aucune trouvée |
| État d'activation | `state/active.json` | présent, `stable`, SHA historique `c23dab3…`, aucun processus |
| Registre processus | `state/process-registry.json` | présent, vide |
| État récupération | phase `recovery_required` ou marqueur `RECOVERY_REQUIRED` | non trouvé dans les racines ciblées |
| Releases précédentes | `releases/` | trois répertoires historiques présents |

Le journal d'actions et son fichier `.ids` doivent être sauvegardés et restaurés
ensemble. L'index et les images relèvent du quota et de la rétention configurés.
Leur absence est cohérente avec un runtime moderne jamais lancé avec cette
configuration, mais la cause n'est pas démontrée.

## Configuration contrôleur

- fichier observé : `runtime/MC-HID-EXEC-001/controller.json` ;
- transport configuré : `source/out/Release/mousse-hogp.exe`, moteur C++
  historique ;
- aucune clé `action_journal` ou `capture_directory` : les chemins par défaut
  ci-dessus s'appliqueraient au code actuel ;
- paramètres réseau et secrets présents mais volontairement expurgés ;
- mécanisme de rollback général observé dans `state/active.json` et
  `releases/`, sans preuve d'un runtime applicatif actif.

## MonOrdinateur

Le canal exact documenté a été tenté avec une commande passive. La sandbox a
refusé la connexion. Version Windows, PositionAgent, tâche, processus, session,
sauvegarde et `RECOVERY_REQUIRED` restent `BLOCKED`. Aucune élévation n'a été
demandée.


