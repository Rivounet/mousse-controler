# Roadmap — jalons sans échéances fixes

**Pilotage : par livrables et preuves**, sans dates calendaires ni estimation obligatoire. Un jalon n'est validé qu'après examen des résultats, non à la seule livraison du code.

| Jalon | Finalité | Livrable attendu | Critère de sortie | État |
|---|---|---|---|---|
| J0 — Cadrage | Source de vérité commune | README, architecture, planning, tests, déploiement, décisions, consignes Codex | Documents cohérents et publiés | Validé |
| J1 — Environnement local | Qualifier mini-pc-backend comme machine de développement et d'exécution | Inventaire contrôlé, clone séparé des releases, tests reproductibles | OS/outils/Bluetooth observés, travaux Git préservés, suite locale exécutable | Validé |
| J2 — Faisabilité HID | Déterminer une voie Bluetooth native viable | Rapport matériel/OS, diagnostic GATT et prototype HID minimal | MonOrdinateur reconnaît une souris Bluetooth issue du mini-PC, avec événement de test | En cours — GO_WITH_RESERVATIONS |
| J3 — API fonctionnelle | Transformer des commandes API en événements souris | API locale + moteur de commandes + adaptateur HID | Mouvements, clics et défilement testés de bout en bout | À faire |
| J4 — Activation robuste | Automatiser artefact Git, lancement local, état, arrêt et rollback | Scripts versionnés ; accès distant optionnel | Version SHA confirmée, idempotence, erreurs gérées et rollback local testés | En cours |
| J5 — MVP qualifié | Vérifier comportement, robustesse et sécurité | Batterie de tests, rapport de qualification, limites résiduelles | Revue indépendante du code et des preuves ; arbitrage explicite | À faire |

## Dépendances et points de décision

- **J1 avant essais réels** : la machine locale, le clone, les outils et le
  Bluetooth sont inventoriés. L'accès distant historique est secondaire.
- **J2 est un jalon de décision GO / NO-GO** : les préconditions donnent
  `GO_WITH_RESERVATIONS`. Une publicité, un appairage et un mouvement autorisés
  restent nécessaires avant `GO`. En cas d'échec, comparer un module HID externe
  sans achat automatique.
- **J3 dépend de J2**, mais l'API peut être maquettée et testée indépendamment grâce à un adaptateur simulé.
- **J4** réutilise les scripts de releases consolidés, mais se concentre sur
  l'activation locale. La maintenance distante est documentée séparément.
- **J5** n'est pas une mise en production automatique.

## Règle d'évolution

Toute modification de périmètre, de jalon ou de critère de sortie est documentée dans [DECISIONS.md](DECISIONS.md), puis reflétée ici et dans [PLANNING.md](PLANNING.md). Aucun jalon validé par simple déclaration non accompagnée de preuves.

**Responsabilités :** Codex réalise, documente les tests et propose les changements ; ChatGPT tient cette roadmap à jour, suit Git/GitHub, et réalise les revues de code ou de preuves sur demande explicite ou au jalon convenu ; l'utilisateur arbitre les décisions engageantes.
