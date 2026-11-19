# Roadmap — jalons sans échéances fixes

**Pilotage : par livrables et preuves**, sans dates calendaires ni estimation obligatoire. Un jalon n'est validé qu'après examen des résultats, non à la seule livraison du code.

| Jalon | Finalité | Livrable attendu | Critère de sortie | État |
|---|---|---|---|---|
| J0 — Cadrage | Source de vérité commune | README, architecture, planning, tests, déploiement, décisions, consignes Codex | Documents cohérents et publiés | En cours |
| J1 — Environnement | Fiabiliser le cycle PC Windows → mini-pc-backend | Inventaire contrôlé, accès distant sécurisé et premier transfert réversible | Exécution et collecte de logs démontrées sur mini-PC | À faire |
| J2 — Faisabilité HID | Déterminer une voie Bluetooth native viable | Rapport matériel/OS et prototype HID minimal | PC Windows reconnaît une souris Bluetooth issue du mini-PC, avec événement de test | À faire |
| J3 — API fonctionnelle | Transformer des commandes API en événements souris | API locale + moteur de commandes + adaptateur HID | Mouvements, clics et défilement testés de bout en bout | À faire |
| J4 — Exploitation | Rendre le déploiement reproductible et sûr | Scripts d'installation, lancement, arrêt et retour arrière | Déploiement, reprise et collecte des preuves reproductibles | À faire |
| J5 — MVP qualifié | Vérifier comportement, robustesse et sécurité | Batterie de tests, rapport de qualification, limites résiduelles | Revue indépendante du code et des preuves ; arbitrage explicite | À faire |

## Dépendances et points de décision

- **J1 avant essais réels** : ne pas modifier un environnement distant sans diagnostic, sauvegarde adaptée et moyen de retour arrière.
- **J2 est un jalon de décision GO / NO-GO** : si le contrôleur intégré ne permet pas le rôle périphérique Bluetooth HID, comparer une voie logicielle alternative ou un module HID externe (ex. ESP32), sans achat automatique.
- **J3 dépend de J2**, mais l'API peut être maquettée et testée indépendamment grâce à un adaptateur simulé.
- **J4 commence techniquement dès J1** (transfert/diagnostic) ; il est finalisé après intégration de l'API.
- **J5** n'est pas une mise en production automatique.

## Règle d'évolution

Toute modification de périmètre, de jalon ou de critère de sortie est documentée dans [DECISIONS.md](DECISIONS.md), puis reflétée ici et dans [PLANNING.md](PLANNING.md). Aucun jalon validé par simple déclaration non accompagnée de preuves.

**Responsabilités :** Codex réalise, documente les tests et propose les changements ; ChatGPT tient cette roadmap à jour, procède à la revue de code et examine les preuves ; l'utilisateur arbitre les décisions engageantes.
