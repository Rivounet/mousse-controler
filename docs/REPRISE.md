# Reprise — Mousse-controler

**État documentaire : 20 novembre 2026.** Les mandats complets sont fournis dans le chat, jamais archivés dans GitHub.

## Objectif actuel

Codex **sur mini-pc-backend** pilote un mandat global **MC-HID-EXEC-001** : faire reconnaître le mini-PC comme souris Bluetooth LE HOGP sur **MonOrdinateur**, contrôler mouvements/clics/défilement, recevoir la position réelle via un **agent Windows visible sortant sur LAN HTTPS sécurisé**, et exécuter des séquences de zones avec trajectoires et correction de position.

L'agent cible lit `GetCursorPos`, la topologie et la session ; **il n'exécute aucune commande souris**. Le récepteur USB Logitech Nano est hors périmètre. Pas d'analyse d'écran ni de prise de décision applicative autonome.

**État courant :** réalisation et qualification terminées, puis fusionnées dans
`main` par la PR #6 au commit
`77d4a5939673053fa2e0dae73bc3a284a8597ac7`. Verdict conservé :
`PASS_WITH_RESERVATIONS`.

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
- PR #6 MC-HID-EXEC-001 : **fusionnée dans `main`** le 20 novembre 2026 au
  commit `77d4a5939673053fa2e0dae73bc3a284a8597ac7` ; HOGP, retour LAN,
  fonctions souris, trajectoires/séquences, AtLogOn, reconnexion et performances
  qualifiés. SHA de référence avant corrections finales :
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
et la reprise GATT transitoire avant convergence automatique. La PR #6 a depuis
été fusionnée dans `main` au commit
`77d4a5939673053fa2e0dae73bc3a284a8597ac7`.

