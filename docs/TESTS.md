# Stratégie de tests et qualification

## Commande locale de référence

```powershell
python -m unittest discover
```

MC-REPRISE-001 a corrigé la découverte depuis la racine : la commande exécute
désormais 72 tests au lieu d'en annoncer zéro. Le 19 novembre 2026, les 72 tests
ont réussi sur mini-pc-backend en 31,876 secondes.

La suite couvre 69 tests historiques d'artefacts, releases, chemins, erreurs,
verrous et client distant hors ligne, plus trois tests du diagnostic Bluetooth
en lecture seule. Elle ne crée pas de publicité et n'émet aucun rapport HID.

## Niveaux

| Niveau | But | État |
|---|---|---|
| T0 | cohérence Git, syntaxe et documentation | exécuté dans MC-REPRISE-001 |
| T1 | unités, artefacts, releases, diagnostic Bluetooth | 72 PASS |
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

## Acceptation MVP

- MonOrdinateur reconnaît une souris Bluetooth native après appairage ;
- aucun logiciel récepteur propre au projet sur MonOrdinateur ;
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
