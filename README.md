# Mousse-controler

Contrôle de la souris de **MonOrdinateur** depuis **mini-pc-backend**. Transport prioritaire : **Bluetooth LE HID (HOGP)**, reconnu par les pilotes Windows natifs ; retour de position réelle par **agent Windows visible et canal LAN privé sécurisé**.

> **État : qualification finale `PASS_WITH_RESERVATIONS`.** Appairage chiffré persistant, souris HID native, redémarrages des deux machines, reconnexion, clic, défilement, zones, trajectoires, précision, performance et arrêt d'urgence sont démontrés. Les réserves concernent l'observabilité du délai LAN absolu et une reprise GATT transitoire.

## Rôles et architecture

- **mini-pc-backend** : Codex unique, Git, développement, moteur HOGP C++/WinRT, contrôleur Python, moteur de trajectoires/séquences, boucle de correction et réception HTTPS des positions.
- **MonOrdinateur** : hôte HID Bluetooth natif ; **agent C# .NET Framework 4.8 visible**, limité à GetCursorPos/topologie/session, à l'envoi sortant des mesures via HTTPS authentifié et au réveil du lien GATT déjà appairé. Il n'exécute aucune commande souris.
- **GitHub** : source officielle. Le récepteur USB Logitech Nano 046D:C534 reste indépendant et hors périmètre de la commande Mousse-controler.

```text
mini-pc-backend : séquences/zones → trajectoires → contrôle de position → HOGP BLE
                                                                │
                                                    MonOrdinateur : HID natif
                                                                │
mini-pc-backend : mesures réelles ← HTTPS/HMAC LAN privé ← agent GetCursorPos
```

## Fonctionnalités demandées

- Séquence de zones **A → B → C → …** ; rectangles, cercles et polygones ; sélection d'un point aléatoire **à l'intérieur** de chaque zone, avec graine déterministe pour les tests.
- Trajectoires courbes, vitesse configurable avec accélération/décélération et micro-variations bornées **uniquement en mouvement**.
- Arrivée vérifiée par **mesure réelle** ; correction HID relative, interruption si mesure périmée, changement de session/topologie ou perte de lien.
- Après arrivée : attente configurable puis progression automatique **ou** attente d'une nouvelle commande ; pause, reprise, étape suivante et arrêt.
- Clics, boutons, défilement et arrêt d'urgence. Les paramètres de mouvement servent à la fluidité et au contrôle, **pas à masquer l'automatisation ni à usurper l'identité Logitech**.

Le système n'est pas garanti indiscernable d'une utilisation humaine. L'analyse d'écran et la prise de décision applicative autonome restent hors périmètre.

## État Git et qualification

Les trois puces suivantes conservent l'historique antérieur à la réalisation ;
elles ne décrivent pas l'état courant de la PR #6.

- PR #4 de consolidation fusionnée dans `main` (merge `d74e13e9a1af502a952d7cfdedf4aef5b0ec7473`) ; PR #1–#3 clôturées sans fusion directe.
- PR #5 Draft : audits MC-HID-AUDIT-001/002, **non fusionnée** ; résultats et scripts présents sur sa branche, à intégrer sans écrasement.
- Audits : radio mini-PC On temporaire, fournisseurs HID/Battery et caractéristiques GATT créés avec succès sans publicité, puis radio restaurée Off. Service Device Information réservé : `DisabledByPolicy`.
- Audit historique de MonOrdinateur : lecture locale de position et deux écrans
  confirmés ; l'intégration réseau et le Bluetooth HID réel, alors non
  qualifiés, le sont désormais dans MC-HID-EXEC-001.
- Les **79 tests** sont déclarés réussis dans le dernier compte rendu d'audit de la PR #5 ; ne pas les attribuer à la suite actuelle de `main` sans réexécution.

## État MC-HID-EXEC-001 vérifié le 20 novembre 2026

