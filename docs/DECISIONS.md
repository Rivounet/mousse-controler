# Décisions et hypothèses

Ce registre est chronologique : les décisions plus récentes complètent ou
remplacent les états antérieurs. L'état courant des constats est centralisé dans
[ROBUSTESSE.md](ROBUSTESSE.md).

Les décisions ne sont pas des preuves de faisabilité. Pour chaque choix structurant, noter **date, statut, motivation et effet**. Ce journal fait foi avec la roadmap.

| ID | Date | Statut | Décision / hypothèse | Conséquence |
|---|---|---|---|---|
| D-001 | 2026-11-19 | Validé | Dépôt officiel : `Rivounet/mousse-controler` | Code et documentation de référence dans ce dépôt |
| D-002 | 2026-11-19 | Validé | Développer avec Codex Desktop sur le PC Windows | Ne pas confondre poste de développement et machine d'exécution |
| D-003 | 2026-11-19 | Validé | Exécuter, déployer et tester sur `mini-pc-backend` | Les résultats locaux seuls sont insuffisants |
| D-004 | 2026-11-19 | Validé | PC cible Windows, réception Bluetooth HID native, sans agent dédié | Appairage Bluetooth autorisé, logiciel récepteur non requis |
| D-005 | 2026-11-19 | Validé | Pilotage par **jalons**, sans échéances calendaires | Validation sur livrables et preuves |
| D-006 | 2026-11-19 | Validé | ChatGPT responsable de la documentation et de la revue du code | Codex propose/implémente ; revue indépendante avant fusion |
| D-007 | 2026-11-19 | Priorité validée, faisabilité ouverte | Tenter d'abord le Bluetooth intégré au mini-PC | J2 décide GO/NO-GO selon tests réels |
| D-008 | 2026-11-19 | À qualifier | OS, pilote et rôle BLE périphérique de mini-pc-backend | Inventaire J1/J2 préalable à tout choix de bibliothèque |
| D-009 | 2026-11-19 | Proposé | Contrat API local, authentifié, commandes relatives et arrêt d'urgence | Design à valider pendant J3 |
| D-010 | 2026-11-19 | Validé | Pas de fusion ni de déploiement durable implicite | Arbitrage explicite après revue |
| D-011 | 2026-11-19 | Validé | Prévoir une procédure et du code robustes pour l'accès distant, la synchronisation Git et le déploiement vers mini-pc-backend | J1 qualifie l'accès ; J4 livre et teste l'automatisation |
| D-012 | 2026-11-19 | Cible à qualifier | GitHub reste la référence officielle ; copie distante et versions exécutées sur mini-PC sont isolées | Pas de deuxième source de vérité, pas de réinitialisation Git destructive ; choix transport soumis à inventaire |

| D-013 | 2026-11-19 | Validé | ChatGPT rédige les mandats Codex et supervise la gestion Git/GitHub | Mandats ciblés ; contrôle du diff, des SHA, des PR et des fusions avant validation |
| D-014 | 2026-11-19 | Validé | Premier mandat = amorçage from scratch et diagnostic non destructif | Pas de prototype HID ou de changement système avant vérification de l'environnement |

| D-015 | 2026-11-19 | Amendé par D-021 | Centraliser la reprise future dans `docs/REPRISE.md` ; ancien archivage des mandats abandonné | Reprise fondée sur l'état Git, le jalon en cours et des livrables vérifiables |

| D-016 | 2026-11-19 | Qualification partielle | Rapport MC-INIT-001 : SSH et listing SFTP opérationnels, indicateur BLE périphérique favorable sur les deux PC | J1 reste ouvert ; HID, transfert réversible et rollback non démontrés ; preuves expurgées désormais examinées dans PR #1 ; contrôles matériels restants ouverts |
| D-017 | 2026-11-19 | Proposition retenue pour qualification | Privilégier OpenSSH/SFTP existants et scripts compatibles PowerShell 5.1 distant | Tester les droits minimaux, l'identité hôte, les hash, les erreurs et le rollback avant déploiement réel |

| D-018 | 2026-11-19 | Validé | Codex publie sur GitHub les rapports et preuves expurgés de chaque mandat via branche et PR Draft | ChatGPT réalise les revues directement depuis GitHub ; pas de transfert manuel systématique par l'utilisateur |

| D-019 | 2026-11-19 | Revue réalisée | PR #1 : 10 fichiers, 9 empreintes concordantes avec fins de ligne CRLF ; PASS documentaire, MC-INIT-001 PASS_WITH_RESERVATIONS | J1 reste ouvert ; PR Draft non fusionnée, MC-INIT-002 préparé sans autorisation implicite d'écriture distante |

| D-020 | 2026-11-19 | Validé avec réserves | Revue PR #2 MC-INIT-002 : 14 fichiers, 13 empreintes concordantes, 31 tests locaux attestés, SSH/SFTP/transfert de 63 octets/arrêt témoin documentés | J1 clôturé avec réserves sur le canal distant ; synchronisation de release par SHA, exécution persistante et rollback transférés explicitement à J4 ; PR #2 reste Draft non fusionnée |

