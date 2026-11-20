# MC-INDEPENDENT-AUDIT-001 — Audit architectural et qualité du code

**Dépôt :** `Rivounet/mousse-controler`

**Commit examiné :** `d19db664bc1e7d83ab1d289f89373f9e327a482b`

**Branche de publication :** `audit/mc-independent-audit-001`

**Date :** 20 novembre 2026

**Nature :** contre-expertise indépendante, produit examiné en lecture seule

## 1. Résumé exécutif

Le projet repose sur une architecture globalement saine : la commande souris
reste sur le mini-PC, le retour de position est un canal sortant distinct, le
transport HID est derrière une interface simulable, et les états non
idempotents sont traités avec une prudence inhabituelle et utile (`EXECUTED`,
`CONFIRMED`, `UNKNOWN`, journal et registre anti-rejeu). Les modules de
géométrie et de trajectoire sont purs, les secrets sont protégés par DPAPI,
les échantillons LAN sont signés avec horodatage et séquence, et les tests
Python couvrent bien la concurrence du contrôleur et la persistance.

Cette base n'est toutefois pas encore suffisamment robuste pour considérer
l'arrêt d'urgence et l'exploitation non supervisée comme entièrement fiables.
Trois défauts avérés sont prioritaires :

1. le transport HOGP peut attendre indéfiniment une ligne du sous-processus ou
   une opération WinRT; le paramètre `startup_timeout` n'est jamais appliqué;
2. une erreur ambiguë sur un bouton avec politique `continue` peut laisser le
   bouton logiquement et physiquement enfoncé tout en conservant le contrôleur
   actif;
3. le quota total de captures n'est pas une limite dure lorsque la suppression
   des anciens fichiers échoue.

Deux risques complémentaires affectent la disponibilité : le serveur HTTPS LAN
crée des threads sans plafond et lit les corps sans timeout de connexion, et
la fermeture de l'exécuteur laisse les actions encore en file au statut
`ACCEPTED`.

**Verdict : `MAINTENABLE_WITH_MAJOR_RESERVATIONS`.** La séparation des
responsabilités et les doubles de test donnent une bonne capacité d'évolution,
mais les constats P1 doivent être corrigés avant d'élargir les fonctions souris
ou de revendiquer un arrêt borné en toutes circonstances. Une refonte globale
n'est pas justifiée.

## 2. Périmètre et méthode

### Périmètre réel

L'inventaire a couvert tous les fichiers du commit, puis la revue approfondie a
porté sur :

- les 15 modules Python de `src/mousse_controler/`;
- le moteur HOGP actif `src/hogp-powershell/hogp.ps1` et son packaging MSIX;
- l'agent cible `src/position-agent/PositionAgent.cs`;
- les scripts de build, démarrage, mise à jour, diagnostic et qualification;
- l'outillage historique/auxiliaire de `scripts/remote/`;
- les 195 tests définis et la documentation technique du commit.

Les répertoires `qualification/` préexistants et `docs/REVUES/` n'ont pas été
consultés comme sources d'analyse. Les documents techniques imposés par
`AGENTS.md` ont servi uniquement à identifier le fonctionnement revendiqué;
leurs verdicts historiques n'ont pas été repris comme preuves.

### Méthode

1. création d'un worktree et d'une branche exactement au SHA demandé;
2. inventaire des fichiers, points d'entrée, imports, builds et relations;
3. lecture ligne à ligne des chemins actifs et inspection ciblée des chemins
   auxiliaires/historiques;
4. recherche de blocages, erreurs, états persistants, limites de ressources,
   duplication et divergences code/documentation;
5. exécution de tests logiciels uniquement, compilation C# temporaire et
   reproductions en mémoire;
6. classement de chaque constat selon preuve, conséquence, priorité, effort et
   risque de régression.

Aucune branche GitHub autre que le SHA fourni n'a été examinée. Aucun fichier
applicatif n'a été modifié.

## 3. Cartographie architecturale

```text
Client local
  └─ POST loopback + bearer + TTL/idempotence
       CommandGateway
       ├─ ActionExecutor / ActionRegistry ── journal JSONL + registre .ids
       ├─ SequenceRunner ── TrajectoryEngine ── Geometry
       └─ MouseController ── NativeHogpTransport
                              └─ processus MSIX PowerShell/WinRT
                                   └─ BLE HOGP → pile HID native cible

Agent cible C# visible
  ├─ GetPhysicalCursorPos / topologie / session
  ├─ capture ponctuelle du moniteur demandé
  └─ HTTPS sortant + pin certificat + HMAC/séquence
       └─ PositionReceiver ── PositionStore ── boucle de correction
       └─ CaptureBroker ── index JSON + PNG privés

ActionRegistry ──→ WebSocket loopback authentifié
```

