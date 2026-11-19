# Planning opérationnel

Progression sans échéances fixes : **À faire → En cours → En revue → Validé**.
Un état validé exige une preuve adaptée ; une capacité déclarée par Windows ne
valide pas à elle seule le fonctionnement HID.

## Situation consolidée

- MC-INIT-001 à 003 : travaux préservés dans les PR Draft #1 à #3 et réunis
  sans fusion dans la branche MC-REPRISE-001.
- Environnement local : inventorié ; clone officiel dans `source/` ; artefacts
  d'exécution préexistants préservés.
- Tests : 72 PASS sur mini-pc-backend.
- Bluetooth : rôles BLE et API GATT favorables ; aucune émission exécutée.

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
| MC-005A | J2 | Construire un prototype HOGP minimal | service conforme, arrêt garanti | En attente d'autorisation d'essai |
| MC-005B | J2 | Publicité, appairage et mouvement minimal | protocole matériel et traces expurgées | En attente d'autorisation |
| MC-006 | J3 | Contrat API et moteur de commandes | contrat + adaptateur simulé + tests | À faire après décision J2 |
| MC-007 | J3 | Intégrer HOGP et sécurités | démo API → souris | À faire |
| MC-009 | J5 | Robustesse, reconnexion et arrêt d'urgence | rapport de qualification | À faire |
| MC-010 | J5 | Revue finale sur demande/jalon | verdict motivé | À faire |

## Prochaine décision

Autoriser ou refuser le protocole
[`PROTOCOLE-HID.md`](../qualification/MC-REPRISE-001/PROTOCOLE-HID.md) :
création du service GATT/HID, publicité visible, appairage avec MonOrdinateur et
mouvement relatif minimal. La commande d'arrêt et les effets sont décrits avant
toute exécution.

Sans cette autorisation, J2 reste en cours et le développement applicatif
complexe ne démarre pas.

## Règles de livraison

Codex travaille sur mini-pc-backend, publie une PR Draft cohérente avec rapport
et preuves expurgées, puis s'arrête avant fusion. Les mandats restent dans le
chat (D-021), une livraison ne déclenche pas automatiquement une revue exhaustive
(D-022) et l'autonomie technique reste bornée par les opérations sensibles
(D-023).
