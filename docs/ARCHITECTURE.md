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
- **PositionController** : une commande relative HID bornée puis une mesure **réelle plus récente** ; correction vers un point intérieur à la zone, arrêt si donnée obsolète, session/topologie modifiée, écart concurrent anormal ou timeout. Ne jamais présenter une estimation comme une mesure.
- **IHogpTransport** : start/stop/state/send_relative/release_all ; HOGP conforme, pairing volontaire, chiffrement, notifications, relâchement boutons, aucun rejeu après reconnexion. Doubles simulés pour tests.
- **Agent cible** : lit seulement curseur, topologie, DPI et état de session ; publie les mesures, sans entrée de commandes souris, sans capture d'écran, sans service caché.
- **LAN** : HTTPS sur réseau privé, certificat épinglé, HMAC-SHA-256, anti-rejeu, séquence, horodatage, secrets protégés, aucun port entrant sur MonOrdinateur.

## Priorités et alternatives

P1 : HOGP natif entre les deux PC. Le récepteur Logitech Nano `046D:C534` est hors périmètre (radio propriétaire 2,4 GHz non Bluetooth). Repli : pont HID physique programmable après arbitrage ; HID virtuel seulement en option secondaire explicitement décidée. `SendInput`/`SetCursorPos` seuls ne satisfont pas l'exigence de périphérique HID.

## État des preuves

Sur mini-pc-backend, radio Bluetooth temporairement On et créations non diffusées HID `0x1812`, Battery `0x180F`, caractéristiques HID et Report Reference réussies ; radio restaurée Off. Device Information `0x180A` : `DisabledByPolicy` (service réservé Windows). **Aucune publicité, association, notification HID ni commande réelle démontrée.** Sur MonOrdinateur, `GetCursorPos` et deux écrans ont été observés ; liaison LAN sécurisée non qualifiée. Ces résultats proviennent des audits en PR #5, non encore fusionnés.

## Exploitation et sécurité

Processus de qualification au premier plan ; agent cible visible, démarrage manuel ; arrêt d'urgence et purge des commandes, bouton relâché, TTL et limites de débit, pas de mouvement après reconnexion. Configuration et journaux sans secrets ; scripts SSH/SFTP et releases conservés comme maintenance secondaire. Pas de garantie d'indétectabilité par les applications.