### Inventaire et statut

| Ensemble | Responsabilité | Statut observé |
|---|---|---|
| `src/mousse_controler/app.py` | composition du runtime et cycle de vie des serveurs | Actif |
| `command_server.py`, `command_client.py`, `api_catalog.py` | API locale, catalogue, validation et client | Actif |
| `actions.py`, `sequence.py` | exécution sérialisée, composition, pause/annulation, états | Actif |
| `controller.py`, `geometry.py`, `trajectory.py` | boucle de position, zones et trajectoires | Actif |
| `transport.py`, `src/hogp-powershell/hogp.ps1` | protocole stdio et serveur GATT/HOGP | Actif |
| `position_server.py`, `security.py`, `dpapi.py` | retour LAN, HMAC/anti-rejeu et secrets locaux | Actif |
| `capture.py`, `event_server.py` | captures ponctuelles et événements WebSocket | Actif |
| `src/position-agent/` | mesures, reconnexion GATT et capture sur la cible | Actif |
| `packaging/hogp/`, `scripts/build/`, `scripts/runtime/`, `scripts/target/` | packaging, compilation, tâches et mise à jour | Actif/opérationnel |
| `scripts/qualification/` | témoins et campagnes manuelles | Auxiliaire, non runtime |
| `scripts/bluetooth/`, `scripts/diagnostics/` | diagnostics et pairabilité bornée | Auxiliaire/opérationnel |
| `scripts/remote/` | artefacts, modèle local de releases et ancien canal distant | Auxiliaire/historique; non dépendance du runtime |
| `src/pairing-tool/` | appairage/inspection interactive | Auxiliaire de mise en service |
| `src/hogp/` | autre moteur HOGP C++/WinRT | Historique/non relié au build actif |
| `src/hogp-launcher/` | lanceur vers l'alias packagé | Non relié au démarrage ou packaging actif |

Le runtime Python n'a pas de dépendance Python tierce. Les dépendances
externes sont principalement les API Windows, .NET Framework 4.8, Windows SDK,
Build Tools/Roslyn et PowerShell 5.1.

## 4. Évaluation de la qualité du code

### Points solides

- Les frontières `HidTransport`, `PositionStore` et les moteurs purs rendent la
  logique métier testable sans matériel.
- `MouseController` publie l'intention d'arrêt avant d'attendre son verrou. Les
  tests de concurrence couvrent les commandes déjà engagées et celles en
  attente.
- Les dataclasses et enums rendent les états explicites; les copies profondes
  des résultats évitent plusieurs fuites de mutabilité.
- Les écritures critiques du journal, du registre d'identifiants et de l'index
  de captures sont vidées (`fsync`) et les compactages utilisent un remplacement
  atomique.
- La distinction entre effet émis et effet observé est techniquement juste et
  doit être conservée.
- Le catalogue API sert à la fois au routage, à une partie de la validation et
  à la documentation générée, ce qui réduit une source classique de dérive.

### Lisibilité et complexité

La complexité est concentrée dans `actions.py`, `api_catalog.py`,
`PositionAgent.cs` et le script HOGP. Leur taille seule n'est pas un défaut.
En revanche :

- `ActionRegistry` cumule registre mémoire, diffusion, journal, migration,
  registre anti-rejeu et compactage;
- `ActionExecutor._perform()` porte toutes les variantes d'action et une partie
  importante de leurs politiques d'erreur;
- les contraintes statiques du catalogue sont partiellement répétées dans
  `_validate_spec()`;
- les protocoles interlangages sont des chaînes JSON/texte sans schéma versionné
  testé de bout en bout.

Une extraction ciblée de la persistance du registre et de la politique de
sûreté des actions serait justifiée. Une multiplication générale de classes ou
un framework web ne le serait pas.

### Gestion des erreurs

Le code échoue souvent fermé sur les données persistantes invalides, les
replays, les données trop anciennes et les changements de session/topologie.
Les faiblesses principales sont les attentes non bornées du transport, la
politique `continue` appliquée à des transitions de bouton ambiguës et quelques
`except Exception` qui transforment un défaut d'infrastructure en état métier
sans mettre le sous-système en quarantaine.

## 5. Duplications et dette technique

### Duplication avérée

