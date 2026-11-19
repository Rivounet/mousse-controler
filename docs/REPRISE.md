# Reprise — Mousse-controler

**État documentaire : 19 novembre 2026.** Les mandats complets sont fournis dans le chat, jamais archivés dans GitHub.

## Objectif actuel

Codex **sur mini-pc-backend** pilote un mandat global **MC-HID-EXEC-001** : faire reconnaître le mini-PC comme souris Bluetooth LE HOGP sur **MonOrdinateur**, contrôler mouvements/clics/défilement, recevoir la position réelle via un **agent Windows visible sortant sur LAN HTTPS sécurisé**, et exécuter des séquences de zones avec trajectoires et correction de position.

L'agent cible lit `GetCursorPos`, la topologie et la session ; **il n'exécute aucune commande souris**. Le récepteur USB Logitech Nano est hors périmètre. Pas d'analyse d'écran ni de prise de décision applicative autonome.

## Fonctionnalités validées pour réalisation

- Séquences **A→B→C→…**, zones **rectangle, cercle, polygone** ; point aléatoire à l'intérieur de chaque zone.
- Trajectoires courbes, vitesse variable (accélération/décélération) et micro-variations bornées **uniquement pendant les déplacements**.
- Vérification d'arrivée par retour de position réelle et correction HID ; jamais de mesure estimée présentée comme réelle.
- Après chaque cible : **temporisation configurable ou attente d'une commande**, combinables dans une séquence ; pause, reprise, étape suivante et arrêt.
- Reconnaissance HID native privilégiée ; aucune usurpation de signature Logitech ni garantie d'indétectabilité.

## État GitHub

- PR #4 MC-REPRISE-001 **fusionnée** dans `main` (merge `d74e13e9a1af502a952d7cfdedf4aef5b0ec7473`).
- PR #1–#3 **clôturées sans fusion directe** ; branches conservées.
- PR #5 MC-HID-AUDIT-001/002 : **Draft, base main, non fusionnée**, dernier SHA connu `275571182aac2b17d2c6f0092a78470a3f14e5a9`. Ses scripts et rapports ne sont pas nécessairement présents dans `main` : récupérer depuis sa branche sans écrasement.
- MC-HID-EXEC-001 : mandat élargi à l'accès autorisé aux deux machines et au moteur de trajectoires. **Aucune livraison de ce mandat n'est confirmée ici.**

## Preuves techniques et réserves

- mini-PC Windows 11 Pro 26H2, Realtek ; radio Bluetooth temporairement activée et **HID/Battery GATT + caractéristiques et Report Reference créés sans publicité** ; radio restaurée Off. Device Information `0x180A` : `DisabledByPolicy` (service réservé).
- Sur la branche de PR #5, Codex déclare **79 tests PASS** ; pas de nouvelle exécution indépendante sur main.
- MonOrdinateur : Windows 11 Famille, Logitech MR0085 / récepteur Nano `046D:C534` propriétaire non Bluetooth ; lecture de curseur `GetCursorPos` et deux écrans 1920×1080 observés lors de l'audit USB.
- **Non démontré** : publicité BLE, appairage, chargement pilote souris HID, mouvement depuis mini-PC, canal HTTPS/HMAC réel, positionnement précis, trajectoires exécutées.
- Accès distant depuis mini-PC à MonOrdinateur : aucun canal natif utilisable trouvé lors de l'audit ; établir/qualifier un accès authentifié, sans présumer d'un accès à la session graphique.

## Prochaine exécution

Codex sur mini-pc-backend : vérifier Git et PR #5, sécuriser l'accès autorisé à MonOrdinateur, installer MSVC/Windows SDK nécessaires, développer et tester HOGP, agent position LAN, contrôleur Python, moteurs de trajectoires et séquences ; démontrer la boucle réelle et publier une **PR Draft unique**. Essais matériels supervisés, arrêt d'urgence, modifications réversibles. Pas de fusion implicite.

## Références

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Planning](PLANNING.md) · [Tests](TESTS.md) · [Décisions](DECISIONS.md) · [Consignes Codex](../AGENTS.md) · [PR #5](https://github.com/Rivounet/mousse-controler/pull/5).

## Gouvernance

D-021 : mandats dans le chat. D-022 : pas de revue exhaustive systématique. D-023 : autonomie orientée résultats, avec limites d'autorisation. Toute fusion requiert un accord explicite.
