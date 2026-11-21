# Tâches Windows, configuration et persistances

## Tâche mini-PC

La définition statique de `MousseControler-HOGP` est lisible et vérifiée :

| Élément | Observation |
|---|---|
| Présence | oui, fichier de tâche SHA-256 `6518E5AD…C77527A` |
| Activée | oui |
| Déclencheur | ouverture de session interactive |
| Principal | compte distinct du jeton Codex, privilège minimal |
| Instances | `IgnoreNew` |
| Redémarrage | 5 essais, intervalle 1 minute |
| Exécutable | Windows PowerShell non interactif |
| Code chargé | clone historique `source`, SHA Git `34b2612…` |
| Configuration | `ProgramData/MousseControler/controller.json` |
| Python | 3.12.10 |

Le script lanceur du clone historique est identique à celui du SHA officiel,
mais le runtime Python serait chargé depuis l'ancien clone. La future
réinscription de la tâche doit donc viser le worktree qualifié.

Le service Task Scheduler est installé et configuré en démarrage automatique.
Son état courant, celui de la tâche, sa dernière exécution et son dernier
résultat restent inconnus : le jeton Codex n'est pas le principal de la tâche,
et la sandbox refuse SC, COM, CIM, TaskCache, les événements et `schtasks`.
Une requête passive depuis la session ordinaire du propriétaire de la tâche est
l'autorisation minimale recommandée ; aucune élévation n'est présumée requise.

## Configuration réellement utilisée

La configuration `ProgramData` utilise déjà l'alias MSIX PowerShell/WinRT. Elle
contient les secrets DPAPI et références TLS valides, mais laisse les chemins
modernes à leurs valeurs par défaut.

| Persistance | État |
|---|---|
| journal actions | présent, 109 710 octets |
| registre `.ids` | présent, 8 329 octets |
| index captures | présent, 26 octets |
| PNG conservés | 0 |
| droits du principal de tâche | lecture et modification confirmées |

Une sauvegarde complémentaire contient configuration, journal, `.ids`, index,
autres fichiers ciblés et définition de tâche : 7 fichiers, 127 543 octets,
0 divergence, manifeste SHA-256
`8A64B08802EC75593D9EDB098373ECDE59B6F0387279BDD81470E1B8FA0F71FA`.

La configuration proposée explicite ces chemins et leurs limites sans changer
les secrets. JSON, alias, fichiers TLS, DPAPI, ACL et persistances : **PASS**.
La configuration active n'a pas été remplacée.