| D-021 | 2026-11-19 | Validé | ChatGPT fournit tous les mandats Codex intégralement dans le chat, **sans enregistrement dans GitHub** | Conserver sur GitHub seulement documentation de référence, roadmap/planning, décisions, revues, code, rapports et preuves ; retirer les fichiers de mandats existants |

| D-022 | 2026-11-19 | Validé | Une livraison ou une nouvelle PR Codex ne déclenche pas automatiquement de revue de code exhaustive par ChatGPT | Suivi Git/GitHub et des jalons courant ; revue approfondie seulement sur demande explicite de l'utilisateur ou à un point de contrôle préalablement convenu ; fusion toujours soumise à décision explicite |

| D-023 | 2026-11-19 | Validé | Mandats Codex orientés vers un objectif fonctionnel complet et vérifiable, autonomie technique encadrée plutôt que micro-mandats | Codex conçoit, implémente, teste et corrige dans le même mandat ; points d'étape significatifs ; arrêt seulement pour décisions structurantes ou opérations sensibles ; PR Draft cohérentes, revues sur demande |

| D-024 | 2026-11-19 | Validé, remplace D-002 et D-003 pour l'organisation courante et amende D-004 sur le rôle cible | Codex, Git, développement, tests et exécution résident directement sur `mini-pc-backend` ; commandes vers `MonOrdinateur` par Bluetooth HID, retour de position réelle par un canal LAN privé sécurisé distinct | Agent Windows visible limité à `GetCursorPos` et à la transmission horodatée multi-écrans/DPI ; aucune réception/exécution de commande souris ; documenter installation, arrêt, fraîcheur et protections réseau |

| D-025 | 2026-11-19 | Validé | Conserver les composants SSH/SFTP et releases sans les supprimer, en les classant comme maintenance/rollback secondaires | Le travail des PR #2 et #3 est préservé ; il ne bloque pas J2 et devra être requalifié avant un nouvel usage distant réel |

| D-026 | 2026-11-19 | Qualification renforcée | Le Realtek et Windows exposent rôle périphérique BLE ; radio On temporaire, fournisseurs HID/Battery, quatre caractéristiques HID et Report Reference créés sans publicité puis radio restaurée Off | Device Information est réservé (`DisabledByPolicy`) ; `GO` exige encore publicité, bonding, chargement HID natif et événement souris réels |

| D-027 | 2026-11-19 | Validé | Consolider les commits utiles des PR #1 à #3 sur une branche neuve issue de `main`, sans modifier les PR historiques | Une PR Draft unique MC-REPRISE-001 porte la base cohérente ; aucune fusion ou fermeture automatique |

| D-028 | 2026-11-19 | Validé ; complète D-024 et amende D-004 | Retour de position réelle depuis MonOrdinateur via LAN privé sécurisé, distinct du Bluetooth HID | Agent Windows visible limité à GetCursorPos, topologie, session et transmission HTTPS authentifiée ; aucune exécution de commandes souris ; D-024 reste la décision de localisation de Codex |