1. Deux implémentations HOGP coexistent. Le packaging actif copie uniquement
   `src/hogp-powershell/hogp.ps1`, tandis que `src/hogp/main.cpp` et son projet
   ne sont référencés par aucun chemin de build ou runtime actif.
2. Les scripts de build C# répètent les mêmes chemins absolus vers Roslyn,
   Windows SDK et les contrats WinRT.
3. Les bornes d'actions sont déclarées dans `api_catalog.py`, puis plusieurs
   sont revérifiées manuellement dans `ActionExecutor._validate_spec()`.
4. Plusieurs tests de contrats recherchent des sous-chaînes dans le source au
   lieu d'exécuter le comportement correspondant.

### Dette documentaire

Le `README.md` présente encore le moteur actif comme « C++/WinRT » alors que le
build courant package PowerShell/WinRT. Cette divergence augmente le risque de
corriger ou qualifier le mauvais composant. La documentation d'architecture
contient aussi des couches historiques et courantes dans un même document;
elles sont traçables mais coûteuses à interpréter.

## 6. Robustesse, sécurité et risques

### Protections à conserver

- API de commande et WebSocket liés à loopback;
- canal cible uniquement sortant, TLS avec certificat épinglé;
- HMAC sur méthode, chemin, horodatage, séquence et hash du corps;
- DPAPI par utilisateur pour les secrets de configuration;
- bornes explicites sur les corps, files, enregistrements et images;
- absence d'API d'injection de souris dans l'agent cible;
- non-rejeu durable des identifiants d'action et états `UNKNOWN` prudents.

### Surface de risque

L'authentification applicative ne protège pas le serveur HTTPS contre une
connexion qui ne termine jamais son corps : la signature n'est vérifiée
qu'après `rfile.read(length)`. Le backlog à 4 ne borne pas les threads actifs de
`ThreadingHTTPServer`. Sur un LAN privé, ce risque est moindre que sur Internet,
mais une machine locale compromise ou un client défaillant peut épuiser les
threads et priver la boucle de retour de position.

Le récepteur accepte par ailleurs une position qui n'est pas explicitement
vérifiée comme appartenant à l'un des écrans annoncés. L'agent actuel effectue
ce contrôle implicitement par l'API Windows, mais le récepteur devrait faire
respecter lui-même cet invariant de sûreté.

## 7. Évaluation des tests

Le commit définit **195 tests** : 114 dans `tests/`, 69 pour l'outillage
remote/releases, 5 Bluetooth/pairabilité et 7 diagnostics. L'audit a exécuté
**188 tests logiciels, tous PASS**, plus la génération documentaire, la
compilation C# avec warnings traités en erreurs et l'analyse syntaxique
PowerShell. Les détails sont dans
[`evidence/EXECUTIONS.md`](evidence/EXECUTIONS.md).

### Forces

- concurrence et arrêt du contrôleur testés de manière déterministe;
- journal, anti-rejeu, compaction et redémarrage bien couverts;
- nombreuses limites et erreurs de l'API et des captures couvertes;
- trajectoires et séquences reproductibles par graines;
- outillage d'artefacts/releases fortement testé en simulation.

### Faiblesses

- sept tests de la suite par défaut lancent de vrais diagnostics d'environnement
  dès que l'OS est Windows; ils ne sont pas soumis à un opt-in matériel;
- 21 tests reposent sur `read_text()` et des assertions de sous-chaînes;
- les six tests de l'agent C# sont tous textuels; la compilation réelle n'est
  pas intégrée au harnais Python;
- les tests du transport natif n'exercent ni timeout, ni crash, ni stdout
  partiel, ni saturation de stderr;
- aucune configuration CI n'est présente;
- aucune mesure de couverture n'a pu être produite avec l'environnement fourni.

La suite est riche mais son total ne doit donc pas être interprété comme une
couverture homogène des frontières C#/PowerShell/WinRT.

## 8. Inventaire des constats avec preuves

### F-01 — Attentes HOGP non bornées

- **Nature :** défaut avéré; conséquence de blocage reproduite avec un double.
- **Gravité / priorité :** majeure / P1.
- **Preuves :** `transport.py:94-96` stocke `startup_timeout`, sans autre lecture;
  `transport.py:121` utilise `stdout.readline()` bloquant;
  `transport.py:133-143` attend chaque réponse sans deadline;
  `transport.py:152` ouvre un pipe stderr jamais drainé;
  `hogp.ps1:11-26` appelle `GetAwaiter().GetResult()` sans timeout.
