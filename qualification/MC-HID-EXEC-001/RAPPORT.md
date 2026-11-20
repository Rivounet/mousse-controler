# MC-HID-EXEC-001 — Rapport d'exécution

**Date :** 20 novembre 2026  
**Branche :** `feat/mc-hid-exec-001`  
**Verdict :** `INCOMPLETE` — noyau HOGP `PASS_WITH_RESERVATIONS`

## Résultat matériel

Le premier appairage volontaire a réussi avec la cérémonie WinRT
`ConfirmOnly`, un niveau de protection effectivement utilisé `Encryption` et
une paire persistante des deux côtés. Aucune fenêtre graphique n'est requise :
la confirmation est prise en charge par l'outil interactif et consignée dans un
JSON expurgé.

MonOrdinateur a chargé les périphériques Windows natifs
`Bluetooth Low Energy GATT compliant HID device` et `HID-compliant mouse`.
Trois rapports relatifs minimaux ont été acceptés. Une sonde indépendante de
454 échantillons sur 14,965 s a observé deux transitions horizontales, +2 puis
+1 pixels, soit +3 pixels et 0 pixel vertical. Les coordonnées absolues ne sont
pas publiées.

La cause de l'ancien échec d'appairage a été isolée : MonOrdinateur acceptait
`ConfirmOnly`, mais le mini-PC rejetait l'authentification entrante tant que sa
fenêtre système de pairabilité n'était pas ouverte. Le nouvel outil
`manage_pairability.py` active temporairement connexions entrantes et découverte,
puis restaure exactement l'état initial dans un bloc `finally`.

## Reconnexion automatique

La paire restait mémorisée et l'endpoint était présent, connectable et appairé,
mais Windows ne rétablissait pas seul l'abonnement après recréation du
`GattServiceProvider`. Une ouverture GATT explicite du service HID, sans nouvel
appairage, a immédiatement rétabli `subscribed=True`.

La correction est intégrée à l'agent de position déjà requis sur
MonOrdinateur. Un moniteur sélectionne uniquement le nom exact, exige
`IsPaired`, `IsPresent` et `IsConnectable`, ouvre l'unique service HID sans
cache et conserve la connexion. Il réessaie après une perte de lien. Il ne
reçoit et n'exécute aucune commande souris ; les rapports restent exclusivement
transportés par le pilote HID Bluetooth natif.

La tâche de l'agent possède un déclencheur `AtLogOn` pour redémarrer dans la
session interactive après redémarrage de MonOrdinateur. Elle sera retirée lors
du nettoyage final de qualification.

Deux recréations complètes du fournisseur ont été qualifiées : retour de
l'abonnement en 15,409 s sur le prototype puis en 14,276 s avec le MSIX final
1.0.0.2 et la commande normale `advertise start`. Un cycle radio cible Off→On a
également été restauré sans nouvel appairage. Aucun rapport ancien n'a été
rejoué.

Les redémarrages matériels complets des deux PC n'ont pas été exécutés : ils
restent soumis à une autorisation explicite distincte. Les pertes équivalentes
des deux couches Bluetooth ont été testées séparément.

## Paquet qualifié

- identité : `Rivounet.MousseControler.Hogp`, version `1.0.0.2` ;
- Publisher : `CN=MousseControler` ;
- empreinte : `F4D17F09181DE18154C429C0ED762AD66A762C54` ;
- signature : `Valid`, type installé `Developer` ;
- SHA-256 : `907AFB9E458C7DA5C2B5555581065A310CD8EBC39BC9BB5EAE2CA508A0B12042` ;
- certificat public : `LocalMachine\TrustedPeople` uniquement ;
- aucun ajout aux magasins Root, aucune protection Windows désactivée.

Smart App Control refusait le moteur C++ nouvellement signé. Le moteur retenu
est le script PowerShell/WinRT catalogué dans le MSIX, exécuté sous la copie
intacte de `powershell.exe` signée Microsoft avec l'identité du paquet.

## Tests et jalons

`python -m unittest discover -v`, avec le répertoire temporaire court prévu :
**113/113 PASS en 63,730 s**. Les builds réels de `PairingTool.exe`,
`PositionAgent.exe` et du MSIX signé ont également réussi.

| Jalon | Résultat |
|---|---|
| Accès aux deux machines | PASS — OpenSSH existant, host key stricte ; jamais RustDesk |
| MSIX, identité et publicité | PASS |
| Appairage chiffré persistant | PASS |
| Reconnaissance souris HID native | PASS |
| Mouvement relatif minimal mesuré | PASS |
| Reconnexion après recréation HOGP | PASS — 14,276 s avec l'agent |
| Cycle radio cible | PASS |
| Redémarrage matériel des deux PC | Non exécuté — autorisation requise |
| Clic, scroll, précision, P95 et trajectoires complètes | Non qualifiés matériellement |
| Livraison | PR #6 Draft, aucune fusion |

## État courant et réserves

La paire est conservée pour le test de redémarrage demandé. Le MSIX, le
certificat temporaire et la radio cible restent actifs tant que cette
qualification n'est pas close. Le nettoyage final restaurera l'état initial.

Le verdict global reste `INCOMPLETE` car les redémarrages matériels, les
clics/scrolls sur surface sûre, la précision, la latence P95 et les séquences
complètes n'ont pas encore de preuve matérielle. Le noyau appairage → HID natif
→ mouvement → reconnexion est démontré.