| D-029 | 2026-11-19 | Historique, remplacé par D-078 | Priorité au Bluetooth LE HID natif entre mini-pc-backend et MonOrdinateur ; récepteur USB Logitech Nano 046D:C534 exclu du transport | D-078 interdit désormais tout matériel ou transport de repli ; aucune usurpation Logitech ni garantie d'indétectabilité |
| D-030 | 2026-11-19 | Validé | MC-HID-EXEC-001 confié à Codex exécuté sur mini-pc-backend, avec intervention autorisée sur MonOrdinateur via accès distant authentifié à établir/qualifier | Développement et qualification des deux côtés coordonnés dans un mandat unique ; pas de deuxième mandat cible indépendant, ni fusion automatique |
| D-031 | 2026-11-19 | Validé | Contrôle par séquences de zones A→B→C : rectangle, cercle ou polygone ; sélection aléatoire d'un point interne par zone | Position réelle confirmée par agent LAN et correction HID ; graine de test reproductible ; validation géométrique et multi-écrans |
| D-032 | 2026-11-19 | Validé | Trajectoires courbes, vitesse variable avec accélération/décélération et micro-variations bornées seulement pendant les déplacements | Moteur de trajectoires indépendant du transport HID ; comportement paramétrable et interruptible, sans objectif de dissimulation d'automatisation |
| D-033 | 2026-11-19 | Validé | Après arrivée : attente temporisée configurable ou attente de commande explicite, combinables dans une séquence | États de séquence, pause/reprise/étape suivante/arrêt, aucune reprise/reconnexion ne rejoue les actions déjà effectuées |
| D-034 | 2026-11-19 | Qualification partielle | La radio du mini-PC activée temporairement permet la création GATT HID/Battery et caractéristiques sans publicité ; retour Off confirmé | Lever l'ancienne incertitude RadioNotAvailable ; HOGP réel, publicité, pairing, mouvement et retour LAN restent non qualifiés (preuves PR #5) |
| D-035 | 2026-11-20 | Validé | Séparer transport HOGP, contrôle de position, trajectoire pure et orchestration de séquence | Le moteur de trajectoires n'accède jamais au Bluetooth ; toute arrivée est confirmée par une mesure réelle |
| D-036 | 2026-11-20 | Validé | Agent cible visible .NET Framework 4.8, sortie HTTPS seulement, lancé par tâche interactive temporaire | Aucun service caché, démarrage automatique ou commande souris sur la cible ; session console vérifiée |
| D-037 | 2026-11-20 | Validé | Secrets HMAC et bearer protégés par DPAPI ; TLS épinglé ; pare-feu limité au port, programme et deux hôtes privés | Ne publier ni secret, certificat privé, adresse privée exacte ni identifiant matériel |
| D-038 | 2026-11-20 | Validé | Zones physiques validées conservativement contre la topologie et sélectionnées avec une graine configurable | Rectangles, cercles et polygones sont reproductibles en test ; une zone traversant un vide d'écran est refusée |
| D-039 | 2026-11-20 | Bloqué par confirmation humaine | Utiliser une identité MSIX avec capacité `bluetooth`, exigée par Windows pour la publicité GATT | Paquet signé de développement prêt ; aucune élévation globale ou baisse de protection ; approbation du certificat utilisateur nécessaire avant essai réel |
| D-040 | 2026-11-20 | Validé ; clôt D-039 | Conserver le MSIX HOGP signé dont le certificat public exact est limité à `LocalMachine\TrustedPeople` | Publicité, appairage `ConfirmOnly` chiffré, HID natif et rapports réels qualifiés sans magasin Root ni désactivation de protection |
| D-041 | 2026-11-20 | Validé ; amende D-036 | Exploiter l'agent visible et le contrôleur par tâches interactives `AtLogOn`, sans auto-logon | Reconnexion après redémarrage et reprise transitoire qualifiées ; ouverture manuelle de session toujours requise |
| D-042 | 2026-11-20 | Validé | Sérialiser l'arrêt effectif et toutes les émissions HID dans le contrôleur, avec intention d'arrêt publiée avant le verrou | Toute commande en attente revalide l'état sous verrou ; arrêt répété idempotent ; `start()` seul ouvre une nouvelle époque de commandes |
| D-043 | 2026-11-20 | Validé avec réserves | Retenir le verdict MC-HID-EXEC-001 `PASS_WITH_RESERVATIONS` dans la PR #6 Draft | HOGP, LAN, fonctions souris, trajectoires, séquences, AtLogOn et performances sont qualifiés ; réserves sur latence LAN aller simple et reprise GATT transitoire ; fusion explicite requise |
| D-044 | 2026-11-20 | Validé ; clôt la porte de fusion de D-043 | Reconnaître la fusion de la PR #6 dans `main` au commit `77d4a5939673053fa2e0dae73bc3a284a8597ac7` et consolider les installations sans réinstallation inutile | Contenus HOGP et agent installés concordants avec les artefacts qualifiés ; contrôleur Python rechargé depuis `main` ; verdict `PASS_WITH_RESERVATIONS` inchangé |

## En cas de changement

Ajouter une ligne datée avec la décision remplacée et sa justification ; ne pas effacer silencieusement une décision antérieure. Répercuter les modifications sur [ROADMAP.md](ROADMAP.md), [PLANNING.md](PLANNING.md) et [ARCHITECTURE.md](ARCHITECTURE.md) lorsque cela s'applique.

**Réserves résiduelles :** la latence LAN aller simple absolue n'est pas
calculable sans synchronisation d'horloges et une reprise GATT transitoire peut
précéder le retour automatique à `subscribed=True`. L'acceptation HOGP, le
bonding/chiffrement, le pilote souris natif, la reconnexion, AtLogOn, l'arrêt et
les performances ne sont plus des inconnues : ils sont qualifiés dans la PR #6.

## Décisions validées — MC-MOUSE-ACTIONS-001 (20 novembre 2026)

