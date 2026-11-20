# Architecture technique — cible MC-HID-EXEC-001

## Deux machines, deux canaux

```text
mini-pc-backend
  CommandGateway (authentification/TTL/idempotence)
    → SequenceEngine (zones, modes d'attente, pause/reprise/arrêt)
    → TrajectoryEngine (chemin courbe, vitesse, variations bornées)
    → PositionController (mesure fraîche, correction, limites)
    → IHogpTransport / WindowsHogpEngine (C++20/C++/WinRT)
           │ Bluetooth LE HOGP
           ▼
MonOrdinateur : pile Bluetooth et souris HID natives Windows
  PositionAgent visible (C# .NET Framework 4.8, session utilisateur)
           │ GetCursorPos / écrans / session / horodatage
           └── HTTPS sortant + certificat épinglé + HMAC/anti-rejeu ──► mini-pc-backend
```

Codex travaille **directement sur mini-pc-backend**. L'accès OpenSSH à clé et
host key stricte vers MonOrdinateur est qualifié pour la maintenance ; l'agent
de position s'exécute séparément dans la session interactive.

## Contrats et limites

- **Zones** : rectangle (x,y,largeur,hauteur), cercle (centre,rayon), polygone (sommets). Validation géométrique, écrans virtuels et coordonnées signées. Point cible tiré aléatoirement dans la zone, graine configurable en test.
- **Séquences** : A→B→C… ; modes après arrivée : temporisation configurable ou commande explicite ; les deux peuvent coexister. États `IDLE`, `MOVING`, `ARRIVED`, `WAITING`, `PAUSED`, `COMPLETED`, `STOPPED`, `ERROR`.
- **Trajectoires** : courbes et points intermédiaires, profils d'accélération/décélération et vitesse variable, micro-variations bornées pendant le mouvement seulement. Paramètres configurables, pas d'usurpation Logitech ni de dissimulation d'automatisation.
- **PositionController** : une commande relative HID adaptative puis une mesure
  **réelle plus récente** ; amplitude rapide calibrée loin de la cible, correction
  fine plafonnée après dépassement, arrêt si donnée obsolète, session/topologie
  modifiée, écart concurrent anormal ou timeout. Ne jamais présenter une
  estimation comme une mesure.
- **IHogpTransport** : start/stop/state/send_relative/release_all ; HOGP conforme, pairing volontaire, chiffrement, notifications, relâchement boutons, aucun rejeu après reconnexion. Doubles simulés pour tests.
- **Agent cible** : lit seulement curseur, topologie, DPI et état de session ; publie les mesures, sans entrée de commandes souris, sans capture d'écran, sans service caché.
- **LAN** : HTTPS sur réseau privé, certificat épinglé, HMAC-SHA-256, anti-rejeu, séquence, horodatage, secrets protégés, aucun port entrant sur MonOrdinateur.

## Priorités et alternatives

P1 : HOGP natif entre les deux PC. Le récepteur Logitech Nano `046D:C534` est hors périmètre (radio propriétaire 2,4 GHz non Bluetooth). Repli : pont HID physique programmable après arbitrage ; HID virtuel seulement en option secondaire explicitement décidée. `SendInput`/`SetCursorPos` seuls ne satisfont pas l'exigence de périphérique HID.

## État des preuves

Les audits de la PR #5 avaient démontré uniquement la création GATT non diffusée
et `GetCursorPos`; cette limite est conservée comme preuve historique. La PR #6
démontre désormais publicité, appairage `ConfirmOnly` chiffré persistant,
pilote/souris HID natifs, mouvements, clics, défilement, retour HTTPS/HMAC,
zones, trajectoires, séquences, reconnexion et tâches `AtLogOn` sur les deux
machines. La série stable de 100 mouvements atteint 100 % de réussite, une
médiane de 670,483 ms, un P95 de 983,052 ms et une erreur maximale de 2 px.

## Exploitation et sécurité

