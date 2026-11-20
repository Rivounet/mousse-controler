# Roadmap — jalons sans échéances fixes

Pilotage par **preuves fonctionnelles**, non par simple disponibilité d'API.
MC-HID-EXEC-001 est livré dans la PR #6 Draft, non fusionnée, avec un verdict
`PASS_WITH_RESERVATIONS`.

| Jalon | Finalité | Livrable attendu | Critère de sortie | État |
|---|---|---|---|---|
| J0 — Cadrage | Source de vérité commune | README, architecture, planning, tests, déploiement, décisions, consignes Codex | Documents cohérents et publiés | Validé |
| J1 — Environnement local | Qualifier mini-pc-backend comme machine de développement et d'exécution | Inventaire contrôlé, clone séparé des releases, tests reproductibles | OS/outils/Bluetooth observés, travaux Git préservés, suite locale exécutable | Validé |
| J2 — Faisabilité HID | Déterminer une voie Bluetooth native viable | Rapport matériel/OS, diagnostic GATT et prototype HID minimal | MonOrdinateur reconnaît une souris Bluetooth issue du mini-PC, avec événement de test | Validé — HOGP natif et appairage chiffré démontrés |
| J3 — API et position | Transformer des commandes API en événements souris corrigés par retour réel | API locale + moteur + adaptateur HID + agent position LAN | Positions, mouvements, clics et défilement testés de bout en bout | Validé — chaîne matérielle complète qualifiée |
| J4 — Activation robuste | Automatiser artefact Git, lancement local, état, arrêt et rollback | Scripts versionnés ; accès distant optionnel | Version SHA confirmée, idempotence, erreurs gérées et rollback local testés | Validé avec réserves — AtLogOn et reprise qualifiés |
| J5 — MVP qualifié | Vérifier comportement, robustesse et sécurité | Batterie de tests, rapport de qualification, limites résiduelles | Revue indépendante du code et des preuves ; arbitrage explicite | En revue — PASS_WITH_RESERVATIONS, PR #6 Draft |

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