| ID | Statut | Décision | Conséquence |
|---|---|---|---|
| D-045 | Validé | Souris uniquement : clics multiples, maintien, glisser-déposer, roulette, boutons compatibles ; actions composables en séquences. Aucun clavier. | Les primitives existantes restent compatibles. |
| D-046 | Validé — 1B | Capture facultative automatiquement avant/après une action configurée, jamais continue ni périodique ; écran entier contenant le curseur au moment de la capture. Pas de commande indépendante de capture. | Toute demande hors contexte d'action est rejetée. |
| D-047 | Validé — 2C/3C | Préparer analyse visuelle locale future sans développer de moteur ; rétention des images configurable par action/séquence. | Stockage privé avec TTL/suppression et interface `analysis_ready`. |
| D-048 | Validé — 4B | Retour automatique des résultats et états d'actions par WebSocket, identifiant stable ; distinguer émission HID et résultat réellement observé. | WebSocket loopback authentifié et événements corrélés. |
| D-049 | Validé — 5C | Politique d'échec configurable arrêt/retry/poursuite, arrêt par défaut ; aucun rejeu automatique des actions non idempotentes à issue incertaine. | `UNKNOWN` prévaut dès qu'une émission non idempotente est ambiguë. |
| D-050 | Validé | Conserver Bluetooth HID pour la souris et LAN sécurisé pour retour et captures ; agent cible visible, autorisé uniquement à mesurer et capturer, jamais à commander la souris. | Aucun port de commande ajouté sur la cible. |
| D-051 | Réalisé | Conserver le descripteur HOGP appairé à cinq boutons et molette verticale ; exposer la roulette horizontale indisponible car `AC Pan` est absent. | Évite une rupture d'appairage ou une fausse émulation horizontale ; capacité interrogeable par API. |
| D-052 | Réalisé | Remettre les demandes de capture dans la réponse HTTPS sortante de position, puis recevoir le PNG sur `/v1/capture` avec TLS épinglé, HMAC et séquence anti-rejeu. | Aucun port entrant ni service de commande sur MonOrdinateur ; demandes bornées avant/après uniquement. |
| D-053 | Réalisé | Journaliser hors Git les identifiants et derniers états d'action ; convertir `ACCEPTED/RUNNING` en `UNKNOWN` après redémarrage. | Une reconnexion ou reprise de processus ne peut jamais rejouer une action ambiguë. |
| D-054 | Réalisé | Réserver `CONFIRMED` à une observation indépendante de position ; clics, boutons et roulette terminent à `EXECUTED`. | L'émission HID n'est jamais présentée comme effet applicatif confirmé. |
| D-055 | Qualification partielle | Déployer le moteur mini-PC sur SHA exact et fournir un installateur cible réversible limité à la tâche `MousseControler-PositionAgent`. | Runtime mini-PC et WebSocket réels qualifiés ; installation/capture/événements matériels cible exigent la session interactive propriétaire de la tâche. |
| D-056 | Validé ; clôt D-055 | Utiliser le canal SSH hors sandbox strictement limité à l'alias `MonOrdinateur`, puis une tâche temporaire interactive limitée pour le témoin. | La session 0 SSH n'est jamais confondue avec la console ; aucun pare-feu, compte, ACL ou mécanisme de protection n'est modifié. |
| D-057 | Validé avec réserves | Retenir le verdict matériel `PASS_WITH_RESERVATIONS` après qualification des 17 actions, captures avant/après, WebSocket, arrêt d'urgence, reconnexion et non-rejeu. | Toute prise de souris future exige un avertissement et un accord explicite ; roulette horizontale hors capacité et dossier de staging vide résiduel documentés. |
| D-058 | Validé | Réserver durablement tout identifiant d'action accepté pendant 30 jours par défaut, dans un registre `.ids` distinct du journal compactable ; l'expiration exige aussi l'éviction de l'état courant. | Saturation, compaction, reconnexion, redémarrage et réémission ne permettent pas un rejeu pendant le contrat ; journal et registre sont administrés ensemble. |
| D-059 | Validé | Déclarer une capture `DELETED` seulement après constat de l'absence du fichier ; persister `DELETE_FAILED` et récupérer les fichiers orphelins au redémarrage. | Un refus de suppression reste visible, retentable et compté dans les quotas ; l'index de capture est un état de production à conserver. |

| D-060 | 2026-11-20 | Validé | Fusion explicite de la PR #8 MC-MOUSE-ACTIONS-001 dans `main` au commit `e0658142a65d8b494f109efa3318c6ea21feac3d` après revue des correctifs | J6 intégré avec verdict `PASS_WITH_RESERVATIONS` ; tests 185/185 publiés ; vérification de la synchronisation des installations restant distincte de la fusion Git |
| D-061 | 2026-11-20 | Validé avec réserves | Synchroniser le clone par fast-forward et relancer uniquement le contrôleur mini-PC pour charger le code fusionné et migrer le registre `.ids`; conserver l'agent cible déjà conforme. | Les deux machines utilisent les composants attendus, journal et `.ids` sont présents ensemble, production saine sans nouvelle émission HID ni capture ; verdict post-fusion `PASS_WITH_RESERVATIONS`. |

## D-062 — Contre-expertise indépendante et plan de correction global (20 novembre 2026)

**Décision de pilotage :** conserver les deux rapports d'audit originaux distincts, archiver leur comparaison contradictoire dans [MC-AUDIT-CONSOLIDATION-001](../audits/2026-11-20-consolidation/REPORT.md), retenir le verdict `MAINTENABLE_WITH_MAJOR_RESERVATIONS` et prioriser la sûreté/robustesse avant le refactoring structurel et toute extension fonctionnelle majeure.

