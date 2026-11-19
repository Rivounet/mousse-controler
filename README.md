# Mousse-controler

Contrôle de la souris de **MonOrdinateur** depuis **mini-pc-backend**. Transport prioritaire : **Bluetooth LE HID (HOGP)**, reconnu par les pilotes Windows natifs ; retour de position réelle par **agent Windows visible et canal LAN privé sécurisé**.

> **État : développement MC-HID-EXEC-001 cadré, non qualifié de bout en bout.** La création locale non diffusée des services GATT HID/Battery a réussi radio temporairement activée ; publicité, appairage, reconnaissance souris, mouvement et retour LAN intégrés restent à démontrer.

## Rôles et architecture

- **mini-pc-backend** : Codex unique, Git, développement, moteur HOGP C++/WinRT, contrôleur Python, moteur de trajectoires/séquences, boucle de correction et réception HTTPS des positions.
- **MonOrdinateur** : hôte HID Bluetooth natif ; **agent C# .NET Framework 4.8 visible**, limité à GetCursorPos/topologie/session et à l'envoi sortant des mesures via HTTPS authentifié. Il n'exécute aucune commande souris.
- **GitHub** : source officielle. Le récepteur USB Logitech Nano 046D:C534 reste indépendant et hors périmètre de la commande Mousse-controler.

```text
mini-pc-backend : séquences/zones → trajectoires → contrôle de position → HOGP BLE
                                                                │
                                                    MonOrdinateur : HID natif
                                                                │
mini-pc-backend : mesures réelles ← HTTPS/HMAC LAN privé ← agent GetCursorPos
```

## Fonctionnalités demandées (non encore démontrées)

- Séquence de zones **A → B → C → …** ; rectangles, cercles et polygones ; sélection d'un point aléatoire **à l'intérieur** de chaque zone, avec graine déterministe pour les tests.
- Trajectoires courbes, vitesse configurable avec accélération/décélération et micro-variations bornées **uniquement en mouvement**.
- Arrivée vérifiée par **mesure réelle** ; correction HID relative, interruption si mesure périmée, changement de session/topologie ou perte de lien.
- Après arrivée : attente configurable puis progression automatique **ou** attente d'une nouvelle commande ; pause, reprise, étape suivante et arrêt.
- Clics, boutons, défilement et arrêt d'urgence. Les paramètres de mouvement servent à la fluidité et au contrôle, **pas à masquer l'automatisation ni à usurper l'identité Logitech**.

Le système n'est pas garanti indiscernable d'une utilisation humaine. L'analyse d'écran et la prise de décision applicative autonome restent hors périmètre.

## État Git et qualification

- PR #4 de consolidation fusionnée dans `main` (merge `d74e13e9a1af502a952d7cfdedf4aef5b0ec7473`) ; PR #1–#3 clôturées sans fusion directe.
- PR #5 Draft : audits MC-HID-AUDIT-001/002, **non fusionnée** ; résultats et scripts présents sur sa branche, à intégrer sans écrasement.
- Audits : radio mini-PC On temporaire, fournisseurs HID/Battery et caractéristiques GATT créés avec succès sans publicité, puis radio restaurée Off. Service Device Information réservé : `DisabledByPolicy`.
- Audit de MonOrdinateur : lecture locale de position et deux écrans confirmés ; intégration réseau et Bluetooth HID réel non qualifiés.
- Les **79 tests** sont déclarés réussis dans le dernier compte rendu d'audit de la PR #5 ; ne pas les attribuer à la suite actuelle de `main` sans réexécution.

## Documentation

[Reprise](docs/REPRISE.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) · [Planning](docs/PLANNING.md) · [Tests](docs/TESTS.md) · [Décisions](docs/DECISIONS.md) · [Consignes Codex](AGENTS.md).

Les **mandats complets restent dans le chat** ; les documents GitHub consignent les décisions et exigences. Aucune fusion implicite.
