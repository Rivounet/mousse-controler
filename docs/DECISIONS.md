# Décisions et hypothèses

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

| D-029 | 2026-11-19 | Validé | Priorité au Bluetooth LE HID natif entre mini-pc-backend et MonOrdinateur ; récepteur USB Logitech Nano 046D:C534 exclu du transport | Les pilotes HID natifs Windows reçoivent les commandes ; pont HID matériel seulement en repli après arbitrage ; aucune usurpation Logitech ni garantie d'indétectabilité |
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
