# Reprise — Mousse-controler

**État documentaire : 20 novembre 2026.** Les mandats complets sont fournis dans le chat, jamais archivés dans GitHub.

## Objectif actuel

Codex **sur mini-pc-backend** pilote un mandat global **MC-HID-EXEC-001** : faire reconnaître le mini-PC comme souris Bluetooth LE HOGP sur **MonOrdinateur**, contrôler mouvements/clics/défilement, recevoir la position réelle via un **agent Windows visible sortant sur LAN HTTPS sécurisé**, et exécuter des séquences de zones avec trajectoires et correction de position.

L'agent cible lit `GetCursorPos`, la topologie et la session ; **il n'exécute aucune commande souris**. Le récepteur USB Logitech Nano est hors périmètre. Pas d'analyse d'écran ni de prise de décision applicative autonome.

**État courant :** réalisation et qualification terminées dans la PR #6 Draft,
branche `feat/mc-hid-exec-001`, non fusionnée. Verdict
`PASS_WITH_RESERVATIONS`; les corrections finales de concurrence et la
réconciliation documentaire précèdent l'arbitrage de fusion.

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
- PR #6 MC-HID-EXEC-001 : **Draft ouverte, base main, non fusionnée** ; HOGP,
  retour LAN, fonctions souris, trajectoires/séquences, AtLogOn, reconnexion et
  performances qualifiés. SHA de référence avant corrections finales :
  `751f75dfe2486ad630364fe7a072a8c06dd08b83`.

## Historique avant réalisation — preuves des audits

Les constats de cette section décrivent l'état des PR #4/#5 avant la PR #6 ; ils
sont conservés pour la traçabilité et ne doivent pas être lus comme l'état
courant.

- mini-PC Windows 11 Pro 26H2, Realtek ; radio Bluetooth temporairement activée et **HID/Battery GATT + caractéristiques et Report Reference créés sans publicité** ; radio restaurée Off. Device Information `0x180A` : `DisabledByPolicy` (service réservé).
- Sur la branche de PR #5, Codex déclare **79 tests PASS** ; pas de nouvelle exécution indépendante sur main.
- MonOrdinateur : Windows 11 Famille, Logitech MR0085 / récepteur Nano `046D:C534` propriétaire non Bluetooth ; lecture de curseur `GetCursorPos` et deux écrans 1920×1080 observés lors de l'audit USB.
- **Non démontré** : publicité BLE, appairage, chargement pilote souris HID, mouvement depuis mini-PC, canal HTTPS/HMAC réel, positionnement précis, trajectoires exécutées.
- Accès distant depuis mini-PC à MonOrdinateur : aucun canal natif utilisable trouvé lors de l'audit ; établir/qualifier un accès authentifié, sans présumer d'un accès à la session graphique.

## Plan historique avant réalisation

Codex sur mini-pc-backend : vérifier Git et PR #5, sécuriser l'accès autorisé à MonOrdinateur, installer MSVC/Windows SDK nécessaires, développer et tester HOGP, agent position LAN, contrôleur Python, moteurs de trajectoires et séquences ; démontrer la boucle réelle et publier une **PR Draft unique**. Essais matériels supervisés, arrêt d'urgence, modifications réversibles. Pas de fusion implicite.

## Constats historiques de faisabilité

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

## État historique réalisé, simulé et non qualifié

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

## Porte historique avant autorisation d'exécution

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

## Historique de la qualification initiale MC-HID-EXEC-001

Cette section conserve l'échec initial d'appairage et le nettoyage intermédiaire.
Elle est supersédée par l'état qualifié courant ci-dessous.

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

## État qualifié courant — 20 novembre 2026

### Correction de reconnexion — 20 novembre 2026

L'appairage `ConfirmOnly` chiffré, la souris HID native et le mouvement minimal
sont démontrés. La paire persistait après recréation du fournisseur, mais
Windows ne rouvrait pas spontanément le service GATT. L'agent cible sélectionne
désormais l'endpoint exact déjà appairé et ouvre l'unique service HID sans cache.
Le MSIX 1.0.0.2 a retrouvé `subscribed=True` en 14,276 s après recréation
complète, sans nouvel appairage ni rejeu. Deux redémarrages de MonOrdinateur et
un redémarrage du mini-PC ont ensuite conservé la paire ; les tâches interactives
`AtLogOn` relancent les composants après ouverture manuelle de session.

Le retour de position HTTPS/HMAC est opérationnel. Mouvements, clics gauche et
droit, défilement, rectangle, cercle, polygone, trajectoires, attentes,
pause/reprise et arrêt d'urgence ont été qualifiés sur surface sûre. Sur 100
mouvements : réussite 100 %, médiane 670,483 ms, P95 983,052 ms, erreur moyenne
0,796 px et maximum 2 px.

L'arrêt d'urgence partage désormais son verrou avec toutes les émissions HID.
Une commande en attente revalide l'état avant transport, l'arrêt répété n'émet
rien et une reprise explicite ouvre une nouvelle époque de commandes. Les
réserves restantes sont la mesure LAN aller simple sans horloges synchronisées
et la reprise GATT transitoire avant convergence automatique. La PR #6 reste
Draft et non fusionnée.

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Planning](PLANNING.md) · [Tests](TESTS.md) · [Décisions](DECISIONS.md) · [Consignes Codex](../AGENTS.md) · [PR #6](https://github.com/Rivounet/mousse-controler/pull/6).

## Gouvernance

D-021 : mandats dans le chat. D-022 : pas de revue exhaustive systématique. D-023 : autonomie orientée résultats, avec limites d'autorisation. Toute fusion requiert un accord explicite.