- 136/136 tests réussis en 35,659 s hors du chemin temporaire artificiellement long du bac à sable.
- MSIX 1.0.0.2 signé et vérifié ; appairage `ConfirmOnly` chiffré persistant.
- Pilotes HID et souris natifs chargés ; mouvement minimal mesuré +3 px horizontal, 0 px vertical.
- Reconnexion après recréation HOGP en 14,276 s grâce au moniteur GATT de l'agent.
- Verdict global `PASS_WITH_RESERVATIONS` après qualification matérielle et redémarrages contrôlés.
- Clic et défilement confirmés sur surface sûre ; rectangle, cercle, polygone et cinq trajectoires mesurés avec erreur maximale 2 px.
- Optimisation adaptative qualifiée sur 100 déplacements : 100 % de réussite,
  médiane 0,670 s, P95 0,983 s, erreur moyenne 0,796 px et maximum 2 px.
- Télémétrie réelle : cadence de feedback médiane 63 ms, HMAC 0,053 ms,
  traitement récepteur 0,145 ms et `GetPhysicalCursorPos` 20 us. La latence LAN
  aller simple reste non calculable sans horloges synchronisées.
- Deux redémarrages cible et un redémarrage mini-PC qualifiés ; reconnexion après ouverture manuelle de session, sans nouvel appairage. Une reprise interne bornée corrige l'échec Bluetooth transitoire observé au premier lancement AtLogOn du mini-PC.
- Arrêt d'urgence sérialisé avec toutes les émissions HID : les commandes qui
  attendent le verrou sont refusées après une demande d'arrêt, l'arrêt répété
  est idempotent et une reprise explicite crée une nouvelle époque de commandes.
- PR #6 : **fusionnée dans `main`** le 20 novembre 2026 au commit
  `77d4a5939673053fa2e0dae73bc3a284a8597ac7`; verdict de qualification
  conservé : `PASS_WITH_RESERVATIONS`.

## Documentation

[Référence API](docs/API-REFERENCE.md) · [Reprise](docs/REPRISE.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) · [Planning](docs/PLANNING.md) · [Tests](docs/TESTS.md) · [Décisions](docs/DECISIONS.md) · [Consignes Codex](AGENTS.md).

Les **mandats complets restent dans le chat** ; les documents GitHub consignent les décisions et exigences. Aucune fusion implicite.

## Évolution J6 qualifiée — MC-MOUSE-ACTIONS-001 (PR #8, non fusionnée)

La [PR #8](https://github.com/Rivounet/mousse-controler/pull/8) livre les actions standard d'une souris à cinq boutons, clics multiples, maintien, glisser-déposer, roulette verticale, séquences mixtes, WebSocket de résultats authentifié et captures optionnelles avant/après d'une action, limitées à l'écran entier sous le curseur. Pas de clavier, capture continue, autonome ou analyse visuelle.

**Verdict de la branche : PASS_WITH_RESERVATIONS** — 177/177 tests PASS en 44,286 s ; 17 actions sur surface sûre, 37 événements observés, deux captures réelles avant/après puis suppression des sources ; arrêt d'urgence et non-rejeu matériel qualifiés. SSH hors sandbox qualifié avec configuration dédiée et autorisation strictement bornée. Réserves : roulette horizontale indisponible sur le descripteur HOGP actuel, dossier de staging maintenance vide et autorisation explicite préalable à toute nouvelle prise de souris. **Ces fonctions J6 ne sont pas encore fusionnées dans `main`**.

**État GitHub J6 :** la PR #8 a été **fusionnée dans `main`** le 20 novembre 2026 au commit `e0658142a65d8b494f109efa3318c6ea21feac3d`. Les mentions historiques « non fusionnée » ci-dessus décrivent l'état antérieur à cette fusion. Verdict J6 : `PASS_WITH_RESERVATIONS`, 185/185 tests logiciels publiés. La concordance des processus installés avec le commit fusionné doit être vérifiée séparément, sans prise de souris non autorisée.

## Registre automatique de l'API — MC-API-CATALOG-001

La commande authentifiée `api_catalog` interroge, sur le port loopback existant,
le registre qui pilote aussi le routage et la validation statique. Elle permet
un catalogue complet, une recherche par nom, un filtre par catégorie et la
sélection des commandes, types d'actions ou événements WebSocket. La
[référence API](docs/API-REFERENCE.md) est générée depuis ce même registre avec
`python scripts/generate_api_reference.py`; `--check` détecte toute référence
obsolète. La consultation n'émet aucun rapport HID et ne demande aucune capture.
