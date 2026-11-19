# Stratégie de tests et qualification

## Commande locale de référence

```powershell
python -m unittest discover
```

MC-REPRISE-001 a corrigé la découverte depuis la racine : la commande exécutait
72 tests au lieu d'en annoncer zéro. MC-HID-AUDIT-001/002 ajoutent six gardes ;
le 19 novembre 2026, les **78 tests** ont réussi sur mini-pc-backend en 34,492 s
avec un chemin temporaire court.

La suite couvre 69 tests historiques d'artefacts, releases, chemins, erreurs,
verrous et client distant hors ligne, trois tests du diagnostic Bluetooth et
six tests du diagnostic cible/gardes anti-publicité et anti-changement radio.
Elle ne crée pas de
publicité et n'émet aucun rapport HID.

## Niveaux

| Niveau | But | État |
|---|---|---|
| T0 | cohérence Git, syntaxe et documentation | exécuté dans MC-REPRISE-001 |
| T1 | unités, artefacts, releases, diagnostics non intrusifs | 78 PASS |
| T1A | radio et diagnostic cible réutilisable | PnP sain, radio Off / RadioNotAvailable ; cible non exécutée |
| T2 | service GATT, publicité, bonding et pilote HID | non exécuté, autorisation requise |
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
il ne lance jamais `StartAdvertising`. Le diagnostic
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