- **Conséquence :** un moteur WinRT ou sous-processus bloqué peut immobiliser
  une commande, le verrou du contrôleur, la maintenance et l'arrêt d'urgence.
  Le verrou global de `CommandGateway.execute()` propage alors le blocage aux
  autres commandes API.
- **Recommandation :** protocole borné par commande avec lecteur dédié, deadline,
  terminaison du processus en dépassement et drainage de stderr; annulation ou
  timeout explicite des opérations WinRT; test de moteur muet/partiel.
- **Bénéfice / effort / régression :** très élevé / moyen-élevé / moyen.

### F-02 — Poursuite possible avec bouton incertain maintenu

- **Nature :** défaut avéré par reproduction en mémoire.
- **Gravité / priorité :** majeure / P1.
- **Preuves :** `controller.py:156-173` modifie `_buttons` autour de l'appel
  transport; `actions.py:647-654` classe l'erreur comme émission incertaine;
  `actions.py:827-832` n'arrête le contrôleur que pour la politique `stop`;
  `actions.py:775-776` poursuit même une séquence. La reproduction obtient
  `UNKNOWN`, contrôleur actif et masques bouton à 1.
- **Conséquence :** un bouton peut rester enfoncé pendant que les actions
  suivantes s'exécutent.
- **Recommandation :** toute transition de bouton ambiguë doit forcer une
  libération/arrêt ou placer le contrôleur en quarantaine, indépendamment de la
  politique métier `continue`; distinguer erreurs pré-émission et post-émission.
- **Bénéfice / effort / régression :** très élevé / moyen / moyen.

### F-03 — Quota total de captures non strict

- **Nature :** défaut avéré dans le code et par le test existant.
- **Gravité / priorité :** majeure / P1.
- **Preuves :** `capture.py:196` écrit avant de réserver le quota;
  `capture.py:266-294` tente de supprimer quand le total dépasse la limite mais
  ne refuse pas l'upload si le total reste supérieur;
  `tests/test_capture.py:127-137` configure une limite inférieure à une image et
  valide que le fichier subsiste en `DELETE_FAILED`.
- **Conséquence :** si les suppressions sont durablement refusées, de nouvelles
  captures peuvent continuer à augmenter l'usage disque; la borne réelle devient
  indirectement `max_records * max_bytes`.
- **Recommandation :** réserver la capacité avant écriture, retenter le prune,
  puis refuser ou désactiver les captures tant que le quota dur ne peut pas être
  respecté; compter temporaires et index.
- **Bénéfice / effort / régression :** élevé / moyen / faible-moyen.

### F-04 — Récepteur LAN vulnérable à l'épuisement de ressources

- **Nature :** absence de borne avérée; exploitation hypothétique.
- **Gravité / priorité :** modérée / P1.
- **Preuves :** `position_server.py:149` lit le corps sans timeout;
  `position_server.py:186-192` utilise `ThreadingHTTPServer`, un backlog de 4
  et TLS, mais aucun plafond de threads/connexions ni timeout par socket.
- **Conséquence :** des connexions lentes peuvent monopoliser des threads avant
  authentification et interrompre le feedback nécessaire au positionnement.
- **Recommandation :** timeout de handshake/lecture/écriture, plafond de
  connexions actives et rejet précoce; conserver la liaison LAN privée et HMAC.
- **Bénéfice / effort / régression :** élevé / moyen / faible-moyen.

### F-05 — Fermeture incomplète de la file d'actions

- **Nature :** défaut avéré par reproduction.
- **Gravité / priorité :** modérée / P2.
- **Preuves :** `actions.py:513-522` positionne `_closed` avant le sentinel;
  `actions.py:524-535` quitte la boucle dès que `_closed` est vrai, sans drainer
  la file. La reproduction donne une action active `CANCELLED` et l'action en
  file encore `ACCEPTED`.
- **Conséquence :** au redémarrage, ces actions deviennent `UNKNOWN` alors
  qu'elles n'ont jamais commencé; les contrôles restent en mémoire jusqu'à la
  fin du processus.
- **Recommandation :** transition atomique de toutes les actions en file vers
  `CANCELLED`, drainage explicite et test de fermeture avec file pleine.
- **Bénéfice / effort / régression :** moyen / faible-moyen / faible.

### F-06 — Harnais de tests partiellement environnemental et textuel

