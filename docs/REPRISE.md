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

Le matériel retourne `true` pour BLE, le rôle périphérique et le rôle central.
Les API WinRT de serveur GATT, création de caractéristiques, notification,
publicité et appairage sont présentes. La documentation Microsoft et la
spécification Bluetooth SIG rendent une implémentation HOGP crédible.

**Verdict : `GO_WITH_RESERVATIONS`.** Aucun service GATT n'a été créé, aucune
publicité démarrée, aucun appairage effectué et aucun événement HID émis. Ces
étapes sont indispensables avant `GO`.

MC-HID-AUDIT-001 a défini l'architecture deux canaux et le plan de réalisation.
Son probe GATT non diffusé a trouvé la radio `Off` et a reçu
`RadioNotAvailable` ; aucune opération sensible n'a été exécutée. MonOrdinateur
n'était pas accessible : son script de diagnostic est prêt, mais ses
caractéristiques restent inconnues.

MC-HID-AUDIT-002 a confirmé que Realtek/PnP/pilote/services sont sains et que
`Off` causait `RadioNotAvailable` : radio On temporaire, HID/Battery,
caractéristiques HID et Report Reference créés avec succès sans publicité ;
Device Information réservé retourne `DisabledByPolicy`. Toutes les ressources
ont été libérées et l'état final `Off` confirmé. Aucun accès natif à
MonOrdinateur n'est configuré depuis le mini-PC ; la cible reste `INCOMPLETE`.

## Réalisé, simulé, non qualifié

| Domaine | État |
|---|---|
| Inventaire local et diagnostic Bluetooth | Réalisé en lecture seule |
| Consolidation des trois PR historiques | Réalisée localement, publication à finaliser |
| Tests artefacts/releases/distant hors ligne | 69 PASS |
| Tests diagnostics Bluetooth/cible et gardes de restauration | 10 PASS |
| Release locale et rollback | Modèle et tests présents ; activation applicative réelle à requalifier |
| SSH/SFTP | Qualifié historiquement, non relancé dans la nouvelle organisation |
| Forme GATT HID/Battery non diffusée | Créée avec succès puis libérée |
| Publicité, bonding, pilote souris, mouvement | Non exécutés — autorisation requise |
| API de commandes | Non développée |

## Prochaine action

Décider l'autorisation du
[`PROTOCOLE-HID.md`](../qualification/MC-REPRISE-001/PROTOCOLE-HID.md). Il
prévoit un prototype au premier plan, arrêt par `Ctrl+C` avec
`StopAdvertising()`, appairage volontaire et mouvement de cinq pixels dans une
surface sûre. Sans autorisation, ne pas passer au développement complexe de
l'API. Exécuter auparavant le diagnostic cible et arbitrer les décisions de
[`MC-HID-AUDIT-001`](../qualification/MC-HID-AUDIT-001/DECISIONS.md).
Les portes complémentaires sont décrites dans
[`MC-HID-AUDIT-002`](../qualification/MC-HID-AUDIT-002/RAPPORT.md).

## Sources de vérité

- [Rapport MC-REPRISE-001](../qualification/MC-REPRISE-001/RAPPORT.md)
- [Audit MC-HID-AUDIT-001](../qualification/MC-HID-AUDIT-001/RAPPORT.md)
- [Complément MC-HID-AUDIT-002](../qualification/MC-HID-AUDIT-002/RAPPORT.md)
- [Roadmap](ROADMAP.md) et [planning](PLANNING.md)
- [Architecture](ARCHITECTURE.md)
- [Déploiement local](DEPLOIEMENT.md)
- [Accès distant secondaire](ACCES-DISTANT-ET-SYNCHRONISATION.md)
- [Tests](TESTS.md), [décisions](DECISIONS.md) et [consignes Codex](../AGENTS.md)

## Gouvernance

D-021 : mandats exclusivement dans le chat. D-022 : pas de revue automatique à
chaque livraison. D-023 : autonomie technique de Codex dans les limites
explicites. Aucune fusion, publicité Bluetooth, modification système ou émission
HID n'est implicite.

## Reprise MC-HID-EXEC-001 — 20 novembre 2026

- branche de travail : `feat/mc-hid-exec-001`, sans fusion ;
- Build Tools 17.14.45, MSVC 14.44 et SDK 10.0.26100 installés ;
- moteur HOGP, contrôleur Python, API locale, canal HTTPS/HMAC, agent .NET 4.8,
  zones/trajectoires/séquences et paquet MSIX implémentés ;
- accès cible : OpenSSH existant à clé et host key stricte, jamais RustDesk ;
- agent cible visible qualifié en session 1, deux écrans et premier échantillon
  accepté ; tâche ensuite arrêtée et supprimée ;
- tests : 105/105 PASS ;
- radios finales : mini-PC `On` (état initial), cible restaurée `Off` ;
- HOGP packagé : certificat, signature, Publisher et SHA vérifiés ; import public
  temporaire dans `LocalMachine\TrustedPeople`, MSIX installé, identité
  `WindowsApps` confirmée, GATT créé et publicité stabilisée `status=2` après un
  `Aborted` transitoire ;
- appairage : quatrième tentative sous identité MSIX, `ConfirmOnly` accepté en
  session 1, résultat `Failed`, protection utilisée `None`, aucune paire ni
  rapport HID ;
- nettoyage : publicité/processus/MSIX/règle/tâches/répertoire cible retirés ;
  certificat temporaire `LocalMachine\TrustedPeople` retiré ; copie exacte
  trouvée dans `CurrentUser\Root` également retirée par empreinte après
  diagnostic des sessions RDP 7/console 6 ; aucun magasin Root ne la conserve ;
- verdict provisoire : `INCOMPLETE`, pas PASS.

La course `Aborted` → `StartedWithoutAllAdvertisementData` du démarrage est
corrigée et compilée, mais pas requalifiée dans un nouveau MSIX après nettoyage.
À la reprise, instrumenter l'échec de bonding sans abaisser l'exigence
`Encryption`. Ne retenter mouvement, clic/scroll ou batterie complète qu'après
pairing et abonnement HID natif.

## Références actuelles

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Planning](PLANNING.md) · [Tests](TESTS.md) · [Décisions](DECISIONS.md) · [Consignes Codex](../AGENTS.md) · [PR #5](https://github.com/Rivounet/mousse-controler/pull/5).

## Gouvernance

D-021 : mandats dans le chat. D-022 : pas de revue exhaustive systématique. D-023 : autonomie orientée résultats, avec limites d'autorisation. Toute fusion requiert un accord explicite.
