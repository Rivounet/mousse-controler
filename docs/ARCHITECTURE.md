# Architecture technique — état courant

L'état de robustesse, les preuves et les réserves sont centralisés dans
[ROBUSTESSE.md](ROBUSTESSE.md). Les sections datées ci-dessous décrivent les
étapes qui ont construit l'architecture ; elles ne remplacent pas cet état.

## Deux machines, deux canaux

```text
mini-pc-backend
  CommandGateway (authentification/TTL/idempotence)
    → SequenceEngine (zones, modes d'attente, pause/reprise/arrêt)
    → TrajectoryEngine (chemin courbe, vitesse, variations bornées)
    → PositionController (mesure fraîche, correction, limites)
    → IHogpTransport / moteur PowerShell/WinRT packagé MSIX
           │ Bluetooth LE HOGP
           ▼
PC cible Windows : pile Bluetooth et souris HID natives Windows
  PositionAgent visible (C# .NET Framework 4.8, session utilisateur)
           │ GetCursorPos / écrans / session / capture explicitement demandée
           └── HTTPS sortant + certificat épinglé + HMAC/anti-rejeu ──► mini-pc-backend
  HogpControlAgent distinct (optionnel, actions désactivées par défaut)
           │ état radio/PnP/HID + acquittements ; aucune API GATT/HID
           └── HTTPS sortant `/v1/hogp-control` ───────────────────────► plan de contrôle backend
```

## Couches et règles de dépendance

L'architecture conserve un seul processus mais sépare les responsabilités :

| Couche | Modules principaux | Responsabilité |
|---|---|---|
| Adaptateurs entrants | `command_server`, `position_server`, `event_server` | protocoles HTTP/WebSocket, authentification, enveloppes et sérialisation |
| Application | `application`, `orchestration`, `actions`, `sequence` | cas d'usage, cycle de vie, coordination et attribution exclusive du périphérique |
| Domaine | `geometry`, `trajectory`, types de `feedback` | règles pures, valeurs et invariants indépendants des protocoles |
| Infrastructure | `controller`, `transport`, `capture`, `dpapi`, `security` | HID, processus WinRT, stockage privé et primitives de sécurité |

`hogp_health` observe le provider sans le recréer lorsqu'un abonné manque.
`hogp_control` porte un plan de contrôle optionnel, authentifié et sans commande
souris. Le runtime cible correspondant est un exécutable séparé de
`PositionAgent`; partager le serveur HTTPS ne fusionne ni leurs clés, ni leurs
séquences, ni leurs responsabilités.
Chaque route possède son propre trousseau : la clé HOGP est refusée par
`/v1/position` et `/v1/capture`, et la clé de télémétrie est refusée par
`/v1/hogp-control`. Le démarrage refuse également deux identifiants dont le
matériau secret serait identique.