- **Nature :** dette avérée.
- **Gravité / priorité :** modérée / P2.
- **Preuves :** `test_all.py:20-33` agrège diagnostics et tests;
  `scripts/bluetooth/test_diagnostics.py:11-25` et
  `scripts/diagnostics/test_inspect_monordinateur.py:11-27` exécutent des
  diagnostics réels sur tout Windows; 21 tests lisent le texte source; aucune
  CI n'est présente.
- **Conséquence :** le résultat de la commande par défaut dépend du matériel;
  une modification sémantiquement incorrecte peut conserver les sous-chaînes
  attendues et passer les tests de contrat.
- **Recommandation :** suites `unit`, `integration`, `hardware` distinctes;
  opt-in explicite pour le matériel; compilation C# et tests comportementaux des
  protocoles dans CI; conserver les tests textuels seulement comme gardes
  secondaires.
- **Bénéfice / effort / régression :** élevé / moyen-élevé / faible.

### F-07 — Implémentations HOGP historiques et documentation ambiguë

- **Nature :** dette avérée.
- **Gravité / priorité :** modérée / P2.
- **Preuves :** `Build-HogpPackage.ps1:26` ne copie que le script PowerShell;
  aucun chemin actif ne référence `src/hogp/MousseHogp.vcxproj` ni
  `src/hogp-launcher/MousseHogpLauncher.vcxproj`; `README.md:9` annonce encore
  un moteur C++/WinRT.
- **Conséquence :** ambiguïté sur la source de vérité, duplication du
  descripteur/protocole et risque d'appliquer un correctif au composant inactif.
- **Recommandation :** confirmer formellement leur statut, puis supprimer ou
  déplacer les implémentations historiques hors du chemin produit; corriger la
  cartographie active.
- **Bénéfice / effort / régression :** moyen-élevé / faible-moyen / faible si
  l'absence d'usage est d'abord validée.

### F-08 — Échantillonnage aléatoire fragile des polygones fins

- **Nature :** défaut avéré sur une géométrie valide extrême.
- **Gravité / priorité :** faible à modérée / P3.
- **Preuves :** `geometry.py:218-222` abandonne après 10 000 rejets. Pour le
  polygone valide `[(0,0),(16383,1),(16382,1)]`, 7 graines sur 20 ont levé
  `RuntimeError` dans la reproduction.
- **Conséquence :** une zone très fine peut échouer de manière dépendante de la
  graine, sans être invalide.
- **Recommandation :** échantillonnage par triangulation pondérée ou algorithme
  scan-line sur coordonnées entières, avec tests de polygones concaves et fins.
- **Bénéfice / effort / régression :** moyen / moyen / moyen.

### F-09 — Garde de registre API incomplète

- **Nature :** risque de maintenance avéré dans l'implémentation.
- **Gravité / priorité :** faible / P3.
- **Preuves :** `_add()` écrase silencieusement une clé existante
  (`api_catalog.py:103-104`), puis le contrôle de doublons sur le dictionnaire
  (`api_catalog.py:735-736`) ne peut plus détecter cet écrasement. Les paramètres
  inconnus sont globalement autorisés (`api_catalog.py:69`, `:377`) et
  `validate_parameters()` ne les inspecte pas.
- **Conséquence :** une future commande dupliquée peut remplacer la première;
  une faute de frappe de client peut être ignorée et produire une valeur par
  défaut inattendue.
- **Recommandation :** refuser le doublon dans `_add`, autoriser les paramètres
  supplémentaires au cas par cas pour compatibilité, et tester les fautes de
  frappe.
- **Bénéfice / effort / régression :** moyen / faible / moyen pour les anciens
  clients, d'où un déploiement versionné.

### F-10 — Build reproductible seulement sur une image machine précise

- **Nature :** dette avérée.
- **Gravité / priorité :** modérée / P2.
- **Preuves :** les scripts `Build-PositionAgent.ps1`,
  `Build-PairingTool.ps1` et `Build-HogpPackage.ps1` codent en dur Visual Studio
  2022 et Windows SDK `10.0.26100.0` sous des chemins absolus.
- **Conséquence :** un poste avec un SDK plus récent seulement ou une autre
  édition de Build Tools ne peut pas construire sans modifier les scripts;
  l'environnement n'est pas validé automatiquement.
- **Recommandation :** résoudre les outils via `vswhere` et l'inventaire SDK,
  accepter des paramètres explicites, afficher les versions retenues et tester
  une matrice minimale supportée.
- **Bénéfice / effort / régression :** moyen-élevé / moyen / faible.

## 9. Recommandations priorisées

