# Planning opérationnel

Progression sans échéances fixes : **À faire → En cours → En revue → Validé**.
Un état validé exige une preuve adaptée ; une capacité déclarée par Windows ne
valide pas à elle seule le fonctionnement HID.

## Situation consolidée

- MC-INIT-001 à 003 : travaux préservés dans les PR Draft #1 à #3 et réunis
  sans fusion dans la branche MC-REPRISE-001.
- Environnement local : inventorié ; clone officiel dans `source/` ; artefacts
  d'exécution préexistants préservés.
- Tests : 79 PASS sur mini-pc-backend après ajout des gardes d'audit.
- Bluetooth : rôles BLE et API GATT favorables ; aucune émission exécutée.
- Audit deux canaux : architecture et plan prêts ; radio observée Off pendant le
  probe GATT non diffusé ; cible non accessible et donc non diagnostiquée.
- Audit complémentaire : PnP/pilote/services sains ; `RadioNotAvailable` causé
  uniquement par la radio logicielle Off pour HID/Battery. Créations GATT
  minimales réussies sans publicité, radio restaurée Off. MonOrdinateur reste
  `INCOMPLETE` faute de canal natif existant depuis le mini-PC.

## Tâches

| ID | Jalon | Travail | Livrable / preuve | État |
|---|---|---|---|---|
| MC-001 | J0 | Documentation de référence | documents du dépôt | Validé |
| MC-002 | J1 | Inventorier mini-pc-backend sans modification | `MC-REPRISE-001/evidence/environment.json` | Validé |
| MC-003 | J1 | Consolider Git et rendre les tests reproductibles | branche unique, 72 PASS | En revue |
| MC-003A | J4 | Artefact par SHA, staging et release locale | code/tests MC-INIT-003 consolidés | En cours |
| MC-003B | J4 | Activation, santé, arrêt et rollback locaux réels | preuve sur une application témoin | À faire |
| MC-003C | J4 | Maintenance SSH/SFTP optionnelle | requalification seulement si nécessaire | Secondaire |
| MC-004 | J2 | Qualifier matériel, pilote, rôles BLE et API GATT | diagnostic et rapport MC-REPRISE-001 | En revue — GO_WITH_RESERVATIONS |
| MC-005A | J2 | Construire un prototype HOGP minimal | service conforme, arrêt garanti | Réalisé — build natif et GATT préparé |
| MC-005B | J2 | Publicité, appairage et mouvement minimal | protocole matériel et traces expurgées | Bloqué — identité MSIX/certificat utilisateur à approuver |
| MC-005C | J2/J3 | Auditer HOGP, retour position et boucle précise | `MC-HID-AUDIT-001` | En revue — audit livré |
| MC-005D | J2/J3 | Qualifier cause radio et prérequis cible | `MC-HID-AUDIT-002` | En revue — mini-PC READY, cible INCOMPLETE |
| MC-006 | J3 | Contrat API, agent LAN et moteur de commandes | contrat + adaptateurs simulés + tests | Réalisé logiciel ; agent réel opérationnel |
| MC-007 | J3 | Intégrer HOGP et sécurités | démo API → souris | En cours — chaîne prête, mouvement réel non atteint |
| MC-008 | J3 | Trajectoires, zones et séquences A→B→C | code, API et tests | Réalisé en simulation ; matériel à qualifier |
| MC-009 | J5 | Robustesse, reconnexion et arrêt d'urgence | rapport de qualification | À faire |
| MC-010 | J5 | Revue finale sur demande/jalon | verdict motivé | À faire |

## Prochaine décision

Approuver ou refuser l'ancre de confiance de développement limitée à
`CurrentUser` nécessaire à l'installation du MSIX HOGP. La cible, l'agent
interactif, le HTTPS privé et la compilation sont déjà qualifiés. Après cette
approbation seulement : publicité, appairage, mouvement minimal puis batterie
matérielle complète. Ne pas déclarer PASS avant ces mesures.

## Règles de livraison

Codex travaille sur mini-pc-backend, publie une PR Draft cohérente avec rapport
et preuves expurgées, puis s'arrête avant fusion. Les mandats restent dans le
chat (D-021), une livraison ne déclenche pas automatiquement une revue exhaustive
(D-022) et l'autonomie technique reste bornée par les opérations sensibles
(D-023).