Les identités PnP sont aussi verrouillées par rôle : l'adaptateur doit être un
nœud Bluetooth sur bus matériel `USB` ou `PCI` (la cible qualifiée expose
`USB`), l'endpoint pairé appartient à `BTHLE\DEV_` et l'enfant HID à
`BTHLEDEVICE\`. Une empreinte correcte associée au mauvais rôle est refusée.

Les adaptateurs ne pilotent plus directement le contrôleur. Ils appellent
`MouseApplicationService`, qui partage un unique `OperationCoordinator` avec
`ActionExecutor` et `SequenceRunner`. Le bail couvre une opération logique
complète ; le verrou du contrôleur continue de protéger chaque émission. Les
commandes d'arrêt restent hors bail afin de toujours pouvoir interrompre le
propriétaire courant.

Le retour cible est publié par `PositionStore` sous forme d'un couple atomique
position/topologie de même génération. Aucun consommateur ne doit maintenir une
copie de topologie séparée ni combiner deux générations.

Le backend et la cible restent deux hôtes distincts. L'agent de position
s'exécute séparément dans la session interactive de la cible. Les anciens
canaux de maintenance de `MonOrdinateur` sont des preuves historiques et ne
qualifient pas `DESKTOP-NPIHO8K`.

## Contrats et limites

- **Zones** : rectangle (x,y,largeur,hauteur), cercle (centre,rayon), polygone (sommets). Validation géométrique, écrans virtuels et coordonnées signées. Point cible tiré aléatoirement dans la zone, graine configurable en test.
- **Séquences** : A→B→C… ; modes après arrivée : temporisation configurable ou commande explicite ; les deux peuvent coexister. États `IDLE`, `MOVING`, `ARRIVED`, `WAITING`, `PAUSED`, `COMPLETED`, `STOPPED`, `ERROR`.
- **Trajectoires** : courbes et points intermédiaires, profils d'accélération/décélération et vitesse variable, micro-variations bornées pendant le mouvement seulement. Paramètres configurables, pas d'usurpation Logitech ni de dissimulation d'automatisation.
- **PositionController** : une commande relative HID adaptative puis une mesure
  **réelle plus récente** ; amplitude rapide calibrée loin de la cible, correction
  fine plafonnée après dépassement, arrêt si donnée obsolète, session/topologie
  modifiée, écart concurrent anormal ou timeout. Ne jamais présenter une
  estimation comme une mesure.
- **IHogpTransport** : start/stop/state/send_relative/release_all ; HOGP conforme,
  pairage volontaire, chiffrement vérifié, exactement un abonné actif autorisé,
  notification ciblée, relâchement boutons et aucun rejeu après reconnexion.
  Doubles simulés pour tests.
- **Agent cible** : lit curseur, topologie, DPI et état de session ; publie les
  mesures et réalise seulement les captures avant/après explicitement liées à
  une action. Il ne reçoit aucune commande souris et n'est pas un service caché.
- **Agent de contrôle HOGP** : observe exclusivement les identités enrôlées et
  l'état Windows Bluetooth/PnP/HID. Une réponse API peut demander un unique
  redémarrage PnP borné si la politique backend et la politique locale
  l'autorisent, si le runtime est élevé et si toutes les empreintes concordent.
  Il utilise uniquement le sélecteur statique Windows des périphériques BLE
  déjà appairés, sans instancier `BluetoothLEDevice`, ouvrir `GattSession` ou
  découvrir un service GATT.
  Cet « agent cible » désigne le runtime applicatif déployé
  `HogpControlAgent.exe`, jamais l'agent Codex utilisé pour l'installation ou le
  diagnostic.
  Un acquittement persiste jusqu'à ce que le backend renvoie exactement son
  identifiant et son état ; une simple réponse HTTP corrélée ne suffit pas à
  l'effacer. Au chargement, il doit aussi référencer une commande de l'historique
  borné et une génération provider connue. Le backend renvoie l'écho de tout
  acquittement cible authentifié, y compris après rotation ou redémarrage, mais
  ne retire sa commande courante que si leurs identifiants correspondent. Dans
  une même réponse, cet écho reçu est prioritaire sur une expiration simultanée
  d'une autre commande ; l'expiration reste mémorisée pour le cycle suivant.
- **LAN** : HTTPS sur réseau privé, certificat épinglé, HMAC-SHA-256, anti-rejeu,
  séquence, horodatage, secrets protégés, aucun port entrant sur la cible.
  Toute identité de clé déclarée pour le plan de contrôle reste réservée à
  cette route même lorsque le plan est désactivé ; elle n'est jamais réinjectée
  dans les clés de télémétrie ou de capture.
- **Supervision provider** : un statut moteur sans champ `advertising` est une
  rupture de contrat, jamais assimilée à une simple attente d'abonné. La reprise
  reste bornée par le même délai monotone. Le coordinateur n'autorise aucune
  reprise cible si `advertising` ou l'état d'abonnement est absent, invalide, ou
  si le provider n'annonce plus. Une commande déjà en attente reste mémorisée
  mais n'est pas redélivrée avant le retour d'un statut sain. Chaque lecture de
  statut est liée à la génération provider observée avant cette lecture ; une
  rotation concurrente invalide le statut et ferme la réponse sans commande.

## Priorités et alternatives

P1 : HOGP natif entre les deux PC. Le récepteur Logitech Nano `046D:C534`, un
pont HID physique, un HID virtuel et `SendInput`/`SetCursorPos` sont hors
périmètre. Il n'existe aucun transport de repli : les limites de la pile
Bluetooth Windows doivent être observables et traitées dans cette architecture.

## État des preuves

Les audits de la PR #5 avaient démontré uniquement la création GATT non diffusée
et `GetCursorPos`; cette limite est conservée comme preuve historique. La PR #6
démontre désormais publicité, appairage `ConfirmOnly` chiffré persistant,
pilote/souris HID natifs, mouvements, clics, défilement, retour HTTPS/HMAC,
zones, trajectoires, séquences, reconnexion et tâches `AtLogOn` sur les deux
machines. La série stable de 100 mouvements atteint 100 % de réussite, une
médiane de 670,483 ms, un P95 de 983,052 ms et une erreur maximale de 2 px.
Ces preuves matérielles sont antérieures aux correctifs R1–R5 : elles ne valent
pas requalification matérielle de ces correctifs ni constat de la version
actuellement installée.

La mention historique « aucune fenêtre graphique requise » ne prouve pas un
pairage entrant sans consentement. La requalification du 28 novembre 2026 sur
`DESKTOP-NPIHO8K` a reproduit une notification backend, puis les événements
`BTHUSB 37` (authentification entrante rejetée) et `BTHUSB 29` (délai du
gestionnaire de sécurité) lorsque personne ne la validait. Sur Windows Desktop,
le consentement unique appartient donc au provisioning. Le fonctionnement
ensuite attendu est automatique et persistant ; toute demande de consentement
après redémarrage ou mise à jour invalide la qualification.

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

## Limite de solution retenue

Le périmètre impose les radios Windows existantes et Bluetooth HOGP. Aucun
matériel supplémentaire ni autre transport n'est un repli admissible. Une
limite de la pile Windows est donc rendue visible et traitée par stabilité du
provider, état fail-closed et plan de contrôle API ; elle n'est pas masquée par
un changement de technologie. SSH reste exclusivement un secours de maintenance.

## Réalisation MC-HID-EXEC-001 — 20 novembre 2026

La réalisation sépare quatre responsabilités :

- `HogpTransport` : processus PowerShell/WinRT sous identité MSIX, hébergé par le
  binaire Windows Microsoft-signé, services HID `0x1812` et Battery
  `0x180F`, rapports relatifs de six octets, chiffrement obligatoire et aucune
  émission sans l'unique abonnement actif dont l'identité hachée est autorisée ;
- `PositionController` : sérialisation des commandes, mesures fraîches de moins
  de 150 ms, correction adaptative tenant compte de l'accélération, plafonnée à
  48 puis mode fin plafonné à 8, changement de session/topologie fail-closed ;
- `TrajectoryEngine` : calcul pur de courbes quadratiques, profil progressif,
  variations de vitesse, micro-variations bornées uniquement en mouvement et
  plafond configurable de points (10 par défaut) ;
- `SequenceRunner` : zones rectangle/cercle/polygone, graine reproductible,
  modes automatique/commandé et états `IDLE` à `ERROR`.

L'agent .NET Framework 4.8 du PC cible s'exécute visiblement dans la
session console, lit position physique/DPI/topologie et ne possède aucune API
d'entrée. Il publie en sortie seulement vers HTTPS privé avec certificat
épinglé, HMAC-SHA-256, séquence et horodatage. L'API de commande reste sur
`127.0.0.1`, avec bearer DPAPI, TTL, idempotence et limite de débit.

`PositionAgent --config` publie exclusivement la télémétrie et les captures. Il
n'ouvre aucun service HOGP, ne crée aucune session GATT et ne surveille aucun
périphérique Bluetooth. Après l'enrôlement, le pilote HID natif Windows est
l'unique Report Host chargé de la connexion et de la reconnexion ; aucun client
GATT applicatif persistant ne lui fait concurrence. L'outil de pairage reste une
commande ponctuelle de provisioning et de diagnostic, jamais une tâche de fond.
L'identité AEP durable est produite uniquement après preuve du chiffrement ; elle
est distincte de l'empreinte de l'adresse radio, qui reste un diagnostic éphémère.
Une seule opération d'enrôlement observe exactement une annonce portant le nom
exact, le type `ConnectableUndirected` et le service HID `0x1812`, puis résout
immédiatement cette même adresse avec `FromBluetoothAddressAsync` avant le
`PairAsync(Encryption)` standard. L'adresse n'est jamais transmise à une seconde
commande ni utilisée comme identité persistante, car une adresse privée BLE peut
tourner entre deux énumérations. Le consentement Windows confirme l'enrôlement.
La commande ponctuelle `Connect` exige ensuite le nom exact, le hachage AEP
durable, `Pairing.IsPaired` et l'ouverture non cachée de l'unique service HID ;
`IsPresent` et `IsConnectable` restent diagnostiques. La commande libère toutes
ses références avant la qualification fonctionnelle afin de rendre la connexion
au pilote HID natif. Ni l'adresse ni l'identifiant AEP bruts ne sont journalisés.

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

## Extension J6 — MC-MOUSE-ACTIONS-001

`ActionExecutor` sérialise une file bornée de commandes et séquences. Chaque
action possède un UUID ou identifiant client, un parent éventuel, des
horodatages, une durée, un résultat et les états `ACCEPTED`, `RUNNING`,
`EXECUTED`, `CONFIRMED`, `FAILED`, `UNKNOWN`, `CANCELLED`. Un journal JSONL
local hors Git conserve les derniers états. Son registre compagnon `.ids`
réserve chaque identifiant avant l'acceptation, indépendamment de l'éviction et
de la compaction des états. La réservation vaut 30 jours par défaut et n'expire
que lorsque ce délai est écoulé **et** que l'action n'est plus dans le registre
courant. Après redémarrage, toute action inachevée devient `UNKNOWN` et ne peut
pas être resoumise. Les actions non-idempotentes à issue incertaine ne sont
jamais retentées.

Le moteur couvre clic simple/double/triple/multiple, cinq boutons et leurs
combinaisons, appui/relâchement, maintien, déplacement bouton maintenu,
glisser-déposer, roulette verticale bornée ou continue, mouvements relatifs et
arrivées absolues confirmées par position réelle. Le descripteur HOGP appairé
reste inchangé : cinq boutons, X/Y 16 bits et molette verticale 8 bits. Il ne
déclare pas `AC Pan`; la roulette horizontale est donc annoncée explicitement
indisponible plutôt que simulée.

Le WebSocket `ws://127.0.0.1:<event_port>/v1/events` utilise le même bearer DPAPI
que l'API locale, exige une négociation RFC 6455 authentifiée, limite connexions
et files, et pousse chaque transition avec `event_id`, `event_sequence` et
`action_id`. Il n'expose aucun port LAN. `EXECUTED` signifie que les rapports
HID de l'action ont été émis ; un clic reste `EXECUTED`. `CONFIRMED` est réservé
à une observation indépendante, actuellement l'arrivée du curseur mesurée.

