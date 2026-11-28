# MC-HID-EXEC-001 — Rapport d'exécution

> **État postérieur au rapport :** la PR #6 a été fusionnée dans `main` le
> 20 novembre 2026 au commit
> `77d4a5939673053fa2e0dae73bc3a284a8597ac7`. Les mentions « Draft » de ce
> rapport décrivent l'état historique au moment de la qualification et sont
> conservées comme preuves.
>
> **Correctif de preuve du 28 novembre 2026 :** l'affirmation historique
> « aucune fenêtre graphique n'est requise » ne démontre pas un pairage entrant
> sans consentement. Une requalification sans validation de la notification sur
> `MINI-PC-BACKEND` a produit `BTHUSB 37` puis `BTHUSB 29` et aucune paire. Le
> consentement Windows Desktop est désormais classé comme provisioning manuel
> unique ; la persistance ultérieure doit rester entièrement automatique.

**Date :** 20 novembre 2026  
**Branche :** `feat/mc-hid-exec-001`  
**Verdict :** `PASS_WITH_RESERVATIONS` — fonctions matérielles, performances et
redémarrages qualifiés ; réserve limitée à l'observabilité absolue du délai LAN
et à une reprise GATT transitoire

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
Les tâches des deux hôtes possèdent également cinq reprises sur échec espacées
d'une minute.

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

Le mini-PC a ensuite redémarré à 08:43:06 après la commande contrôlée. OpenSSH
est revenu en mode `Running/Automatic`, le port 22 écoute en IPv4 et IPv6, le
Git était resté propre et l'auto-logon était toujours désactivé. Après
l'ouverture manuelle de session, le premier lancement AtLogOn a retourné `1`
et laissé un runtime partiel : condition Bluetooth transitoire non journalisée
par Task Scheduler. Une reproduction en premier plan a réussi sans changement
d'appairage, puis la tâche de production a retrouvé les deux API, l'annonce
`Started`, `subscribed=True`, les boutons à zéro et une position fraîche. La
borne supérieure observée entre ce lancement et la preuve d'abonnement est
51,248 s.

Cette panne réelle a conduit à deux protections supplémentaires : nettoyage du
transport si l'initialisation échoue, puis cinq tentatives internes espacées de
30 s dans le lanceur. Une injection de panne contrôlée, précédée de l'arrêt
d'urgence authentifié, a qualifié cette reprise : le nouveau processus et les
deux ports sont revenus seuls, puis l'abonnement HID existant et la position
fraîche (47 ms), sans appairage. Les radios Bluetooth finales des deux machines
sont `On`; les périphériques HID et GATT cible sont `OK`.

## Qualification fonctionnelle sur surface sûre

Une fenêtre temporaire dédiée, sans donnée ni commande applicative, a borné les
essais. Elle a été arrêtée et supprimée après collecte des événements.

- clics gauche et droit : appuis et relâchements matériels observés ;
- défilement : événement Windows `delta=120` observé après 112 ms ;
- zones rectangle, cercle et polygone : trois arrivées `COMPLETED`, erreurs
  mesurées 2, 2 et 1 px ;
- cinq trajectoires comparables après optimisation : médiane 803,582 ms,
  P95 1 966,363 ms, erreur moyenne 0,4 px et maximum 1 px ;
- stabilité : 100/100 déplacements réussis, médiane 670,483 ms, P95
  983,052 ms, maximum 1 245,531 ms, erreur moyenne 0,796 px et maximum 2 px ;
- pause : accusé d'arrêt effectif, position inchangée pendant 500 ms ;
- arrêt d'urgence : état `STOPPED`, boutons libérés et aucune position nouvelle
  après le retour de commande pendant 1 s ; runtime ensuite relancé.

Le diagnostic instrumenté a isolé la cause dominante : l'amplitude HID fixe de
huit unités imposait 254 corrections sur cinq déplacements et l'attente des
mesures réelles représentait 15 952,262 ms, contre 1 750,118 ms de transport.
La génération de trajectoire restait inférieure à 0,2 ms. La boucle utilise
désormais une amplitude adaptative tenant compte de l'accélération observée,
jusqu'à 48 unités loin de la cible, puis une correction fine plafonnée à huit
après dépassement. Les trajectoires conservent leur profil configurable mais
sont plafonnées à dix points par défaut. Aucun réglage souris Windows n'a été
modifié.

