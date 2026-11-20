# Stratégie de tests et qualification

## Référence

```powershell
python -m unittest discover
```

MC-REPRISE-001 a corrigé la découverte depuis la racine : la commande exécutait
72 tests au lieu d'en annoncer zéro. MC-HID-AUDIT-001/002 ajoutent sept gardes ;
le 19 novembre 2026, les **79 tests** ont réussi sur mini-pc-backend après le
cycle radio temporaire, avec un chemin temporaire court.

La suite couvre 69 tests historiques d'artefacts, releases, chemins, erreurs,
verrous et client distant hors ligne, trois tests du diagnostic Bluetooth et
sept tests du diagnostic cible/gardes anti-publicité et de restauration radio.
Elle ne crée pas de
publicité et n'émet aucun rapport HID.

La PR #4 a livré 72 tests réussis selon MC-REPRISE-001. La PR #5 a déclaré **79 tests réussis** après les audits radio, mais elle reste Draft ; ne pas attribuer ce total à `main` sans réexécution.

## Matrice de qualification

| Niveau | Vérifications | Statut |
|---|---|---|
| T0 | cohérence Git, syntaxe et documentation | PASS dans la PR #6 |
| T1 | Unités, géométrie, trajectoires, séquences, sécurité et adaptateurs simulés | PASS ; suite complète courante |
| T2 | Séquences A→B→C, modes temporisé/commandé, pause/reprise/étape suivante/arrêt, état et non-rejeu | PASS simulé et matériel ciblé |
| T3 | HOGP GATT, publicité, pairing, chiffrement, pilote HID natif, mouvement/clic/scroll et relâchement boutons | PASS matériel |
| T4 | Agent GetCursorPos, topologie/DPI/session, HTTPS épinglé/HMAC, anti-rejeu et mesures fraîches | PASS ; latence aller simple réservée faute d'horloges synchronisées |
| T5 | Correction par feedback réel, arrivée dans zone, vitesse, latence, arrêt d'urgence et reconnexion | PASS_WITH_RESERVATIONS |

## Critères d'acceptation

- **Souris HID native** reconnue sur MonOrdinateur, sans pilote personnalisé sur la cible ; rapport HID réel observé.
- **Retour réel** de coordonnées physiques signées par agent visible ; horodatage, source, session et génération topologique.
- **Séquences** de zones A→B→C ; les trois géométries ; point cible tiré dans le périmètre ; trajectoires courbes, vitesse variable et micro-variations bornées pendant mouvement seulement.
- **Modes** : délai configurable ou commande explicite, avec pause/reprise/arrêt sans rejeu.
- **Performances démontrées** : 100/100 mouvements, médiane 670,483 ms,
  P95 983,052 ms, erreur moyenne 0,796 px et maximum 2 px.
- **Sécurité** : arrêt d'urgence, commandes TTL/idempotentes, relâchement boutons, pas de commande via l'agent cible, aucune donnée sensible publiée.

Distinguer les tests simulés, locaux et **observés sur les deux machines**. Une compilation ou un test simulé ne valide pas le fonctionnement réel. La qualification ne vise ni l'usurpation Logitech ni l'évasion de détection d'automatisation.

Le probe historique `scripts/bluetooth/probe-gatt-shape.ps1` ne constituait pas
la porte 2 : il créait la forme locale sans `StartAdvertising`. La qualification
ultérieure de la PR #6 a exécuté le diagnostic cible puis démontré séparément la
publicité, l'association et le fonctionnement HID réel.

## Acceptation MVP

- MonOrdinateur reconnaît une souris Bluetooth native après appairage ;
- agent cible limité au retour de position, visible et incapable de recevoir une
  commande souris ;
- mouvement relatif, clic gauche/droit et défilement via un client autorisé ;
- aucune commande invalide ou expirée émise ;
- reconnexion sans rejeu de commandes obsolètes ;
- arrêt d'urgence mesuré, publicité arrêtée et souris physique disponible ;
- API non exposée publiquement ;
- activation par SHA et rollback reproductibles sur mini-pc-backend.

## Compte rendu d'un lot

Indiquer branche et SHA, machine, commandes, total de tests, durée, PASS/FAIL,
opérations non exécutées, effets Bluetooth éventuels, arrêt/rollback et preuves
expurgées. Ne publier ni adresses Bluetooth, identifiants matériels uniques,
comptes, chemins personnels, secrets ou journaux privés.

La revue de code approfondie reste sur demande ou au jalon convenu ; livraison
d'une PR Draft ne signifie ni validation, ni fusion.

## Chronologie historique MC-HID-EXEC-001

