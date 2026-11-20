# Roadmap — jalons sans échéances fixes

Pilotage par **preuves fonctionnelles**, non par simple disponibilité d'API.
MC-HID-EXEC-001 est fusionné dans `main` par la PR #6 au commit
`77d4a5939673053fa2e0dae73bc3a284a8597ac7`, avec un verdict
`PASS_WITH_RESERVATIONS`.

| Jalon | Finalité | Livrable attendu | Critère de sortie | État |
|---|---|---|---|---|
| J0 — Cadrage | Source de vérité commune | README, architecture, planning, tests, déploiement, décisions, consignes Codex | Documents cohérents et publiés | Validé |
| J1 — Environnement local | Qualifier mini-pc-backend comme machine de développement et d'exécution | Inventaire contrôlé, clone séparé des releases, tests reproductibles | OS/outils/Bluetooth observés, travaux Git préservés, suite locale exécutable | Validé |
| J2 — Faisabilité HID | Déterminer une voie Bluetooth native viable | Rapport matériel/OS, diagnostic GATT et prototype HID minimal | MonOrdinateur reconnaît une souris Bluetooth issue du mini-PC, avec événement de test | Validé — HOGP natif et appairage chiffré démontrés |
| J3 — API et position | Transformer des commandes API en événements souris corrigés par retour réel | API locale + moteur + adaptateur HID + agent position LAN | Positions, mouvements, clics et défilement testés de bout en bout | Validé — chaîne matérielle complète qualifiée |
| J4 — Activation robuste | Automatiser artefact Git, lancement local, état, arrêt et rollback | Scripts versionnés ; accès distant optionnel | Version SHA confirmée, idempotence, erreurs gérées et rollback local testés | Validé avec réserves — AtLogOn et reprise qualifiés |
| J5 — MVP qualifié | Vérifier comportement, robustesse et sécurité | Batterie de tests, rapport de qualification, limites résiduelles | Revue indépendante du code et des preuves ; arbitrage explicite | Validé avec réserves — PR #6 fusionnée |

## Dépendances et priorités

- **J1 avant essais réels** : la machine locale, le clone, les outils et le
  Bluetooth sont inventoriés. L'accès distant historique est secondaire.
- **J2 est franchi** : publicité, appairage chiffré, pilote HID natif et rapports
  réels sont démontrés.
- **J3 est franchi** : l'API, le retour LAN, les mouvements, clics, défilement,
  trajectoires et séquences sont qualifiés ensemble.
- L'audit MC-HID-AUDIT-001 fournit l'architecture, les choix recommandés et le
  plan d'un mandat exécutoire unique ; ses préconditions ont été levées par la
  qualification réelle de MonOrdinateur.
- MC-HID-AUDIT-002 démontre radio On que HID/Battery et la forme HID minimale se
  créent sans publicité, puis restaure Off. La porte radio est franchie ; le
  diagnostic de MonOrdinateur a ensuite été exécuté dans la PR #6.
- **J4** réutilise les scripts de releases consolidés, mais se concentre sur
  l'activation locale. La maintenance distante est documentée séparément.
- **J5** n'est pas une mise en production automatique.

## Extension trajectoires et séquences

Le code et les tests couvrent les trois géométries, le tirage déterministe, les
courbes et profils de vitesse, A→B→C, les attentes automatique/commandée,
pause/reprise/skip/stop et l'interruption sur perte de position ou topologie.
La validation matérielle couvre rectangle, cercle, polygone, attentes,
pause/reprise, clics, défilement et arrêt. La série stable de 100 mouvements
atteint 100 % de réussite, médiane 670,483 ms, P95 983,052 ms et erreur maximale
2 px.

## Règle d'évolution

Toute modification de périmètre, de jalon ou de critère de sortie est documentée dans [DECISIONS.md](DECISIONS.md), puis reflétée ici et dans [PLANNING.md](PLANNING.md). Aucun jalon validé par simple déclaration non accompagnée de preuves.

**Responsabilités :** Codex réalise, documente les tests et propose les changements ; ChatGPT tient cette roadmap à jour, suit Git/GitHub, et réalise les revues de code ou de preuves sur demande explicite ou au jalon convenu ; l'utilisateur arbitre les décisions engageantes.

## J6 — MC-MOUSE-ACTIONS-001 : extension fonctionnelle en qualification

**Statut : logiciel réalisé, qualification réelle partielle.** Succède au MVP
J5 fusionné et consolidé. Une seule PR Draft de développement, sans fusion
automatique. Le runtime mini-PC et le WebSocket réel sont actifs ; les essais
visibles de l'agent/capture et les actions matérielles étendues restent la porte
de sortie.

| Ordre | Lot | Critère de sortie |
|---|---|---|
| J6.1 | Actions souris standard complètes : clics multiples, maintien, drag/drop, boutons compatibles, roulette verticale ; horizontale explicitement indisponible sur le HID actuel | Réalisé logiciel ; essai matériel sûr en attente |
| J6.2 | Actions composables en séquences ; identifiant, états et événements WebSocket authentifiés | Réalisé ; non-rejeu persistant et WebSocket réel qualifiés |
| J6.3 | Capture ponctuelle optionnelle avant/après action configurée | Réalisé logiciel et build cible ; essai cible en attente |
| J6.4 | Qualification et documentation | En cours ; suite complète PASS, rapport et paquet cible préparés |

Hors périmètre : clavier, capture continue/périodique, capture indépendante, moteur d'analyse d'images, garantie de réaction de l'application cible.
