# MC-HID-EXEC-001 — Rapport d'exécution

**Date :** 20 novembre 2026  
**Branche :** `feat/mc-hid-exec-001`  
**Verdict :** `INCOMPLETE` — fonctions matérielles `PASS_WITH_RESERVATIONS`,
redémarrage du mini-PC autorisé et en attente de preuve finale

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

La tâche persistante `MousseControler-PositionAgent` possède un déclencheur
`AtLogOn` et redémarre dans la session interactive après ouverture manuelle de
session. Aucune connexion automatique n'a été activée.

Le runtime du mini-PC démarre la publicité juste après la préparation GATT. La
tâche persistante `MousseControler-HOGP`, déclenchée `AtLogOn`, a été installée
avec la configuration DPAPI/TLS de production. Un moniteur interne observe
l'état du fournisseur et le recrée après 30 s sans abonnement. Le canal stdio
du moteur empaqueté force UTF-8 pour éviter qu'un message localisé interrompe
la commande de reprise.

Deux recréations complètes du fournisseur ont été qualifiées : retour de
l'abonnement en 15,409 s sur le prototype puis en 14,276 s avec le MSIX final
1.0.0.2 et la commande normale `advertise start`. Un cycle radio cible Off→On a
également été restauré sans nouvel appairage. Aucun rapport ancien n'a été
rejoué.

Le premier redémarrage complet de MonOrdinateur a conservé l'appairage et a
reproduit un défaut de reconnexion : l'endpoint restait appairé mais non présent
et non connectable pour le client. Ce test a conduit aux corrections de
réannonce, d'encodage et d'observabilité. Un second redémarrage de validation a
retrouvé le réseau et OpenSSH. Après l'ouverture manuelle de session requise
par `AtLogOn`, l'agent a démarré, les deux endpoints Bluetooth et la souris HID
sont revenus `OK`, et le transport a atteint `Started/subscribed=True` sans
nouvel appairage. La preuve donne une borne supérieure de 197,731 s depuis le
démarrage de l'agent ; Windows ne journalise pas l'instant exact de souscription.

Le redémarrage du mini-PC a d'abord été différé pendant qu'un processus de tests
`poker-vision`, étranger au projet, rendait la condition « absence d'opération
critique » fausse. Il n'a été ni interrompu ni modifié et s'est terminé avant le
précontrôle final.

## Qualification fonctionnelle sur surface sûre

Une fenêtre temporaire dédiée, sans donnée ni commande applicative, a borné les
essais. Elle a été arrêtée et supprimée après collecte des événements.

- clic gauche : appui matériel observé 207 ms après le lancement de la commande,
  relâchement 62 ms plus tard ;
- défilement : événement Windows `delta=120` observé après 112 ms ;
- zones rectangle, cercle et polygone : trois arrivées `COMPLETED`, erreurs
  mesurées 2, 2 et 1 px ;
- cinq trajectoires supplémentaires : erreur moyenne 1,8 px, maximum 2 px ;
- latence de positionnement : médiane 3 220,356 ms, P95 9 475,176 ms ;
- pause : position inchangée pendant 1 s ;
- arrêt d'urgence : état `STOPPED`, boutons libérés et aucune position nouvelle
  après le retour de commande pendant 1 s ; runtime ensuite relancé.

La latence de positionnement reste une réserve importante. La limite de huit
unités HID par rapport évite les dépassements provoqués par l'accélération
Windows sans modifier les réglages système, au prix d'un déplacement lent.

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
**123/123 PASS en 39,541 s**. Les builds réels de `PairingTool.exe`,
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
| Redémarrage MonOrdinateur | PASS — deux cycles, OpenSSH, AtLogOn, reconnexion sans nouvel appairage |
| Redémarrage mini-pc-backend | Autorisé et en attente du précontrôle final |
| Clic et défilement | PASS sur surface dédiée |
| Zones et trajectoires | PASS — rectangle, cercle, polygone et 5 trajets mesurés |
| Précision | PASS — moyenne 1,8 px, maximum 2 px |
| Latence | MESURÉE AVEC RÉSERVE — médiane 3,220 s, P95 9,475 s |
| Pause et arrêt d'urgence | PASS matériel |
| Livraison | PR #6 Draft, aucune fusion |

## État courant et réserves

La paire, les deux tâches `AtLogOn`, le MSIX, le certificat de qualification et
les radios restent actifs car ils sont nécessaires à la qualification de
redémarrage encore ouverte. Les tâches de sonde et la surface temporaire ont été
retirées ; le secret d'agent temporaire en clair a été écrasé puis supprimé.

Le verdict global reste `INCOMPLETE` uniquement tant que le redémarrage du
mini-PC n'a pas sa preuve finale. La reconnexion cible, les fonctions clic,
scroll, zones, trajectoires, précision et arrêt disposent de preuves
matérielles expurgées.
