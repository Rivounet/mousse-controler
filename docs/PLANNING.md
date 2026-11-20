# Planning opérationnel

**Statuts :** À faire / En cours / En revue / Validé / Bloqué. Le mandat
MC-HID-EXEC-001 est réalisé et qualifié `PASS_WITH_RESERVATIONS`. La PR #6 est
fusionnée dans `main` au commit
`77d4a5939673053fa2e0dae73bc3a284a8597ac7`.

## État de référence

- PR #4 fusionnée dans main ; PR #1–#3 clôturées sans fusion directe.
- PR #5 Draft : MC-HID-AUDIT-001/002, radio On temporaire et GATT local réussis ; tests **79 PASS déclarés** sur sa branche, non réexécutés sur main.
- Audit USB réalisé sur MonOrdinateur : Logitech MR0085 / Nano 046D:C534 non Bluetooth ; retour GetCursorPos local et deux écrans observés.
- Appairage HOGP chiffré, souris native, mouvement minimal et retour LAN démontrés.
- MC-HID-EXEC-001 : chaîne matérielle, redémarrages, AtLogOn, reconnexion,
  fonctions souris, trajectoires/séquences et performance qualifiés. Référence
  publiée : 127 PASS au SHA `751f75d`; corrections de concurrence finales
  revalidées par une suite complète de 136 PASS dans la même PR #6.

## Travaux structurants

| ID | Jalon | Travail | Preuve attendue | État |
|---|---|---|---|---|
| MC-001 | J0 | Documentation de référence | documents du dépôt | Validé |
| MC-002 | J1 | Inventorier mini-pc-backend sans modification | `MC-REPRISE-001/evidence/environment.json` | Validé |
| MC-003 | J1 | Consolider Git et rendre les tests reproductibles | branche unique, 72 PASS | En revue |
| MC-003A | J4 | Artefact par SHA, staging et release locale | code/tests MC-INIT-003 consolidés | En cours |
| MC-003B | J4 | Activation, santé, arrêt et rollback locaux réels | preuve sur une application témoin | À faire |
| MC-003C | J4 | Maintenance SSH/SFTP optionnelle | requalification seulement si nécessaire | Secondaire |
| MC-004 | J2 | Qualifier matériel, pilote, rôles BLE et API GATT | diagnostic et rapport MC-REPRISE-001 | En revue — GO_WITH_RESERVATIONS |
| MC-005A | J2 | Construire un prototype HOGP minimal | service conforme, arrêt garanti | Réalisé — build natif et GATT préparé |
| MC-005B | J2 | Publicité, appairage et mouvement minimal | protocole matériel et traces expurgées | Validé — redémarrages et reconnexion ensuite qualifiés |
| MC-005C | J2/J3 | Auditer HOGP, retour position et boucle précise | `MC-HID-AUDIT-001` | En revue — audit livré |
| MC-005D | J2/J3 | Qualifier cause radio et prérequis cible | `MC-HID-AUDIT-002` | Validé historiquement ; prérequis cible levés par la PR #6 |
| MC-006 | J3 | Contrat API, agent LAN et moteur de commandes | contrat + adaptateurs simulés + tests | Réalisé logiciel ; agent réel opérationnel |
| MC-007 | J3 | Intégrer HOGP et sécurités | démo API → souris | Validé matériellement |
| MC-008 | J3 | Trajectoires, zones et séquences A→B→C | code, API et tests | Validé logiciel et matériel |
| MC-009 | J5 | Robustesse, reconnexion et arrêt d'urgence | rapport de qualification | Validé avec réserves ; concurrence finale durcie |
| MC-010 | J5 | Revue finale sur demande/jalon | verdict motivé | Validé avec réserves — PR #6 fusionnée |

**Mandat :** Codex sur mini-pc-backend, autorisé à coordonner les deux machines dans les limites du mandat exécutoire ; les modifications sensibles, l'accès distant et l'appairage restent supervisables. Une seule PR Draft cohérente, sans fusion automatique. Ne pas enregistrer le texte du mandat dans GitHub.

## Prochaine porte

Maintenir la cohérence entre `main` et les composants installés. Toute correction
post-fusion indispensable est isolée dans une PR Draft ciblée ; aucune fusion
supplémentaire n'est implicite.

## Règles de livraison

Codex travaille sur mini-pc-backend, publie une PR Draft cohérente avec rapport
et preuves expurgées, puis s'arrête avant fusion. Les mandats restent dans le
chat (D-021), une livraison ne déclenche pas automatiquement une revue exhaustive
(D-022) et l'autonomie technique reste bornée par les opérations sensibles
(D-023).

## Critères mesurés

Sur 100 mouvements : erreur maximale 2 px, réussite 100 %, latence médiane
670,483 ms et P95 983,052 ms. L'arrêt matériel, la libération des boutons et
l'absence de rejeu sont qualifiés ; la concurrence du contrôleur est couverte
par des tests déterministes sur l'adaptateur simulé.

## J6 — MC-MOUSE-ACTIONS-001 : qualification achevée avec réserves

