# Stratégie de tests et qualification

## Référence

```powershell
python -m unittest discover
```

La PR #4 a livré 72 tests réussis selon MC-REPRISE-001. La PR #5 a déclaré **79 tests réussis** après les audits radio, mais elle reste Draft ; ne pas attribuer ce total à `main` sans réexécution.

## Matrice de qualification

| Niveau | Vérifications | Statut |
|---|---|---|
| T0 | Git, documentation, compilation, provenance dépendances | Partiel |
| T1 | Géométrie rectangle/cercle/polygone, sélection aléatoire intérieure, graine de test, trajectoires courbes, profils de vitesse et micro-variations seulement en mouvement | À faire |
| T2 | Séquences A→B→C, modes temporisé/commandé, pause/reprise/étape suivante/arrêt, état et non-rejeu | À faire |
| T3 | HOGP GATT, publicité, pairing, chiffrement, pilote HID natif, mouvement/clic/scroll et relâchement boutons | GATT non diffusé qualifié en PR #5 ; reste à faire |
| T4 | Agent GetCursorPos, topologie/DPI/session, HTTPS épinglé/HMAC, anti-rejeu, mesures fraîches, coupures LAN | GetCursorPos local observé ; intégration à faire |
| T5 | Correction par feedback réel, arrivée dans zone, multi-écrans, vitesse, concurrence souris physique, latence, arrêt d'urgence et reconnexion | À faire |

## Critères d'acceptation

- **Souris HID native** reconnue sur MonOrdinateur, sans pilote personnalisé sur la cible ; rapport HID réel observé.
- **Retour réel** de coordonnées physiques signées par agent visible ; horodatage, source, session et génération topologique.
- **Séquences** de zones A→B→C ; les trois géométries ; point cible tiré dans le périmètre ; trajectoires courbes, vitesse variable et micro-variations bornées pendant mouvement seulement.
- **Modes** : délai configurable ou commande explicite, avec pause/reprise/arrêt sans rejeu.
- **Précision cible proposée** : erreur ≤ 2 px sur trois mesures, P95 ≤ 4 px, réussite ≥ 99 % sous 2 s ; mesure > 150 ms refusée ; arrêt cible ≤ 250 ms. Ce ne sont pas des performances démontrées.
- **Sécurité** : arrêt d'urgence, commandes TTL/idempotentes, relâchement boutons, pas de commande via l'agent cible, aucune donnée sensible publiée.

Distinguer les tests simulés, locaux et **observés sur les deux machines**. Une compilation ou un test simulé ne valide pas le fonctionnement réel. La qualification ne vise ni l'usurpation Logitech ni l'évasion de détection d'automatisation.

Les livraisons Codex sont publiées en PR Draft avec SHA, tests, durées, résultats et preuves expurgées. Pas de revue de code exhaustive automatique ; fusion sur autorisation.
