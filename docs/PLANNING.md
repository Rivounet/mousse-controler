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

## Chantier courant — MC-MOUSE-ACTIONS-001 (J6)

**Statut : en qualification.** Branche `feat/mc-mouse-actions-001` issue de
`4b5e804`. Le moteur est activé sur mini-pc-backend ; l'agent cible compilé et
le paquet réversible sont en staging. PR Draft unique, sans fusion automatique.

| Priorité | ID | Travail | État |
|---|---|---|---|
| 1 | MC-011 | Contrat d'actions souris et capacités HID, clics multiples, maintien, drag/drop, roulette, boutons | Réalisé logiciel ; matériel ciblé à exécuter |
| 2 | MC-012 | Composition des actions et attentes dans les séquences ; annulation, non-rejeu, arrêt | Réalisé et testé |
| 3 | MC-013 | Identifiants et suivi d'action ; notifications WebSocket automatiques, authentifiées | Réalisé ; WebSocket runtime réel qualifié |
| 4 | MC-014 | Capture optionnelle avant/après action, moniteur entier contenant le curseur ; stockage et rétention configurables | Réalisé logiciel/agent ; cible interactive à qualifier |
| 5 | MC-015 | Tests, qualification matérielle, sécurité, documentation et PR Draft | En cours — 175 PASS au jalon global |

Choix validés : 1B capture avant/après uniquement ; 2C analyse future seulement ; 3C conservation par action/séquence ; 4B WebSocket ; 5C erreur configurable, arrêt par défaut. Aucun rejeu d'action incertaine, aucun clavier, aucune capture continue.

Contrôles réels sans émission HID : tâche mini-PC relancée sur le commit
`597f740`, GATT `Started`, abonnement actif, boutons à zéro, position fraîche,
ports commande/WebSocket limités à loopback. Une action d'attente de 200 ms a
produit automatiquement `ACCEPTED → RUNNING → EXECUTED` avec trois événements
uniques et corrélés. L'accès SSH `codex-remote` est volontairement séparé de la
session propriétaire de `MousseControler-PositionAgent`; l'installation cible
nécessite donc l'exécution du paquet préparé dans la session visible.