**Statut : En revue pour fusion.** Livraison technique qualifiée `PASS_WITH_RESERVATIONS` le 20 novembre 2026 sur la [PR #8](https://github.com/Rivounet/mousse-controler/pull/8), toujours **Draft non fusionnée**. SHA applicatif de qualification `92817a7d802c0d2c0d22b4502071a3dc4a994c19`.

| ID | Travail | État |
|---|---|---|
| MC-011 | Actions souris cinq boutons, clics multiples, maintien, glisser, roulette verticale | Validé logiciel + matériel ; horizontale indisponible sur HID actuel |
| MC-012 | Séquences mixtes, attentes, pause/reprise, politiques d'erreur et non-rejeu | Validé logiciel + matériel |
| MC-013 | Journal d'actions et événements WebSocket corrélés et authentifiés | Validé logiciel + runtime |
| MC-014 | Capture optionnelle avant/après, moniteur complet sous curseur, rétention | Validé logiciel + deux captures réelles ; sources supprimées |
| MC-015 | Tests, qualification sur deux machines, arrêt d'urgence, nettoyage, preuves | Validé avec réserves ; 177/177 tests PASS en 44,286 s |

Preuves : 17 actions matérielles réussies, 37 événements sur surface sûre ; WebSocket réel, arrêt d'urgence sans événement postérieur, reconnexion HOGP active/boutons à zéro/sans rejeu. SSH hors sandbox via configuration dédiée qualifié, tâche interactive temporaire contrôlée sans élévation.

**Réserves :** absence d'AC Pan pour la roulette horizontale ; ancien dossier de staging maintenance vide non supprimé sous Windows Temp ; nouvelle prise de souris soumise à avertissement et accord explicite. Aucune CI GitHub configurée. Le prochain jalon est la décision explicite de revue/fusion, **pas une reprise de qualification automatique**.

### Contrôle de sortie J6 — correctifs de revue

Sur le SHA applicatif `e7e26332e56a39cbd2ca915413c313da07c638d9`, corrections de suppression des captures et du registre anti-rejeu intégrées : refus de suppression conservé en `DELETE_FAILED`, index de fichiers persistant ; réservations d'identifiants conservées 30 jours par défaut et jusqu'à éviction des états, y compris après compaction et redémarrage. **17/17 tests ciblés PASS ; 185/185 tests complets PASS en 54,007 s**, selon les preuves publiées. Aucun nouveau test HID réel après ces correctifs. **Prochaine porte : décision explicite de fusion de la PR #8**, actuellement Draft.

### Clôture GitHub J6

**PR #8 fusionnée dans `main`** au commit `e0658142a65d8b494f109efa3318c6ea21feac3d` le 20 novembre 2026. MC-011 à MC-015 : **Validé avec réserves**, selon qualification publiée ; les deux corrections de sûreté ont été revues avant fusion. Prochaine étape opérationnelle : contrôler la concordance entre `main`, clone local et processus installés, sans déclencher de commande HID ni de capture non autorisée. Les réserves J6 restent suivies.

## J7 — MC-API-CATALOG-001 : implémenté, livraison Draft en cours

| ID | Travail | État |
|---|---|---|
| MC-016 | Registre central partagé par découverte, routage et validation statique | Validé logiciel |
| MC-017 | Commande `api_catalog`, recherche, catégories et sélection des sections | Validé logiciel |
| MC-018 | Contrats des 28 commandes, 12 actions et 6 événements WebSocket | Validé logiciel |
| MC-019 | Référence API générée et garde `--check` | Validé logiciel |
| MC-020 | Exhaustivité, compatibilité, authentification et absence d'effet matériel | 195/195 PASS ; PR Draft à publier |

La qualification est strictement logicielle : aucune commande HID ni capture
réelle. La prochaine porte est la revue de la PR Draft ; aucune fusion ni mise à
jour de production n'est implicite.

## J8 — Plan global de correction après double audit (état courant, 20 novembre 2026)

J7 / PR #10 est **fusionnée** dans `main` au SHA `d19db664bc1e7d83ab1d289f89373f9e327a482b` ; les mentions « Draft à publier » ci-dessus sont des états historiques. La PR #11 d'audit indépendant reste **Draft non fusionnée**. Rapport contradictoire : [MC-AUDIT-CONSOLIDATION-001](../audits/2026-11-20-consolidation/REPORT.md).

| Lot | Périmètre | Priorité | État | Porte de sortie |
|---|---|---|---|---|
| R0 | Baseline, tests simulés, non-régression et consentement matériel | Prérequis | Validé — PR #13 fusionnée, `d8b412f` | Scénarios reproductibles sans HID |
| R1 | Boutons incertains, arrêt global des séquenceurs, file d'actions | P1/P2 | Validé logiciel — PR #14 fusionnée, `5b158a6` | Aucune poursuite ambiguë, états cohérents |
| R2 | Délais HOGP/WinRT et limites connexions/lectures LAN | P1 | Correctif de revue B1/B2 qualifié — PR Draft #15 | Attentes bornées, aucune reprise ambiguë |
| R3 | Quotas de captures, nettoyage serveurs, rollback agent | P1/P2 | À lancer après R0 | Quota strict, ressources fermées, restauration testée |
| R4 | Tests comportementaux, opt-in matériel, compilation C#, builds reproductibles | P2 | En accompagnement R1–R3 | Suite logicielle reproductible |
| R5 | Séquenceurs, validations, historique HOGP, refactoring ciblé | P2/P3 | Différé | Aucun changement de contrat, gain démontré |
| R6 | Documentation, roadmap, planning, reprise et suivi des preuves | Transversal | En cours | Statuts courants cohérents |

**Règles :** PR distinctes, revue avant fusion, aucun HID/capture réelle ni intervention sur `MonOrdinateur` sans autorisation. Aucune synchronisation de la production impliquée par ce planning.