`CaptureBroker` n'accepte aucune capture autonome. Une politique d'action ou de
séquence peut demander `before` et/ou `after`. La demande est remise à l'agent
dans la réponse HTTPS à son échantillon de position sortant : aucun port entrant
n'est ajouté sur le PC cible. L'agent visible relit alors le curseur, choisit
le rectangle écran qui le contient (coordonnées négatives incluses), affiche
l'indication `CAPTURE VISIBLE`, copie uniquement ce moniteur complet puis
téléverse un PNG HMAC sur `/v1/capture` avec corrélation et horodatage. Taille,
nombre, attente, stockage total et TTL sont bornés ; suppression explicite et
prune automatique sont disponibles. Un index atomique `.capture-index.json`
conserve le suivi après redémarrage. `DELETED` n'est affecté qu'après constat
d'absence du fichier ; `DELETE_FAILED` conserve chemin, taille et erreur, reste
compté dans le quota et peut être retenté. Les fichiers orphelins d'un arrêt
inopiné sont récupérés dans cet état. Les images et journaux restent hors Git et
ne sont jamais servis par HTTP. Le champ `analysis_ready` prépare une future
analyse locale sans moteur visuel dans ce mandat.

## Registre de contrats — MC-API-CATALOG-001

`api_catalog.py` est la source structurée des commandes, des types d'actions et
des événements WebSocket. Chaque commande associe son contrat public à un nom
de gestionnaire privé. `CommandGateway` résout ce contrat, valide les paramètres
statiques puis appelle le gestionnaire déclaré : il n'existe donc plus de liste
de routage indépendante susceptible de diverger du catalogue.

