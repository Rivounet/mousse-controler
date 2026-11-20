# Planning opérationnel

**Statuts :** À faire / En cours / En revue / Validé / Bloqué. Le mandat global en cours de cadrage est **MC-HID-EXEC-001** ; ne pas confondre spécification et fonctionnalité réalisée.

## État de référence

- PR #4 fusionnée dans main ; PR #1–#3 clôturées sans fusion directe.
- PR #5 Draft : MC-HID-AUDIT-001/002, radio On temporaire et GATT local réussis ; tests **79 PASS déclarés** sur sa branche, non réexécutés sur main.
- Audit USB réalisé sur MonOrdinateur : Logitech MR0085 / Nano 046D:C534 non Bluetooth ; retour GetCursorPos local et deux écrans observés.
- Appairage HOGP chiffré, souris native, mouvement minimal et retour LAN démontrés.
- MC-HID-EXEC-001 : 113 PASS ; reconnexion après recréation HOGP en 14,276 s via l'agent. Redémarrages matériels et qualification fonctionnelle complète restent à faire.

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
| MC-005B | J2 | Publicité, appairage et mouvement minimal | protocole matériel et traces expurgées | Validé avec réserves — redémarrage matériel non testé |
| MC-005C | J2/J3 | Auditer HOGP, retour position et boucle précise | `MC-HID-AUDIT-001` | En revue — audit livré |
| MC-005D | J2/J3 | Qualifier cause radio et prérequis cible | `MC-HID-AUDIT-002` | En revue — mini-PC READY, cible INCOMPLETE |
| MC-006 | J3 | Contrat API, agent LAN et moteur de commandes | contrat + adaptateurs simulés + tests | Réalisé logiciel ; agent réel opérationnel |
| MC-007 | J3 | Intégrer HOGP et sécurités | démo API → souris | En cours — chaîne prête, mouvement réel non atteint |
| MC-008 | J3 | Trajectoires, zones et séquences A→B→C | code, API et tests | Réalisé en simulation ; matériel à qualifier |
| MC-009 | J5 | Robustesse, reconnexion et arrêt d'urgence | rapport de qualification | À faire |
| MC-010 | J5 | Revue finale sur demande/jalon | verdict motivé | À faire |

**Mandat :** Codex sur mini-pc-backend, autorisé à coordonner les deux machines dans les limites du mandat exécutoire ; les modifications sensibles, l'accès distant et l'appairage restent supervisables. Une seule PR Draft cohérente, sans fusion automatique. Ne pas enregistrer le texte du mandat dans GitHub.

## Prochaine porte

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

## Critères proposés (non mesurés)

Erreur finale ≤ 2 px sur trois mesures, P95 ≤ 4 px, ≥ 99 % des cibles sous 2 s, refus d'une mesure > 150 ms, arrêt cible ≤ 250 ms. Les seuils sont à valider par essais réels et peuvent nécessiter arbitrage motivé.
