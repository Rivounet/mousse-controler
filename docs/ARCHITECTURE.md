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

Codex travaille **directement sur mini-pc-backend**. L'accès OpenSSH à clé et
host key stricte vers MonOrdinateur est qualifié pour la maintenance ; l'agent
de position s'exécute séparément dans la session interactive.

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

Les audits de la PR #5 avaient démontré uniquement la création GATT non diffusée
et `GetCursorPos`; cette limite est conservée comme preuve historique. La PR #6
démontre désormais publicité, appairage `ConfirmOnly` chiffré persistant,
pilote/souris HID natifs, mouvements, clics, défilement, retour HTTPS/HMAC,
zones, trajectoires, séquences, reconnexion et tâches `AtLogOn` sur les deux
machines. La série stable de 100 mouvements atteint 100 % de réussite, une
médiane de 670,483 ms, un P95 de 983,052 ms et une erreur maximale de 2 px.

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
n'est ajouté sur MonOrdinateur. L'agent visible relit alors le curseur, choisit
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
d'actions utilise le même registre pour reconnaître ses 12 discriminants ; les
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
le handler métier et borne à 8 les connexions actives ainsi que le backlog. Les
deadlines par phase sont : handshake TLS 3 s, en-têtes 2 s, inactivité de
lecture du corps 5 s et écriture 2 s. Le corps doit correspondre exactement à
`Content-Length` avant HMAC. Les slots sont libérés en `finally`, y compris sur
timeout ou déconnexion. TLS 1.2 minimum, HMAC, anti-rejeu, tailles maximales,
interfaces d'écoute et protocoles publics restent inchangés.
