# Matrice des capacités qualifiées

| Capacité | Contexte réel | Preuve | Limite |
|---|---|---|---|
| Git, fichiers du worktree | Sandbox | `check-environment` PASS | Écriture hors racines refusée |
| Python, PowerShell, builds | Sandbox | 279 tests logiciels et build local | Les fournisseurs système peuvent être masqués |
| Réseau général | Sandbox | Refus observé | Aucune permission générale ajoutée |
| SSH `MonOrdinateur` | Hors sandbox, commande exacte | PASS puis réutilisation PASS | Session SSH = session 0, pas une preuve d'affichage |
| Tâche locale | Hors sandbox, inspecteur exact | Deux PASS | Lecture seule, aucun démarrage ou ACL |
| Processus locaux | Même inspecteur | Aucun runtime actif observé | Visibilité dépend du jeton courant |
| Tâche/processus distants | Canal SSH exact | Tâche et hash du processus concordants | Aucune action interactive |
| Clé MSIX | Profil utilisateur hors sandbox | Create, Create idempotent, Restore PASS | DPAPI est lié au compte et à la machine |
| Signature MSIX | Artefact isolé sous `out/` | Signature embarquée et identité concordantes | Nouvelle racine non approuvée |
| Installation/déploiement | Non autorisé | Préconditions seulement | Autorisation séparée obligatoire |
| HID/capture | Exclus | Aucun appel | Mandat interactif explicite obligatoire |

## Interprétation des restrictions

La configuration utilisateur exprime une préférence de sandbox élevée,
mais le profil effectif de Codex Desktop reste la source de vérité : réseau
restreint, écriture bornée au workspace et fournisseurs COM/CIM partiellement
masqués. Un refus dans ce contexte n'est donc pas un refus Windows. Inversement,
une connexion SSH réussie suivie d'un refus Windows désignerait le jeton, la
session ou une ACL de la cible; les procédures ne compensent jamais ce cas par
une élévation.