[Architecture](ARCHITECTURE.md) · [Roadmap](ROADMAP.md) · [Planning](PLANNING.md) · [Tests](TESTS.md) · [Décisions](DECISIONS.md) · [Consignes Codex](../AGENTS.md) · [PR #6](https://github.com/Rivounet/mousse-controler/pull/6).

## Gouvernance

D-021 : mandats dans le chat. D-022 : pas de revue exhaustive systématique. D-023 : autonomie orientée résultats, avec limites d'autorisation. Toute fusion requiert un accord explicite.

## Nouveau chantier validé — MC-MOUSE-ACTIONS-001

**20 novembre 2026 — planifié, non développé.** Le MVP est fusionné (PR #6), la consolidation documentaire également (PR #7). Le verdict existant reste PASS_WITH_RESERVATIONS.

Souris uniquement, sans clavier : clics multiples, maintien, glisser-déposer, boutons compatibles, roulette, actions composables. Résultats d'action corrélés par identifiant et transmis automatiquement par WebSocket (4B). Capture optionnelle avant/après action si activée (1B), jamais continue : écran entier contenant le curseur au moment de la capture. Conservation configurable par action/séquence (3C). Analyse locale future préparée, non implémentée (2C). Erreurs configurables arrêt/retry/poursuite, arrêt par défaut (5C), sans rejeu automatique d'action incertaine.

Conserver Bluetooth HID pour les commandes et LAN sécurisé pour retour et captures. Agent cible visible limité aux mesures/captures, sans exécution de commandes souris. Codex sur mini-pc-backend développe dans une seule PR Draft, sans fusion automatique. Voir roadmap/planning ; mandat intégral dans le chat.

### État final du chantier — qualification du 20 novembre 2026

**Verdict : PASS_WITH_RESERVATIONS, PR #8 Draft non fusionnée.** Branche `feat/mc-mouse-actions-001`, SHA technique qualifié initialement `92817a7d802c0d2c0d22b4502071a3dc4a994c19`; base `main` `4b5e80450931a19adb88312d6f6a3b0ff8e4fd81`. Les modifications documentaires de consolidation ultérieures ne constituent pas une nouvelle qualification exécutable.

- Logiciel : **177/177 tests PASS en 44,286 s**, compilation Python et builds Roslyn C# avec warnings-as-errors.
- Matériel réel : **17 actions souris réussies** dans la surface témoin sûre ; cinq boutons, clics multiples, combinaison, maintien, glisser confirmé, mouvements, roulette verticale et séquence. Témoin : **37 événements** dans la surface sûre.
- Suivi : événements WebSocket corrélés et identifiants uniques. `CONFIRMED` réservé aux positions observées, `EXECUTED` aux clics/boutons/roulette.
- Captures ponctuelles avant/après : deux PNG réels **1920×1080**, seuls des recadrages de preuve **884×611** conservés dans `qualification/MC-MOUSE-ACTIONS-001/evidence/`. Captures sources plein écran supprimées. Aucun flux continu ni analyse visuelle.
- Sécurité : arrêt d'urgence annule l'action en attente (`CANCELLED`), **zéro événement post-arrêt** ; après reconnexion, HOGP `Started`, `subscribed=True`, boutons 0, aucun rejeu et aucune action en cours.
- SSH : connexion via l'alias **exact `MonOrdinateur`** et le fichier dédié `~/.ssh/monordinateur-pv-mig.conf`, refus réseau en sandbox et réussite hors sandbox avec une approbation persistante strictement limitée. SSH session 0 ; console/agent/témoin session 1. Tâche temporaire interactive contrôlée, sans changements d'ACL, compte, pare-feu ou protection.
- Nettoyage : témoin/tâche/staging interactif supprimés, production `Running` en session 1, souris libérée. Dossier de staging de maintenance **vide** encore présent sous Windows Temp (suppression refusée, aucune élévation réalisée).
- **Réserves** : roulette horizontale indisponible car `AC Pan` absent du descripteur HID déjà appairé ; dossier vide résiduel ; toute nouvelle prise de souris pour qualification exige annonce préalable et accord explicite. Réserves historiques du MVP : mesure LAN aller simple absolue et reprise GATT transitoire.
- Preuves : [rapport J6](../qualification/MC-MOUSE-ACTIONS-001/RAPPORT.md), `evidence/hardware-summary.json` et `evidence/ssh-summary.json`. Pas de CI GitHub configurée ; tests exécutés sur les machines, pas dans un workflow distant.

**Prochaine porte :** suivi documentaire et décision explicite de revue/fusion de la [PR #8](https://github.com/Rivounet/mousse-controler/pull/8). Ne pas annoncer le code J6 comme intégré à `main` avant fusion. Codex reste responsable de l'exécution ; ChatGPT maintient la documentation et pilote l'arbitrage GitHub. Les mandats complets restent dans le chat.

### Clôture de revue ciblée — correctifs de sûreté (20 novembre 2026)

**SHA logiciel revu :** `e7e26332e56a39cbd2ca915413c313da07c638d9`, PR #8 toujours Draft, non fusionnée. Deux anomalies identifiées pendant la revue ont reçu des correctifs :

- Capture : `DELETED` exige la disparition constatée du fichier ; `DELETE_FAILED` est conservé par index persistant, les fichiers sont comptabilisés dans les quotas, le redémarrage réconcilie les orphelins et une suppression refusée est retentable.
- Actions : registre durable `<action_journal>.ids` ; les identifiants demeurent réservés malgré éviction, saturation, compaction, redémarrage et reconnexion ; rétention anti-rejeu **30 jours par défaut**, configurable, avec expiration seulement après éviction de l'état. Le journal et le fichier `.ids` doivent être sauvegardés/restaurés ensemble.

**Validation Codex déclarée et publiée :** 17/17 tests ciblés PASS et 185/185 tests complets PASS en 54,007 s. Aucune nouvelle prise de souris, émission HID ni capture réelle. Les preuves matérielles qualifiées au SHA précédent restent valides pour les composants non retouchés ; le correctif logiciel récent n'a pas été requalifié sur la souris réelle. Pas de CI GitHub configurée.

**État de pilotage :** revue ciblée favorable sur les deux corrections ; aucune fusion sans autorisation explicite. Après fusion autorisée, mettre à jour planning/roadmap/reprise sur `main` et qualifier la synchronisation locale sans prise de souris non approuvée.

### Fusion J6 confirmée — 20 novembre 2026

La PR #8 MC-MOUSE-ACTIONS-001 est **MERGED** dans `main` au commit `e0658142a65d8b494f109efa3318c6ea21feac3d` (autorisation explicite de l'utilisateur). Le dernier SHA de branche fusionné est `578acf976e3ce00a4f01142aaedad243bb19284a`, les corrections applicatives qualifiées sont au SHA `e7e26332e56a39cbd2ca915413c313da07c638d9`. **J6 intégré, PASS_WITH_RESERVATIONS**. Tests Codex 185/185 PASS ; les essais matériels antérieurs couvrent 17 actions et 37 événements, sans nouvelle émission HID après les corrections. Pas de CI GitHub configurée. La fusion Git ne prouve pas à elle seule la synchronisation du clone ou des processus en cours sur mini-pc-backend ; contrôler les SHA locaux avant tout redéploiement, sans prise de souris non autorisée. Les réserves restent ouvertes : roulette horizontale sans AC Pan, dossier temporaire vide résiduel, accord préalable pour toute prise de souris.

### Qualification post-fusion MC-POST-MERGE-002 — 20 novembre 2026

`main` local et GitHub concordent au SHA
`09fa2fe475cc70c9bdaf375fffc684195207161b`. Le contrôleur mini-PC a été
rechargé depuis ce contenu : GATT annoncé et abonné, boutons zéro, position
fraîche, WebSocket authentifié et registre anti-rejeu `.ids` migré avec le
journal. `MonOrdinateur` conserve l'agent qualifié exact en session interactive
et son rollback ; aucune mise à jour cible n'a été nécessaire. Suite 185/185
PASS, test runtime limité à une attente sans HID, aucune capture réelle.
Verdict : `PASS_WITH_RESERVATIONS`. Voir le
[rapport post-fusion](../qualification/MC-POST-MERGE-002/RAPPORT.md).

### Chantier actif — MC-API-CATALOG-001

Branche `feat/mc-api-catalog-001`, base `main`
`97d81346304b1234b77ae5a8dfe35cb63e787ad6`. Le registre central contient 28
commandes, 12 types d'actions et 6 événements WebSocket. `api_catalog` est
authentifié sur le endpoint loopback existant ; le routage et la validation
statique consomment la même déclaration. La référence est générée dans
`docs/API-REFERENCE.md` et vérifiable avec
`python scripts/generate_api_reference.py --check`.

Qualification : **195/195 PASS en 67,411 s** avec `MC_TEST_TMP` court ; 10 tests
nouveaux couvrent exhaustivité, absence de fantômes, filtres, schémas, exemples,
erreurs, authentification, compatibilité et absence d'effet HID/capture. Aucun
matériel réel n'a été sollicité. État de reprise : publier une PR Draft unique,
joindre le rapport expurgé, ne pas fusionner et ne pas modifier la production.