```text
Mousse-controler/
    source/       # clone Git et tests
    releases/     # artefacts immuables par SHA
    staging/      # préparation contrôlée
    state/        # activation, verrous et états
    logs/         # journaux locaux expurgés
```

Le clone n'est jamais remplacé par une release. Les composants SSH/SFTP restent
isolés dans `scripts/remote/` et ne sont pas une dépendance de l'application.

## Limites du MVP

Commandes prévues : `move(dx, dy)`, `click(button)`, `press`, `release`,
`scroll(delta)`, `status()` et `stop()`. Toutes les émissions passent sous le
même verrou que l'arrêt : l'intention d'arrêt est publiée avant l'attente du
verrou, puis chaque commande revalide l'époque active juste avant le transport.
Les coordonnées absolues, l'analyse de
l'écran et le contrôle intelligent des applications sont hors périmètre.

L'API de commande est liée à `127.0.0.1` par défaut. Un endpoint LAN distinct,
HTTPS et authentifié, reçoit uniquement les mesures de position émises par la
cible ; il n'est pas une API de commande.

L'architecture détaillée et la boucle de position sont spécifiées dans
[`MC-HID-AUDIT-001/ARCHITECTURE.md`](../qualification/MC-HID-AUDIT-001/ARCHITECTURE.md).

## Alternative en cas de NO-GO

Si le prototype conforme échoue sur la pile Windows/Realtek, comparer d'abord un
adaptateur externe programmable capable d'HOGP. Un changement d'OS, de pilote ou
de matériel nécessite une décision explicite ; aucune installation implicite.

## Réalisation MC-HID-EXEC-001 — 20 novembre 2026

La réalisation sépare quatre responsabilités :

- `HogpTransport` : processus PowerShell/WinRT sous identité MSIX, hébergé par le
  binaire Windows Microsoft-signé, services HID `0x1812` et Battery
  `0x180F`, rapports relatifs de six octets, chiffrement obligatoire et aucune
  émission sans abonnement du Host ;
- `PositionController` : sérialisation des commandes, mesures fraîches de moins
  de 150 ms, correction adaptative tenant compte de l'accélération, plafonnée à
  48 puis mode fin plafonné à 8, changement de session/topologie fail-closed ;
- `TrajectoryEngine` : calcul pur de courbes quadratiques, profil progressif,
  variations de vitesse, micro-variations bornées uniquement en mouvement et
  plafond configurable de points (10 par défaut) ;
- `SequenceRunner` : zones rectangle/cercle/polygone, graine reproductible,
  modes automatique/commandé et états `IDLE` à `ERROR`.

L'agent .NET Framework 4.8 de `MonOrdinateur` s'exécute visiblement dans la
session console, lit position physique/DPI/topologie et ne possède aucune API
d'entrée. Il publie en sortie seulement vers HTTPS privé avec certificat
épinglé, HMAC-SHA-256, séquence et horodatage. L'API de commande reste sur
`127.0.0.1`, avec bearer DPAPI, TTL, idempotence et limite de débit.

La base GATT exige une identité de package déclarant la capacité `bluetooth`.
Smart App Control refuse le binaire C++ auto-signé même lorsque le certificat
public exact est dans `LocalMachine\TrustedPeople`. Le paquet utilise donc une
copie Authenticode-valide de `powershell.exe`, signée Microsoft, pour héberger le
script WinRT catalogué dans le MSIX. `CreateAsync`, la création des services,
la publicité `Started`, la reconnaissance HID et les rapports réels ont été
démontrés sans désactiver de protection.

L'agent cible reste visible et démarre par tâche interactive `AtLogOn`, après
ouverture manuelle de session, sans auto-logon. L'arrêt d'urgence publie d'abord
l'état arrêté, attend l'émission en cours, libère les boutons et arrête le
transport sous le même verrou. Un second arrêt n'émet rien ; seul `start()`
ouvre une nouvelle époque. TTL, limites de débit et absence de rejeu après
reconnexion restent imposés. Les scripts SSH/SFTP et releases sont des moyens
secondaires de maintenance. Aucune garantie d'indétectabilité par les
applications.
