# Stratégie de tests et qualification

## Commande locale de référence

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

## Niveaux

| Niveau | But | État |
|---|---|---|
| T0 | cohérence Git, syntaxe et documentation | exécuté dans MC-REPRISE-001 |
| T1 | unités, artefacts, releases et gardes diagnostics | 79 PASS |
| T1A | radio et diagnostic cible réutilisable | HID/Battery et forme HID créés sans publicité ; radio finale Off ; cible non exécutée |
| T2 | publicité, bonding et pilote HID | non exécuté, autorisation requise |
| T3 | API → mouvement/clic/scroll | non développé |
| T4 | reconnexion, saturation, arrêt d'urgence | non développé |

## Qualification Bluetooth en deux portes

1. **Lecture seule** : pilote, services, rôles BLE et surface WinRT. Autorisée
   sans interaction avec la cible ; script `scripts/bluetooth/diagnose.ps1`.
2. **Matérielle** : service HOGP, publicité, appairage et mouvement minimal.
   Exécutée seulement après autorisation selon
   `qualification/MC-REPRISE-001/PROTOCOLE-HID.md`.

Un résultat positif de porte 1 ne peut produire qu'un
`GO_WITH_RESERVATIONS`. `GO` requiert la reconnaissance comme souris et un
événement réellement observé sur MonOrdinateur.

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
`INCOMPLETE`, indépendamment des 103 PASS.