La série stable de 100 déplacements totalise 6 650,919 ms de transport et
62 227,298 ms d'attente de feedback : le retour réel demeure le poste dominant,
mais les objectifs médiane < 1 s, P95 < 2 s, réussite >= 99 % et erreur maximale
2 px sont tous atteints. Un contrôle post-déploiement de télémétrie a confirmé
10/10 déplacements, médiane 611,730 ms, P95 863,088 ms et erreur maximale 2 px.

Sur 2 048 échantillons, la cadence réelle médiane est 63 ms (P95 94 ms), la
vérification HMAC 0,053 ms (P95 0,070 ms), le traitement récepteur 0,145 ms
(P95 0,195 ms) et `GetPhysicalCursorPos` 20 us (P95 22 us). L'horloge de la cible
étant environ 166 ms en avance, la latence LAN absolue aller simple ne peut pas
être déduite sans synchronisation d'horloges ; ce point reste explicitement non
qualifié plutôt que présenté comme une mesure négative.

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

`python -m unittest discover -v`, hors du chemin temporaire artificiellement
long du bac à sable : **136/136 PASS en 35,659 s**. Les builds réels de `PairingTool.exe`,
`PositionAgent.exe` et du MSIX signé ont également réussi.

## Correction finale de l'arrêt d'urgence

La revue a identifié une fenêtre de concurrence : `move()` testait l'arrêt avant
le verrou, tandis que `set_buttons()`, `click()` et `scroll()` ne le revalidaient
pas sous verrou. Une commande déjà en attente pouvait donc franchir une demande
d'arrêt. Un second `emergency_stop()` répétait en outre `release_all/stop` après
l'arrêt effectif.

Le contrôleur publie désormais l'intention d'arrêt avant d'attendre le verrou,
mais sérialise l'arrêt effectif et chaque émission transport sous ce même verrou.
Chaque commande revalide l'état immédiatement avant l'adaptateur. L'état du
transport effectivement arrêté est explicite : l'arrêt répété est idempotent,
`restart_transport()` abandonne une reconnexion concurrente, et seul `start()`
ouvre une nouvelle époque. Un échec après démarrage transport partiel déclenche
son nettoyage et laisse le contrôleur arrêté.

Neuf scénarios déterministes vérifient les événements exacts du transport simulé :
mouvement, clic, défilement et boutons en attente du verrou, clic déjà engagé,
reconnexion concurrente, arrêt répété, reprise explicite et échec injecté de
démarrage. Aucun événement souris ne suit l'arrêt effectif et les boutons sont
libérés avant `stop`. Aucune requalification matérielle n'a été nécessaire : ni
le protocole HOGP, ni l'algorithme de mouvement, ni les composants déployés ne
changent. Les 19 tests du contrôleur ont également réussi 50 fois de suite sans
échec d'ordonnancement.

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
| Redémarrage mini-pc-backend | PASS avec réserve — appairage conservé ; panne transitoire initiale corrigée et reprise injectée qualifiée |
| Clic et défilement | PASS sur surface dédiée |
| Zones et trajectoires | PASS — rectangle, cercle, polygone et 5 trajets mesurés |
| Précision | PASS — 100 mouvements, moyenne 0,796 px, maximum 2 px |
| Latence | PASS — 100 mouvements, médiane 0,670 s, P95 0,983 s |
| Pause et arrêt d'urgence | PASS matériel |
| Concurrence arrêt/commandes | PASS — neuf scénarios déterministes |
| Livraison | PR #6 Draft, aucune fusion |

## État courant et réserves

La paire, les deux tâches `AtLogOn`, le MSIX et le certificat de qualification
restent actifs car ils constituent la configuration fonctionnelle qualifiée.
Les tâches de sonde et la surface temporaire ont été retirées ; le secret
d'agent temporaire en clair a été écrasé puis supprimé.

Le verdict global est `PASS_WITH_RESERVATIONS`. Les objectifs de performance
sont atteints. Les réserves restantes sont l'absence de mesure LAN aller simple
absolue faute d'horloges synchronisées, l'instant exact de souscription Bluetooth
non journalisé et un intervalle transitoire `subscribed=False` après déploiement
de l'agent. La maintenance automatique a rétabli `Started/subscribed=True` sans
nouvel appairage. Aucun redémarrage physique supplémentaire n'a été nécessaire.