Les contraintes de type, présence, valeurs autorisées, bornes et valeurs par
défaut sont déclarées comme contraintes statiques. Les préconditions liées à
l'état — fraîcheur de position, moteur optionnel, action ou séquence active,
topologie physique, abonnement HID — sont publiées séparément comme contraintes
dynamiques et restent vérifiées par les composants métier existants. Le moteur
d'actions utilise le même registre pour reconnaître ses 13 discriminants ; les
contrôles conditionnels de sûreté restent dans `ActionExecutor`.

La découverte emprunte exclusivement `POST /v1/command` sur `127.0.0.1` et
conserve bearer, enveloppe, TTL, idempotence, débit et taille maximale. Elle ne
crée ni port ni effet matériel. La disponibilité runtime indique explicitement
si les sous-systèmes actions ou captures ont été injectés. La référence
`docs/API-REFERENCE.md` est rendue de façon déterministe à partir du registre.

## Durcissement R1 — sûreté fonctionnelle des actions

Une erreur de livraison susceptible de laisser un bouton dans un état inconnu
porte désormais une information de sûreté distincte de la politique métier.
`press`, `release`, `hold`, `drag`, `move_with_buttons` et `click` convergent
alors vers `UNKNOWN`, publient une intention d'arrêt à toutes les actions,
tentent le relâchement via l'arrêt contrôleur et placent l'exécuteur en
quarantaine. `continue` et `retry` ne peuvent pas contourner cette règle. La
tentative de relâchement n'est jamais présentée comme une confirmation physique.

