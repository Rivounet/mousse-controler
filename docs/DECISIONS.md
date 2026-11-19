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

| D-028 | 2026-11-20 | Validé | Séparer transport HOGP, contrôle de position, trajectoire pure et orchestration de séquence | Le moteur de trajectoires n'accède jamais au Bluetooth ; toute arrivée est confirmée par une mesure réelle |
| D-029 | 2026-11-20 | Validé | Agent cible visible .NET Framework 4.8, sortie HTTPS seulement, lancé par tâche interactive temporaire | Aucun service caché, démarrage automatique ou commande souris sur la cible ; session console vérifiée |
| D-030 | 2026-11-20 | Validé | Secrets HMAC et bearer protégés par DPAPI ; TLS épinglé ; pare-feu limité au port, programme et deux hôtes privés | Ne publier ni secret, certificat privé, adresse privée exacte ni identifiant matériel |
| D-031 | 2026-11-20 | Validé | Zones physiques validées conservativement contre la topologie et sélectionnées avec une graine configurable | Rectangles, cercles et polygones sont reproductibles en test ; une zone traversant un vide d'écran est refusée |
| D-032 | 2026-11-20 | Bloqué par confirmation humaine | Utiliser une identité MSIX avec capacité `bluetooth`, exigée par Windows pour la publicité GATT | Paquet signé de développement prêt ; aucune élévation globale ou baisse de protection ; approbation du certificat utilisateur nécessaire avant essai réel |

## En cas de changement

Ajouter une ligne datée avec la décision remplacée et sa justification ; ne pas effacer silencieusement une décision antérieure. Répercuter les modifications sur [ROADMAP.md](ROADMAP.md), [PLANNING.md](PLANNING.md) et [ARCHITECTURE.md](ARCHITECTURE.md) lorsque cela s'applique.

**Inconnues majeures :** acceptation réelle du service HOGP par le pilote,
bonding/chiffrement avec MonOrdinateur, chargement du pilote souris natif,
reconnexion et stabilité. L'accès distant n'est plus une inconnue bloquante du
MVP ; l'activation locale réelle et le rollback restent à qualifier.
