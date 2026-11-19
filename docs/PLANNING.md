# Planning opérationnel

**Statuts :** À faire / En cours / En revue / Validé / Bloqué. Le mandat global en cours de cadrage est **MC-HID-EXEC-001** ; ne pas confondre spécification et fonctionnalité réalisée.

## État de référence

- PR #4 fusionnée dans main ; PR #1–#3 clôturées sans fusion directe.
- PR #5 Draft : MC-HID-AUDIT-001/002, radio On temporaire et GATT local réussis ; tests **79 PASS déclarés** sur sa branche, non réexécutés sur main.
- Audit USB réalisé sur MonOrdinateur : Logitech MR0085 / Nano 046D:C534 non Bluetooth ; retour GetCursorPos local et deux écrans observés.
- Aucun appairage HOGP, mouvement souris depuis mini-PC ni retour LAN intégré démontré.

## Travaux structurants

| ID | Jalon | Travail | Preuve attendue | État |
|---|---|---|---|---|
| MC-BASE | J0/J1 | Référentiel et environnement local, consolidation PR #4 | Fusion et rapports | Validé |
| MC-AUDIT | J2 | Audits HOGP et radio, diagnostic cible | PR #5, création GATT sans publicité | En revue |
| MC-HID | J2 | Installer MSVC/SDK, développer HOGP, appairer et qualifier la souris native | Mouvement réel, pilote chargé, arrêt | À faire |
| MC-TARGET | J3 | Accès sécurisé à MonOrdinateur, agent visible C# et retour HTTPS/HMAC | Coordonnées réelles, session/topologie, sécurité et latence | À faire |
| MC-TRAJ | J3 | Zones rectangle/cercle/polygone ; point aléatoire interne ; trajectoires courbes, vitesse variable et micro-variations en mouvement | Tests géométriques, séquences et trajectoires | À faire |
| MC-SEQUENCE | J3 | A→B→C, attente temporisée ou commande, pause/reprise/étape suivante/arrêt | Tests d'état et séquences réelles | À faire |
| MC-CORRECTION | J3 | Mesure réelle, mouvement relatif borné, correction et confirmation d'arrivée | Matrice de précision et délais mesurés | À faire |
| MC-ROBUST | J4/J5 | Reconnexion, boutons, TTL, sécurité, rollback et qualification intégrée | Tests réels et rapport | À faire |

**Mandat :** Codex sur mini-pc-backend, autorisé à coordonner les deux machines dans les limites du mandat exécutoire ; les modifications sensibles, l'accès distant et l'appairage restent supervisables. Une seule PR Draft cohérente, sans fusion automatique. Ne pas enregistrer le texte du mandat dans GitHub.

## Critères proposés (non mesurés)

Erreur finale ≤ 2 px sur trois mesures, P95 ≤ 4 px, ≥ 99 % des cibles sous 2 s, refus d'une mesure > 150 ms, arrêt cible ≤ 250 ms. Les seuils sont à valider par essais réels et peuvent nécessiter arbitrage motivé.