La commande globale `stop` sépare publication et exécution : elle réveille
d'abord l'exécuteur moderne et le `SequenceRunner` historique, puis effectue un
unique arrêt contrôleur. Une erreur d'un composant n'empêche pas la notification
des suivants. `SequenceRunner` protège son état `STOPPED` contre une transition
tardive de son thread.

`ActionExecutor.close()` ferme atomiquement l'admission, réveille l'action
active, transforme chaque action encore en file en `CANCELLED`, puis termine le
worker dans une borne. Une action bouton déjà émise et dont le relâchement n'est
pas physiquement confirmé reste `UNKNOWN`. Ces transitions utilisent le journal
et le registre `.ids` existants ; le contrat anti-rejeu est inchangé.

## Durcissement R2 — transport HOGP et récepteur LAN

`NativeHogpTransport` supervise chaque processus actif avec trois workers
bornés : lecture `stdout`, drainage `stderr` et écriture `stdin`. Le thread
appelant n'effectue plus d'accès bloquant direct aux pipes. Une deadline unique
couvre l'acquisition du verrou, l'écriture et la réponse d'une commande. Un
timeout, une réponse partielle/invalide, un pipe rompu ou une mort du moteur
invalide le canal et lance une terminaison hors protocole par le handle du
processus. Aucune commande HID n'est rejouée.

Les valeurs par défaut sont : démarrage 15 s, commande 3 s, arrêt protocolaire
3 s et terminaison processus 2 s. Les opérations WinRT du moteur PowerShell ont
une limite propre de 5 s avec annulation best-effort. Si `terminate` puis `kill`
échouent, le handle est conservé, `recovery_required` devient vrai et aucun
nouveau moteur ne peut être lancé. La fin du processus ou une tentative de
relâchement ne confirme jamais l'état physique des boutons.

Le récepteur HTTPS utilise `BoundedThreadingHTTPServer`. L'admission précède
la création du thread et borne à 8 les connexions actives ainsi que le backlog.
Le thread d'acceptation ne réalise aucun handshake : chaque handshake TLS est
effectué dans le worker déjà admis, avec une borne de 3 s. Un client TLS muet
ne retarde donc pas l'acceptation d'un autre client tant qu'un slot reste libre,
et aucun thread n'est créé pour une connexion excédentaire.

Les lectures HTTP combinent une limite d'inactivité et une deadline absolue,
recalculée avant chaque `recv` : 2 s/5 s pour les en-têtes, 5 s/10 s pour un
corps de position et 5 s/120 s pour une capture. La progression partielle ne
renouvelle jamais le budget total. Les 120 s autorisent le maximum de 24 Mio à
environ 205 Kio/s, tout en restant finis. Le corps doit correspondre exactement
à `Content-Length` avant HMAC. Les slots sont libérés en `finally`, y compris
sur timeout ou déconnexion. TLS 1.2 minimum, HMAC, anti-rejeu, tailles maximales,
interfaces d'écoute et protocoles publics restent inchangés.