**Références :** audit ChatGPT sur `audit/independent-review-chatgpt-20261120` (commit `81e840668a07f135f925b7f9e0b92c083c3cdcf0`), audit Codex [PR #11](https://github.com/Rivounet/mousse-controler/pull/11) (Draft, non fusionnée), base commune `d19db664bc1e7d83ab1d289f89373f9e327a482b`. Les quatre P1 prioritaires sont HOGP non borné, bouton incertain, quota captures non strict et absence de bornes explicites sur les connexions/lectures LAN. Les autres risques sont conservés dans la matrice du rapport.

**Exécution :** lots R0 à R6 définis au planning ; aucune correction, déploiement, essai HID réel, capture réelle ou fusion de PR n'est autorisé implicitement. Conserver la séparation entre code GitHub, clone local et processus en service. Une revue et une autorisation de fusion restent requises pour chaque PR.

## D-063 — Transactions bornées pour stockage, runtime et agent (21 novembre 2026)

**Décision :** le quota de captures porte sur le pic physique complet avant
écriture ; le runtime possède explicitement toutes ses ressources et les ferme
en ordre inverse sans abandon au premier échec ; une mise à jour PositionAgent
n'est confirmée qu'après contrôle du binaire, de la tâche et du processus.

**Conséquence :** les fichiers temporaires, index et orphelins sont inclus dans
le plafond et restent traçables ; les erreurs de fermeture sont agrégées ; une
panne post-remplacement restaure la sauvegarde en deux tentatives maximum ou
laisse un marqueur durable `RECOVERY_REQUIRED` qui interdit toute nouvelle
installation ambiguë. La qualification R3 reste logicielle et n'autorise ni
déploiement, ni tâche cible, ni HID/capture réelle.

## D-064 — Qualification locale Windows et profils fermés (21 novembre 2026)

**Décision :** la qualification de Mousse-controler est exécutée localement
sous Windows. GitHub sert au versionnement, aux PR et à la conservation des
preuves. GitHub Actions et les services CI externes sont exclus.

**Conséquence :** les profils `software`, `build` et `full-local` sont des
listes fermées et ne peuvent lancer ni diagnostic matériel, ni installation,
ni déploiement, ni accès distant. Les diagnostics matériels restent hors de
l'orchestrateur et exigent une autorisation explicite distincte. Un outil
absent, une interruption ou un test en échec produit un verdict non favorable
et une sortie non nulle. Le build découvre Roslyn et le SDK Windows de manière
contrôlée, sans changer la cible .NET Framework ni les contrats des artefacts.

## D-065 — Refactoring R5 limité aux gains démontrés (21 novembre 2026)

**Décision :** corriger C-13 par un repli déterministe borné sur un sommet et
C-14 par une insertion unique contrôlée avant mutation. Conserver la tolérance
des paramètres inconnus, les deux séquenceurs, les persistances séparées et les
sources C++ HOGP historiques.

**Conséquence :** les polygones valides extrêmes restent échantillonnables sans
boucle non bornée et les trois registres refusent les doublons sans écrasement.
C-09/C-11/C-12/C-17 restent documentés mais non déclarés terminés : leur
suppression, convergence ou extraction exige une PR dédiée et une mesure nette.

## D-066 — Clôture documentaire R0–R6 (21 novembre 2026)

**Décision :** prendre `docs/ROBUSTESSE.md` comme matrice unique C-01 à C-17 et
recentrer README, roadmap, planning, reprise et tests sur l'état courant. R0–R5
sont fusionnés ; R5 a corrigé uniquement C-13/C-14. C-09/C-11/C-12/C-17 restent
différés sans priorité automatique. La PR #11 reste ouverte Draft non fusionnée.

**Conséquence :** séparer définitivement fusion GitHub, qualification locale,
preuves matérielles historiques, synchronisation des machines et déploiement.
R1–R5 ne sont pas matériellement requalifiés. L'état des processus installés
reste à vérifier. Les profils Windows locaux demeurent la seule qualification
logicielle officielle ; GitHub Actions et toute CI externe restent exclus.

## D-067 — Autorisation de mise en service contrôlée (21 novembre 2026)

**Décision utilisateur :** autoriser sur `mini-pc-backend` et `MonOrdinateur` la mise en confiance du certificat **public** MSIX v2 vérifié dans le magasin approprié, l'installation du MSIX signé, la mise à jour transactionnelle de PositionAgent, la synchronisation du contrôleur, la migration des seules configurations et tâches Mousse-controler, l'activation progressive et les contrôles de santé/communication. Sauvegarde et rollback obligatoires.

**Limites :** aucun mouvement/clic HID réel, aucune prise de souris ni capture sans accord matériel spécifique ultérieur. Aucun affaiblissement de Defender/Smart App Control, aucune permission générale SSH/ACL/administrateur, aucun changement hors composants Mousse-controler. Cette décision ne vaut pas fusion automatique d'une nouvelle PR.

**État :** autorisation accordée, **exécution et qualification opérationnelle non encore attestées**. Le dernier `main` qualifié pour la préparation est `e5553f2ff3342b16546128e4a351b57f2e2801dc` (PR #24 fusionnée) ; `OPERATIONAL_PASS` exige des preuves sur les binaires et processus réellement actifs. La qualification matérielle demeure une porte distincte.

## D-068 — Déplacement relatif confirmé en pixels (21 novembre 2026)

**Décision :** conserver `move_relative` comme primitive brute en unités HID et
ajouter `move_relative_confirmed` pour le contrat fonctionnel en pixels écran.
Cette dernière action calcule une cible depuis une mesure PositionAgent fraîche
et utilise une boucle fermée strictement bornée. La configuration Windows du
pointeur n'est ni modifiée ni contournée.

**Motivation :** l'essai matériel de la PR #26 a observé 9 pixels pour un
rapport relatif de 10 unités avec l'accélération Windows active, puis un retour
exact par positionnement confirmé. L'hypothèse « une unité HID égale un pixel »
est donc invalide ; l'accélération est un contributeur observé, sans être
présentée comme cause mécanique unique.

**Conséquence :** fraîcheur, durée, amplitude, mouvement cumulé, itérations,
stagnation, oscillation et absence de progrès sont bornés. Une émission dont le
résultat devient incertain n'est jamais rejouée. La correction logicielle doit
être qualifiée avant un unique scénario matériel séparément autorisé ; elle ne
change ni HOGP, ni PositionAgent, ni l'installation active.

## D-069 — Clôture opérationnelle et preuve stabilisée (21 novembre 2026)

**Décision :** retenir PositionAgent comme observation indépendante après une
fenêtre passive bornée ; conserver `move_relative` en unités HID et employer la
boucle fermée pour tout contrat en pixels. Une observation immédiate ne permet
ni de conclure à l'absence d'effet ni de rejouer une action incertaine.

**Conséquence :** la validation finale couvre les fonctions souris, la
précision confirmée, les communications, une capture privée et la récupération.
Un arrêt HOGP non acquitté impose un redémarrage qualifié avant reprise. Les
captures brutes restent privées et sont supprimées après empreinte ; l'export
expurgé calcule son SHA-256 via .NET pour rester compatible avec le contexte
Windows PowerShell réellement exécuté.

## D-070 — Couche applicative et propriété exclusive du HID (27 novembre 2026)

**Décision :** conserver les contrats publics des actions et des séquences,
mais déplacer leur composition hors de l'adaptateur HTTP. Un
`MouseApplicationService` porte les cas d'usage et partage un
`OperationCoordinator` avec les deux moteurs. Toute action, séquence ou
commande historique possède un bail exclusif pendant toute son opération
logique ; l'arrêt reste prioritaire et ne dépend pas de ce bail.

**Motivation :** le verrou du contrôleur protégeait les rapports individuels,
pas leur intention. Un test simulé a démontré qu'un déplacement historique
pouvait s'insérer pendant un maintien moderne et produire un glisser-déposer.

**Conséquence :** une action moderne attend dans sa file, une séquence réserve
le périphérique avant démarrage et une commande historique synchrone reçoit un
refus explicite si le périphérique est occupé. Aucun troisième moteur de
séquence ni changement de contrat matériel n'est introduit.

## D-071 — Feedback atomique et releases contrôleur immuables (27 novembre 2026)

**Décision :** publier position et topologie comme une même génération dans
`PositionStore`. Exécuter les tâches contrôleur uniquement depuis une release
extraite des objets Git d'un SHA propre, munie d'un manifeste et vérifiée avant
inscription puis à chaque lancement.

**Motivation :** la position et la topologie étaient mises à jour sous deux
verrous distincts. Par ailleurs, le runtime observé chargeait quatre fichiers
modifiés d'un worktree ; ni reproduction ni rollback par SHA n'étaient alors
possibles.

**Conséquence :** une génération incohérente est refusée fail-closed. Le mode
source mutable reste limité au développement manuel ; toute activation de la
nouvelle release conserve une porte distincte de qualification, sauvegarde,
rollback et décision de fusion.

## D-072 — Identités HOGP et qualification inter-machine exclusive (28 novembre 2026)

**Décision :** une émission HOGP n'est permise que vers l'unique abonné actif
dont l'identité WinRT hachée est configurée. Le pairage et la reconnexion de la
cible exigent eux aussi une empreinte attendue et ne sélectionnent jamais par le
seul nom. La télémétrie PositionAgent et la supervision de reconnexion restent
deux processus et deux responsabilités distinctes.

**Décision de qualification :** tout essai matériel like-prod utilise une
instance HOGP et des tâches dédiées. Un bail à durée limitée est acquis sur le
backend et un autre sur la cible ; ils doivent partager le même `run_id`, le
même SHA et se désigner mutuellement. La surface sûre et le pilote d'actions
refusent de démarrer si ces preuves ne sont pas fraîches et cohérentes.

**Conséquence :** une ancienne cible connectée, un second client, un nom BLE
dupliqué, un statut cible périmé ou un run concurrent provoquent un refus
fail-closed. La production `mini-pc-backend` et les preuves historiques de
`MonOrdinateur` ne sont ni utilisées ni présentées comme qualification de
`DESKTOP-NPIHO8K`.

## D-073 — Consentement Windows limité au provisioning HOGP (28 novembre 2026)

**Décision :** sur Windows Desktop, la validation système d'une demande de
pairage entrante est une étape manuelle unique de provisioning, jamais une étape
de démarrage ou de reprise. La fenêtre de pairabilité doit déclarer la politique
`windows-interactive`. La politique `unattended` est refusée avant l'accès radio
tant qu'aucun périphérique HOGP capable d'accepter lui-même le bonding n'est
retenu.

**Preuve :** au SHA `399ac5322df44663d84641ffcf655ac3287500b8`, le scan radio
et `Inspect` ont sélectionné un unique endpoint. Sans validation de la
notification backend, `Pair` a fini `Failed`, protection `None`, et aucune paire
n'a subsisté. Au même instant, le backend a journalisé `BTHUSB 37` (demande
entrante rejetée) puis les deux machines `BTHUSB 29` (délai de sécurité).

**Critère de clôture :** après un consentement unique et un pairage
`ProtectionLevelUsed=Encryption`, prouver sans nouveau consentement la
reconnexion, le redémarrage de chaque machine, un cycle radio et la recréation ou
mise à jour du runtime avec identité et descripteur HOGP inchangés.

## D-074 — Identités d'enrôlement et de reconnexion HOGP (28 novembre 2026)

**Décision :** séparer l'identité radio éphémère utilisée pendant l'enrôlement
de l'identité Windows durable utilisée pour la reconnexion. L'inspection et le
pairage initial sélectionnent le nom exact et le hachage de l'adresse radio de
la fenêtre courante. Après preuve `ProtectionLevelUsed=Encryption`, le résultat
publie en plus le hachage de l'identifiant AEP appairé. Seul ce second hachage
est accepté par le moniteur persistant `--hogp-reconnect`.

**Conséquence :** une rotation d'adresse BLE ou un redémarrage du fournisseur
HOGP ne casse pas la sélection de la paire persistante. Ni l'adresse radio ni
l'identifiant AEP bruts ne sont journalisés. Un pairage non chiffré, un rollback
ou une erreur ne produit jamais d'identité durable utilisable.

## D-075 — Enrôlement atomique face aux adresses privées BLE (28 novembre 2026)

**Décision :** amender la partie enrôlement de D-072 et D-074. Une empreinte
d'adresse radio observée par un premier processus ne peut pas autoriser un
second processus : la pile Windows et le fournisseur HOGP peuvent présenter une
nouvelle adresse privée avant la seconde énumération. `PairingTool` réalise donc
dans un seul processus le scan actif, l'exigence d'un candidat unique au nom
exact/connectable/HID, la résolution directe de cette adresse par
`FromBluetoothAddressAsync` et le `PairAsync(Encryption)` standard. La validation
Windows manuelle reste le point de confiance humain du provisioning.

**Conséquence :** le script de pairage direct par empreinte radio est supprimé.
L'adresse et son hachage restent des diagnostics de la tentative, jamais une
identité transmissible. Après succès chiffré seulement, le hachage AEP durable
devient l'unique identité acceptée par `Connect` et `--hogp-reconnect`.

## D-076 — La présence AEP n'est pas une porte de reconnexion (28 novembre 2026)

**Décision :** après un pairage chiffré, la sélection de reconnexion exige le
nom exact, l'empreinte AEP durable et `Pairing.IsPaired`, mais ne refuse pas un
endpoint uniquement parce que `System.Devices.Aep.IsPresent` vaut `false`.
L'ouverture `BluetoothLEDevice.FromIdAsync` puis la découverte non cachée de
l'unique service HID constituent la preuve autoritative de disponibilité.

**Motif :** Windows peut conserver `IsPresent=false` sur l'Association Endpoint
alors que le bond est chiffré, que le nœud HID PnP est sain et que la pile HOGP
est déjà abonnée. Utiliser ce drapeau comme précondition créait un faux négatif
et empêchait le moniteur de reconnexion d'atteindre la vérification GATT réelle.

**Conséquence :** l'identité durable et l'état appairé restent fail-closed ; le
client ne contourne ni le chiffrement ni l'unicité. Un endpoint absent échoue
toujours lors de l'ouverture ou de la découverte GATT, puis le moniteur réessaie
de façon bornée sans déclencher de nouvel appairage.

## D-077 — Session GATT maintenue pendant les indisponibilités radio (28 novembre 2026)

**Décision :** après la découverte non cachée de l'unique service HID, le
moniteur conserve son `GattSession`, exige `CanMaintainConnection` et positionne
`MaintainConnection=true`. Une transition temporaire vers `Closed` ne détruit
plus le device, le service et la session : Windows conserve la demande et
reconnecte lorsque le périphérique redevient disponible. Ces ressources ne sont
libérées, avec `MaintainConnection=false`, qu'à l'arrêt du moniteur ou avant une
nouvelle ouverture initiale ayant échoué.

**Motif :** la découverte GATT non cachée est une opération finie dont le délai
est variable et peut atteindre plusieurs minutes quand des requêtes sont mises
en file. La détruire puis la relancer à chaque déconnexion radio accumulait des
tentatives `Unreachable`. `GattSession.MaintainConnection` est la primitive
Windows prévue pour attendre indéfiniment et reprendre dès disponibilité.

**Conséquence :** le cycle radio ne déclenche ni nouvel appairage ni boucle de
découverte GATT. Les transitions `Closed` puis `Active` sont journalisées et la
reprise `Active` constitue la preuve de reconnexion de la même session maintenue.

## D-078 — Propriété HOGP exclusive du pilote cible Windows (28 novembre 2026)

**Décision propriétaire :** conserver exclusivement le transport Bluetooth sur
les radios Windows existantes, sans matériel supplémentaire et sans changement
de transport. SSH reste un moyen de maintenance de dernier recours et ne porte
jamais les commandes souris. Après l'enrôlement chiffré, le pilote HID natif
Windows est l'unique Report Host : `PositionAgent` redevient strictement un agent
de télémétrie/capture et son mode `--hogp-reconnect` est supprimé.

**Motif :** le moniteur applicatif ouvrait un second client GATT sur le service
HID déjà possédé par Windows. Les essais sur `DESKTOP-NPIHO8K` ont montré qu'une
session `MaintainConnection=true` restait `Closed` après cycle radio et qu'un
probe distinct reproduisait ce défaut ; cette couche ne rétablissait donc pas la
connexion et pouvait concurrencer le pilote HID. Les bibliothèques GATT tierces
resteraient des enveloppes de la même pile Windows.

**Conséquence :** D-074 à D-077 restent les traces historiques des hypothèses et
essais, mais leurs prescriptions de moniteur persistant sont remplacées par la
présente décision. `PairingTool Connect` demeure un diagnostic ponctuel fondé
sur l'identité AEP durable et doit libérer toutes ses références avant un essai
fonctionnel. La porte like-prod exige la reconnexion native après redémarrage du
provider, cycle radio, redémarrage cible et mise à jour à identité/descripteur
inchangés, sans nouveau consentement. L'instance HOGP de production reste hors
qualification.

## D-079 — Provider stable et plan de contrôle API séparé (28 novembre 2026)

**Constat matériel :** au SHA `d179e93bb05a502846eba1e9679d5662a9000b5f`,
le pilote HID de `DESKTOP-NPIHO8K` s'est abonné automatiquement tant que le
provider GATT qualificatif conservait sa durée de vie. Après recréation du
provider, aucun abonnement n'est revenu pendant plus de 180 secondes, après
cycle de chaque radio ni après redémarrage de la cible. L'annonce conservait
pourtant le même nom, le service HID, le type connectable, l'adresse hachée et
l'AEP appairé chiffré. Le nœud HID restait absent. Un cycle radio cible a en
outre placé l'adaptateur Qualcomm Atheros en code 43 jusqu'au redémarrage.

**Décision backend :** l'absence d'abonné est un état externe
`awaiting_subscriber`, jamais une panne du moteur. La supervision ne recrée le
provider que si son canal de commande est réellement défaillant, avec délai de
reprise borné. Le provider doit rester stable pendant les mises à jour du code
qui n'affectent pas son contrat ; une évolution ultérieure de son hébergement
devra préserver cette propriété.

**Décision cible :** un runtime déployé distinct, `HogpControlAgent`, peut
utiliser l'API HTTPS sortante comme plan de contrôle. Il remonte radio, PnP,
pairage et présence HID puis exécute seulement une commande PnP explicitement
autorisée, liée à la génération du provider et à quatre empreintes enrôlées. Il
ne contient ni client GATT, ni pairage, ni API d'entrée ou d'injection. Les
redémarrages PnP exigent une tâche `Highest` installée une fois en contexte
administrateur ; sans preuve d'élévation, le backend n'émet aucune commande.
Le terme « agent cible » désigne ce runtime déployé, pas l'agent Codex distant.
Son binaire, sa configuration et son état sont placés sous ACL protégées ; un
manifeste vérifie leurs empreintes et la définition de tâche avant démarrage.
La génération provider, la séquence, les identifiants déjà traités et tout
acquittement en attente persistent atomiquement. Une interruption pendant une
opération est publiée `outcome_unknown` et n'est jamais rejouée implicitement.
Toute recréation réelle du provider fait tourner sa génération ; un provider
vivant mais sans publicité est une panne distincte de l'absence d'abonné.

**Conséquence :** Bluetooth HOGP reste l'unique plan de données souris. L'API
ne transporte aucune action HID et ne remplace pas le pilote Windows ; elle
coordonne et atteste les opérations Windows bornées. SSH reste un secours de
maintenance. Les deux actions PnP sont désactivées par défaut et leur promotion
hors qualification exige une preuve matérielle favorable et une décision de
déploiement distincte.