| Priorité | Action | Valeur attendue |
|---|---|---|
| P1 | Borner toutes les commandes HOGP/WinRT et garantir un chemin d'arrêt hors du canal bloqué | Restaure la propriété d'arrêt borné |
| P1 | Rendre toute erreur ambiguë de bouton fail-safe, même sous `continue` | Évite un bouton maintenu pendant les actions suivantes |
| P1 | Faire du quota de captures une admission stricte | Prévient l'épuisement disque |
| P1 | Borner connexions et temps de lecture du récepteur LAN | Protège la disponibilité du feedback |
| P2 | Drainer/annuler proprement la file à la fermeture | Rend les états persistés exacts |
| P2 | Séparer tests unitaires, intégration et matériel; ajouter CI/build C# | Rend la non-régression reproductible |
| P2 | Clarifier l'implémentation HOGP active et rationaliser les sources historiques | Réduit la dette et les erreurs de maintenance |
| P2 | Rendre les builds découvrables et versionnés | Améliore la portabilité du build |
| P3 | Remplacer le rejet aléatoire des polygones fins | Supprime un échec rare mais réel |
| P3 | Durcir le registre API contre doublons et paramètres inconnus | Prévient les dérives futures |

## 10. Plan de refactoring proposé

Le plan reste incrémental; aucune réécriture n'est nécessaire.

### Étape 1 — Sûreté et bornes

- introduire des deadlines testables dans le transport;
- traiter les états bouton ambigus et la fermeture de file;
- ajouter l'admission stricte des captures et les timeouts serveur;
- ajouter les tests de régression correspondants avec doubles bloqués.

### Étape 2 — Tests et protocoles

- rendre le matériel explicitement opt-in;
- tester le protocole JSON-lines avec un faux sous-processus complet;
- compiler et tester l'agent C# dans le pipeline;
- versionner les messages du transport HOGP si leur contrat évolue.

### Étape 3 — Rationalisation

- isoler la persistance `ActionRegistry` dans un composant interne ciblé;
- centraliser les contraintes statiques d'actions;
- supprimer ou archiver les implémentations HOGP non actives;
- mutualiser la découverte de l'outillage Windows.

Chaque étape doit rester une PR autonome avec transport simulé, tests de
concurrence et aucun besoin de prise de souris pour les deux premières passes
logicielles.

## 11. Points positifs à préserver

- architecture à deux canaux et absence de commande entrante sur la cible;
- interface de transport et double simulé;
- échantillons frais obligatoires et abandon sur changement de session ou
  topologie;
- publication de l'intention d'arrêt avant le verrou;
- états `UNKNOWN` et absence de rejeu automatique des actions ambiguës;
- journal et registre d'identifiants séparés mais sauvegardables ensemble;
- catalogue API générateur de documentation;
- capture ponctuelle, visible et corrélée à une action;
- limites de taille et validation des chemins dans l'outillage de releases;
- compilation C# avec warnings traités comme erreurs.

## 12. Limites de l'audit

- Aucun essai Bluetooth, appairage, mouvement, clic, défilement ou capture réelle.
- Aucun accès à MonOrdinateur et aucune vérification de la configuration des
  deux machines.
- Le MSIX actif et le projet C++ historique n'ont pas été construits.
- Les sept tests de diagnostics matériels n'ont pas été exécutés.
- Pas de mesure de couverture, d'analyseur de types, de linter ou de fuzzing
  disponible sans installer d'outil supplémentaire.
- Les performances et preuves matérielles déclarées dans la documentation ne
  sont pas revalidées par cet audit et ne fondent aucun constat positif ou
  négatif ci-dessus.
- L'analyse de sécurité est une revue de code, pas un test d'intrusion.

## 13. Verdict final

La maintenabilité est **moyenne à bonne sur le cœur Python**, grâce aux
frontières nettes, aux états explicites et aux tests de concurrence/persistance.
La capacité d'évolution est réelle : de nouvelles actions ou stratégies de
trajectoire peuvent être ajoutées sans refonte de l'architecture.

La robustesse opérationnelle globale reste toutefois **insuffisante pour un
composant de contrôle qui revendique un arrêt d'urgence borné**, principalement
à cause du transport non borné et de la poursuite possible avec bouton
incertain. La dette multi-langages et l'ambiguïté entre moteurs actifs et
historiques augmenteront le coût des prochaines évolutions si elles ne sont pas
rationalisées.

**Verdict final : `MAINTENABLE_WITH_MAJOR_RESERVATIONS`.** Corriger les quatre
actions P1 suffit à améliorer fortement le verdict; aucune refonte totale n'est
recommandée.