## Durcissement R3 — stockage, cycle de vie et mise à jour cible

Le quota de `CaptureBroker` est un plafond dur vérifié avant chaque écriture.
L'admission compte tous les fichiers du répertoire privé, y compris index
courant, index temporaire atomique, PNG, fichiers temporaires, index invalides
préservés et orphelins. Elle contrôle aussi l'espace disque libre. Les
téléversements concurrents sont sérialisés pendant admission et commit. Chaque
index atomique emploie un temporaire unique : l'ancien index, le PNG final et le
nouvel index temporaire sont comptés simultanément, sans soustraire un fichier
avant sa disparition physique. Un observateur optionnel mesure chaque étape et
vérifie `used_bytes <= capture_total_bytes`. Un refus passe la
demande à `FAILED` sans créer de PNG. Au démarrage, un index absent ou invalide
ne provoque aucune suppression : l'index invalide est conservé sous un nom
distinct et les fichiers non indexés deviennent `DELETE_FAILED`, donc visibles,
comptés et supprimables par une nouvelle tentative contrôlée.

Le runtime principal utilise une pile de ressources idempotente. Chaque serveur
est enregistré immédiatement après sa création et fermé en ordre inverse. Seuls
les serveurs dont le thread a démarré reçoivent `shutdown()` ; tous reçoivent
`server_close()`. L'arrêt continue malgré les erreurs de fermeture, ferme aussi
le moteur d'actions et le contrôleur, puis expose l'ensemble des erreurs dans
`RuntimeCleanupError`, sans masquer l'erreur initiale.

La mise à jour de `PositionAgent.exe` est une transaction observable. Le script
vérifie les empreintes de l'agent installé, de l'artefact, du staging et de la
sauvegarde ; il persiste les phases dans un marqueur atomique voisin du binaire.
Le nouveau binaire n'est confirmé qu'après démarrage de la tâche et observation
conjointe de son état `Running` et du processus attendu. Tout échec après
remplacement tente au plus deux restaurations de la sauvegarde, avec vérification
d'empreinte et redémarrage. Un échec de restauration conserve
`RECOVERY_REQUIRED` et bloque une nouvelle installation ambiguë jusqu'à une
récupération explicite. Une panne avant remplacement restaure aussi l'état
initial de la tâche : un agent auparavant actif est redémarré et contrôlé avant
suppression du marqueur. Le rollback explicite prépare la sauvegarde et une
copie vérifiée de la version courante hors du chemin actif, puis effectue un
remplacement atomique. Si la version restaurée ne peut pas être validée, la
copie préservée est compensée en deux essais maximum ; sinon les éléments de
récupération restent accompagnés de `RECOVERY_REQUIRED`. Le mode d'injection de panne est réservé au harness
isolé par une variable d'environnement ; il ne touche aucune tâche réelle.

## Qualification locale R4

`scripts/qualification/qualify.py` est l'unique point d'entrée des profils
locaux. Il orchestre une liste fermée de phases et écrit pour chacune un log,
une durée et un statut, puis un `summary.json` contenant SHA Git, versions,
exclusions et artefacts. Un résultat logiciel non favorable reste une preuve
comptable : ses compteurs sont validés et agrégés avant l'arrêt fail-closed de
la qualification. `full-local` enchaîne strictement `software` puis
`build`; il n'existe aucune transition vers un diagnostic matériel.

La chaîne build Windows découvre Roslyn avec `vswhere`, le SDK avec
`KitsRoot10`, puis valide les métadonnées et contrats WinRT avant compilation.
L'analyse PowerShell appelle uniquement l'analyseur syntaxique 5.1 sur les
fichiers ; elle ne les exécute pas. Les fichiers temporaires et caches Python
sont isolés puis supprimés. Les logs et artefacts restent sous `out/`, sans
installation ni activation.

## Rationalisation R5

