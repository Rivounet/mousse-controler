# Écarts et risques

| ID | Niveau | Écart / preuve | Conséquence possible | Action ultérieure envisageable | Autorisation nécessaire |
|---|---|---|---|---|---|
| E-01 | `MAJOR` | clone `34b2612…` contre GitHub `440ab39…` | code local incomplet par rapport à R0–R6 | décider d'une synchronisation contrôlée après sauvegarde | mandat de synchronisation Git |
| E-02 | `MAJOR` | état `active.json` sur `c23dab3…`, release témoin historique et aucun processus associé | état de contrôle obsolète ou trompeur | inventorier le rôle de cet état puis préparer une activation propre | mandat d'exploitation |
| E-03 | `MAJOR` | `controller.json` pointe vers le moteur C++ historique | prochain démarrage potentiel sur un transport différent du chemin officiel | migrer la configuration vers l'artefact approuvé après vérification | mandat de déploiement/configuration |
| E-04 | `MAJOR` | aucun journal anti-rejeu, registre `.ids` ou index capture trouvé dans les emplacements opérationnels | sûreté de reprise non démontrée si le runtime était relancé | identifier les chemins réels ou initialiser via procédure officielle | mandat d'inspection étendue puis déploiement |
| E-05 | `MINOR` | plusieurs builds anciens restent dans `source/out` | confusion possible entre artefact présent et installé | établir un manifeste d'artefacts approuvés | mandat documentaire/exploitation |
| E-06 | `INFORMATIONAL` | MSIX et tâches non lisibles sans droits supplémentaires | version/activation inconnues | inspection passive avec contexte déjà autorisé | approbation distincte si requise |
| E-07 | `INFORMATIONAL` | `MonOrdinateur` inaccessible dans la sandbox | état PositionAgent et récupération inconnus | refaire l'audit via canal approuvé hors sandbox | nouvelle autorisation d'accès |
| E-08 | `INFORMATIONAL` | journal disponible ancien ; échec d'activation restauré le 19 novembre, aucune trace récente | aucune preuve récente de fonctionnement ou d'erreur persistante | définir une collecte passive autorisée | mandat distinct si nécessaire |

## Synthèse

- Risques `CRITICAL` : **0**.
- Risques `MAJOR` : **4**.
- Risques `MINOR` : **1**.
- Informations manquantes/historiques : **3**.

Aucun écart n'a été corrigé. La priorité recommandée est d'obtenir une
inspection complète autorisée, puis de décider séparément de la synchronisation
et de l'activation. Aucun essai fonctionnel ne doit précéder cette décision.

