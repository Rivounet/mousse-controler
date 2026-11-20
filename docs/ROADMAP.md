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

## J6 — MC-MOUSE-ACTIONS-001 : qualifié avec réserves, fusion en attente

**Statut : PASS_WITH_RESERVATIONS sur la PR #8 Draft non fusionnée**, qualification matérielle du 20 novembre 2026, SHA applicatif qualifié `92817a7d802c0d2c0d22b4502071a3dc4a994c19`. Les résultats ne sont pas encore ceux du code intégré à `main`.

| Lot | Résultat | État |
|---|---|---|
| J6.1 | 17 actions souris testées réellement, cinq boutons, clics multiples, maintien, drag/drop, roulette verticale ; horizontale non compatible AC Pan | Qualifié avec réserve HID |
| J6.2 | Séquences mixtes, non-rejeu et WebSocket authentifié ; 37 événements témoins | Qualifié |
| J6.3 | Capture avant/après, écran entier sous curseur ; deux PNG 1920×1080 traités, sources supprimées, versions de preuve recadrées | Qualifié avec conservation contrôlée |
| J6.4 | Suite **177/177 PASS**, arrêt d'urgence et reconnexion réels, rapport et preuves expurgés | Qualifié avec réserves |

SSH hors sandbox vers `MonOrdinateur` qualifié via fichier dédié, autorisation persistante restreinte et tâche interactive temporaire contrôlée. Aucune modification d'ACL, compte, pare-feu ou protection. Réserves : roulette horizontale HID indisponible, dossier de staging maintenance vide résiduel, accord préalable pour toute future prise de souris.

**Prochaine porte :** vérification des preuves puis arbitrage explicite de fusion de la PR #8. Pas de fusion implicite. Hors périmètre : clavier, capture continue ou autonome, moteur d'analyse visuelle.

### Clôture du jalon J6 dans GitHub

PR #8 **fusionnée dans `main`** le 20 novembre 2026, commit `e0658142a65d8b494f109efa3318c6ea21feac3d`. **J6 : validé avec réserves**, 185 tests logiciels réussis selon les preuves publiées et 17 actions matérielles vérifiées avant les correctifs finaux. Aucune qualification post-fusion des processus installés n'est revendiquée. Réserves et contraintes de prise de souris maintenues.

## J7 — Découverte automatique des contrats API

MC-API-CATALOG-001 ajoute une source déclarative unique pour les commandes, les
types d'actions et les événements. Le routeur consomme directement les contrats,
la documentation est générée depuis eux et les tests interdisent commandes
fantômes ou gestionnaires non catalogués. État : **implémenté et qualifié en
logiciel sur branche dédiée, PR Draft à publier**. Critère de sortie GitHub : PR
Draft documentée, revue puis décision explicite ; aucune fusion automatique.

## J8 — Consolidation des audits et programme de fiabilisation (20 novembre 2026)

**État courant :** J7 MC-API-CATALOG-001 **MERGED** via [PR #10](https://github.com/Rivounet/mousse-controler/pull/10), commit `d19db664bc1e7d83ab1d289f89373f9e327a482b`. Les anciennes mentions Draft ci-dessus sont historiques et ne sont plus le statut courant. Audit indépendant Codex [PR #11](https://github.com/Rivounet/mousse-controler/pull/11) **Draft, non fusionnée** ; audit ChatGPT archivé sur branche isolée.

**Verdict consolidé :** `MAINTENABLE_WITH_MAJOR_RESERVATIONS`. [Comparaison et plan global](../audits/2026-11-20-consolidation/REPORT.md). Lots R0 baseline/tests sûrs, R1 sûreté actions/arrêt, R2 bornes HOGP/LAN, R3 quotas/ressources/rollback, R4 tests et builds, R5 refactoring minimal, R6 documentation. Les quatre P1 issus de la contre-expertise sont des portes avant extension fonctionnelle importante. Aucun correctif ou déploiement encore effectué. Fusion des PR et HID réel uniquement après accord explicite.