Le moteur HOGP actif est `src/hogp-powershell/hogp.ps1`, copié dans le MSIX par
`Build-HogpPackage.ps1` et lancé par l'alias
`mousse-hogp-packaged.exe`. Les projets `src/hogp` et `src/hogp-launcher` sont
des implémentations C++ historiques non référencées par le build, le packaging
ou les tests actifs. Ils restent conservés car un usage manuel ou diagnostic
n'a pas été exclu. Le descripteur HID et le chemin HOGP actif sont inchangés.

`SequenceRunner` conserve l'orchestration historique par zones et
`ActionExecutor` l'orchestration moderne persistée. Leurs mécanismes de
pause/reprise/arrêt se ressemblent, mais leurs états publics, unités de travail
et garanties d'échec diffèrent ; aucune fusion ni troisième ordonnanceur n'est
introduit. Le catalogue refuse désormais un identifiant dupliqué avant
insertion pour ses trois familles de ressources.

## Convergence architecturale — MC-ARCHITECTURE-CONVERGENCE-001

Les deux modèles de séquence sont conservés pour compatibilité fonctionnelle,
mais ne constituent plus deux voies concurrentes vers le HID. Une séquence
historique réserve le coordinateur avant de démarrer ; une action moderne
attend ce même coordinateur dans sa file ; une commande historique synchrone
est refusée explicitement si une autre opération possède déjà le périphérique.
Ainsi, un déplacement ne peut plus s'insérer pendant un maintien de bouton.

`CommandGateway` est ramené à son rôle d'adaptateur : authentification,
idempotence, validation du contrat et traduction de réponse. La composition des
cas d'usage, des requêtes et du cycle de séquence appartient à
`MouseApplicationService`. Le stockage de feedback est extrait du contrôleur et
publie position et topologie dans une transaction mémoire unique.

Le runtime planifié doit provenir d'une release contrôleur préparée par
`scripts/runtime/controller_release.py` depuis les blobs d'un commit exact et
un dépôt propre. La release contient un manifeste et les empreintes de chaque
fichier ; le gestionnaire de tâche et le lanceur vérifient son intégrité. Le
mode source mutable n'est disponible que manuellement avec
`-AllowMutableSource` et ne doit jamais servir à une tâche de production.

## Précision HID et boucle fermée — MC-HID-PRECISION-001

Un rapport relatif HOGP transporte des **unités HID**, pas des pixels écran.
Windows applique ensuite sa chaîne de pointeur ; la vitesse, l'accélération et
les arrondis peuvent donc produire une amplitude écran différente. L'action
historique `move_relative` conserve volontairement cette sémantique brute.

L'action `move_relative_confirmed` exprime au contraire `dx` et `dy` en pixels
écran. Elle relève d'abord une mesure PositionAgent fraîche, en déduit une cible
absolue sur la même topologie, puis réutilise la boucle fermée `move_to`. Chaque
correction est bornée en amplitude, durée, nombre d'itérations et mouvement HID
cumulé. La boucle s'arrête aussi sur stagnation, oscillation, absence de progrès,
changement de session/topologie ou arrêt d'urgence. `CONFIRMED` n'est publié
qu'après une nouvelle observation indépendante dans la tolérance demandée.

Une mesure initiale absente ou périmée ne produit aucun rapport. Après une
émission, toute perte de retour ou erreur de transport est classée comme issue
incertaine et interdit le rejeu automatique. Les métriques exposent la cible,
l'erreur finale, les corrections et le mouvement commandé, sans transformer une
tentative de compensation en preuve matérielle.

## Validation matérielle finale

`MC-FINAL-VALIDATION-001` confirme sur la chaîne réelle la séparation des deux
contrats : un rapport brut de valeur 10 a produit 7 pixels après stabilisation,
alors que les déplacements confirmés ont atteint exactement les cibles X/Y,
absolues et relatives, puis la position initiale. Une mesure PositionAgent
fraîche et stabilisée clôt chaque action confirmée.

L'arrêt global annule d'abord l'ordonnanceur et tente ensuite la libération et
l'arrêt HOGP avec des délais bornés. Si l'arrêt protocolaire HOGP expire, la
séquence reste `CANCELLED`, mais le runtime est considéré non réutilisable et la
procédure qualifiée redémarre la tâche. Le registre anti-rejeu persiste ce
redémarrage et refuse l'ancien identifiant.
