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

Codex travaille **directement sur mini-pc-backend** et pilote les interventions autorisées sur MonOrdinateur via un accès distant authentifié à établir ou à qualifier ; un accès réseau distant n'assure pas à lui seul l'accès à la session graphique interactive.

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

Sur mini-pc-backend, radio Bluetooth temporairement On et créations non diffusées HID `0x1812`, Battery `0x180F`, caractéristiques HID et Report Reference réussies ; radio restaurée Off. Device Information `0x180A` : `DisabledByPolicy` (service réservé Windows). **Aucune publicité, association, notification HID ni commande réelle démontrée.** Sur MonOrdinateur, `GetCursorPos` et deux écrans ont été observés ; liaison LAN sécurisée non qualifiée. Ces résultats proviennent des audits en PR #5, non encore fusionnés.

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
`scroll(delta)`, `status()` et `stop()`. Les coordonnées absolues, l'analyse de
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
script WinRT catalogué dans le MSIX. `CreateAsync`, la création des services et
la publicité `Started` ont été démontrés sans désactiver de protection. La
reconnaissance HID et les rapports réels restent à qualifier sur la cible.

Le processus de qualification reste au premier plan ; l'agent cible est visible
et à démarrage manuel. L'arrêt d'urgence purge les commandes et relâche les
boutons ; TTL, limites de débit et absence de rejeu après reconnexion sont
imposés. Les scripts SSH/SFTP et releases restent des moyens secondaires de
maintenance. Aucune garantie d'indétectabilité par les applications.