Le 20 novembre 2026, `python -m unittest discover -v` a exécuté **103 tests en
60,365 s : 103 PASS**. Les 24 tests ajoutés couvrent :

- transport simulé, fraîcheur, correction et changements session/topologie ;
- HMAC, anti-rejeu, horodatage et réception bornée ;
- rectangle, cercle, polygone, graine et invalidation hors topologie ;
- courbe, accélération/décélération, variation de vitesse et absence de jitter
  à l'arrêt ;
- A→B→C, attente automatique/commandée, pause/reprise, stop et absence de HID
  après arrêt ;
- API loopback, bearer constant-time, TTL et idempotence.

À ce jalon intermédiaire, les preuves réelles obtenues étaient : agent session console 1, deux écrans, échantillon
HTTPS signé, appairage chiffré, pilote HID/souris natif, rapports relatifs et
reconnexion après recréation du fournisseur en 14,276 s. Non qualifiés :
redémarrages matériels, clic/scroll sur surface sûre, précision, P95,
multi-écrans en trajectoire et arrêt matériel. Le statut global demeure donc
`INCOMPLETE`.

Après ajout de l'hôte MSIX compatible Smart App Control et de son routage par le
transport Python, la suite a exécuté **105 tests en 52,869 s : 105 PASS**, puis
une revalidation complète **105/105 en 80,412 s**. Les
deux tests supplémentaires vérifient la commande de l'alias packagé et la
compatibilité du contrat historique direct.

Après correction de la pairabilité et de la reconnexion, la suite complète a
exécuté **115/115 tests en 78,087 s**. Le chemin court `MC_TEST_TMP` est requis
pour les tests de déploiement sous la limite de chemins Windows.

La finalisation de performance a porté la suite à **127/127 PASS en 41,984 s**.
Les nouveaux tests couvrent l'amplitude adaptative et son plafond explicite, le
plafond configurable des trajectoires, les métriques de position et la
télémétrie récepteur. Sur matériel réel, la matrice stable comporte 100/100
arrivées, médiane 670,483 ms, P95 983,052 ms et erreur maximale 2 px.

## Corrections finales avant fusion

Les tests déterministes de concurrence couvrent mouvement, clic, défilement et
commande boutons en attente du verrou, reconnexion concurrente à l'arrêt, clic
déjà engagé, arrêt répété et reprise explicite. Ils vérifient la liste exacte des
événements reçus par `SimulatedHidTransport` : aucune émission ne suit l'arrêt
effectif, les boutons sont libérés avant `stop`, et `start()` ouvre seul une
nouvelle époque. La qualification matérielle antérieure n'est pas répétée car le
protocole et l'algorithme de mouvement ne changent pas.

Après ajout du nettoyage d'un démarrage transport partiel, la suite finale a
exécuté **136/136 tests en 35,659 s : PASS** hors du chemin temporaire long du
bac à sable.

## Revalidation post-fusion

Le 20 novembre 2026, après synchronisation de `main` sur le commit de fusion
`77d4a5939673053fa2e0dae73bc3a284a8597ac7`, la commande de référence a
réexécuté **136/136 tests en 37,648 s : PASS**. Le contrôleur rechargé depuis ce
contenu a ensuite confirmé, sans mouvement de souris : publicité HOGP
`Started`, abonnement HID actif, boutons à zéro, API locale accessible et
position distante HTTPS/HMAC fraîche.
La branche documentaire post-fusion a ensuite exécuté la même suite :
**136/136 tests en 38,938 s : PASS**.

Les livraisons Codex sont publiées en PR Draft avec SHA, tests, durées, résultats et preuves expurgées. Pas de revue de code exhaustive automatique ; fusion sur autorisation.

## Critères de qualification futurs — MC-MOUSE-ACTIONS-001

- Clics simple/double/triple, maintien, glisser-déposer, boutons et roulette verticale/horizontale selon HID ; relâchement sur arrêt.
- Composition en séquences, attente, pause/reprise, erreur configurable, absence de rejeu après reconnexion.
- Identifiants et notifications WebSocket authentifiées, états cohérents et distinction entre émission HID et effet observé.
- Capture uniquement avant/après une action configurée ; aucun déclenchement permanent ou indépendant ; sélection du moniteur sous curseur au moment de la capture, y compris multi-écrans.
- Transfert LAN protégé, intégrité, quotas, stockage et rétention par action/séquence, absence de fuite de captures dans les logs ou GitHub.
- Arrêt d'urgence prioritaire ; échec de capture sans répétition de l'action souris ; tests logiciels et matériels sur surface sûre.

Ces critères sont planifiés, pas encore qualifiés. Référence MVP avant J6 : 136 tests réussis, 100/100 mouvements réels.
