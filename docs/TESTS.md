# Stratégie de tests et qualification

## Référence

```powershell
python -m unittest discover
```

MC-REPRISE-001 a corrigé la découverte depuis la racine : la commande exécutait
72 tests au lieu d'en annoncer zéro. MC-HID-AUDIT-001/002 ajoutent sept gardes ;
le 19 novembre 2026, les **79 tests** ont réussi sur mini-pc-backend après le
cycle radio temporaire, avec un chemin temporaire court.

La suite couvre 69 tests historiques d'artefacts, releases, chemins, erreurs,
verrous et client distant hors ligne, trois tests du diagnostic Bluetooth et
sept tests du diagnostic cible/gardes anti-publicité et de restauration radio.
Elle ne crée pas de
publicité et n'émet aucun rapport HID.

La PR #4 a livré 72 tests réussis selon MC-REPRISE-001. La PR #5 a déclaré **79 tests réussis** après les audits radio, mais elle reste Draft ; ne pas attribuer ce total à `main` sans réexécution.

## Matrice de qualification

| Niveau | Vérifications | Statut |
|---|---|---|
| T0 | cohérence Git, syntaxe et documentation | exécuté dans MC-REPRISE-001 |
| T1 | Unités, géométrie, trajectoires, séquences, sécurité et adaptateurs simulés | 105 PASS |
| T2 | Séquences A→B→C, modes temporisé/commandé, pause/reprise/étape suivante/arrêt, état et non-rejeu | PASS simulé ; réel à faire |
| T3 | HOGP GATT, publicité, pairing, chiffrement, pilote HID natif, mouvement/clic/scroll et relâchement boutons | GATT non diffusé qualifié en PR #5 ; reste à faire |
| T4 | Agent GetCursorPos, topologie/DPI/session, HTTPS épinglé/HMAC, anti-rejeu, mesures fraîches, coupures LAN | Agent réel et échantillon signé qualifiés ; coupures à faire |
| T5 | Correction par feedback réel, arrivée dans zone, multi-écrans, vitesse, concurrence souris physique, latence, arrêt d'urgence et reconnexion | À faire |

## Critères d'acceptation

- **Souris HID native** reconnue sur MonOrdinateur, sans pilote personnalisé sur la cible ; rapport HID réel observé.
- **Retour réel** de coordonnées physiques signées par agent visible ; horodatage, source, session et génération topologique.
- **Séquences** de zones A→B→C ; les trois géométries ; point cible tiré dans le périmètre ; trajectoires courbes, vitesse variable et micro-variations bornées pendant mouvement seulement.
- **Modes** : délai configurable ou commande explicite, avec pause/reprise/arrêt sans rejeu.
- **Précision cible proposée** : erreur ≤ 2 px sur trois mesures, P95 ≤ 4 px, réussite ≥ 99 % sous 2 s ; mesure > 150 ms refusée ; arrêt cible ≤ 250 ms. Ce ne sont pas des performances démontrées.
- **Sécurité** : arrêt d'urgence, commandes TTL/idempotentes, relâchement boutons, pas de commande via l'agent cible, aucune donnée sensible publiée.

Distinguer les tests simulés, locaux et **observés sur les deux machines**. Une compilation ou un test simulé ne valide pas le fonctionnement réel. La qualification ne vise ni l'usurpation Logitech ni l'évasion de détection d'automatisation.

Le probe `scripts/bluetooth/probe-gatt-shape.ps1` ne constitue pas la porte 2 :
il a créé la forme locale uniquement et ne lance jamais `StartAdvertising`.
Le diagnostic
`scripts/diagnostics/Inspect-MonOrdinateur.ps1` doit être exécuté dans la session
interactive de la cible avant le mandat de réalisation.

## Acceptation MVP

- MonOrdinateur reconnaît une souris Bluetooth native après appairage ;
- agent cible limité au retour de position, visible et incapable de recevoir une
  commande souris ;
- mouvement relatif, clic gauche/droit et défilement via un client autorisé ;
- aucune commande invalide ou expirée émise ;
- reconnexion sans rejeu de commandes obsolètes ;
- arrêt d'urgence mesuré, publicité arrêtée et souris physique disponible ;
- API non exposée publiquement ;
- activation par SHA et rollback reproductibles sur mini-pc-backend.

## Compte rendu d'un lot

Indiquer branche et SHA, machine, commandes, total de tests, durée, PASS/FAIL,
opérations non exécutées, effets Bluetooth éventuels, arrêt/rollback et preuves
expurgées. Ne publier ni adresses Bluetooth, identifiants matériels uniques,
comptes, chemins personnels, secrets ou journaux privés.

La revue de code approfondie reste sur demande ou au jalon convenu ; livraison
d'une PR Draft ne signifie ni validation, ni fusion.

## MC-HID-EXEC-001

Le 20 novembre 2026, `python -m unittest discover -v` a exécuté **103 tests en
60,365 s : 103 PASS**. Les 24 tests ajoutés couvrent :

- transport simulé, fraîcheur, correction et changements session/topologie ;
- HMAC, anti-rejeu, horodatage et réception bornée ;
- rectangle, cercle, polygone, graine et invalidation hors topologie ;
- courbe, accélération/décélération, variation de vitesse et absence de jitter
  à l'arrêt ;
- A→B→C, attente automatique/commandée, pause/reprise, stop et absence de HID
  après arrêt ;
- API loopback, bearer constant-time, TTL et idempotence.

Preuves réelles déjà obtenues : agent session console 1, deux écrans, échantillon
HTTPS signé accepté, radio cible activée et publicité nominalement détectée lors
des premières tentatives. Non qualifiés : appairage final, pilote HID, rapports
souris, précision, P95, reconnexion et arrêt matériel. Le statut demeure donc
`INCOMPLETE`, indépendamment des tests logiciels réussis.

Après ajout de l'hôte MSIX compatible Smart App Control et de son routage par le
transport Python, la suite a exécuté **105 tests en 52,869 s : 105 PASS**, puis
une revalidation complète **105/105 en 80,412 s**. Les
deux tests supplémentaires vérifient la commande de l'alias packagé et la
compatibilité du contrat historique direct.

Les livraisons Codex sont publiées en PR Draft avec SHA, tests, durées, résultats et preuves expurgées. Pas de revue de code exhaustive automatique ; fusion sur autorisation.
