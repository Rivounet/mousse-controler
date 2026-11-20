# MC-AUDIT-CONSOLIDATION-001 — Arbitrage contradictoire et plan global de correction

**Date :** 20 novembre 2026  
**Référence immuable du code :** `d19db664bc1e7d83ab1d289f89373f9e327a482b` (`main` après PR #10).  
**Statut :** arbitrage documentaire ; aucune correction exécutée, aucun déploiement ni essai HID.  
**Sources indépendantes :**
- [Audit ChatGPT](https://github.com/Rivounet/mousse-controler/blob/audit/independent-review-chatgpt-20261120/audits/2026-11-20-chatgpt-independent/REPORT.md), branche isolée, commit `81e840668a07f135f925b7f9e0b92c083c3cdcf0`.
- [Audit Codex PR #11](https://github.com/Rivounet/mousse-controler/pull/11), rapport `qualification/MC-INDEPENDENT-AUDIT-001/RAPPORT.md`, SHA `42adb2976edac4048cfc2150ce247dc7c2951a74`; [preuves](https://github.com/Rivounet/mousse-controler/blob/42adb2976edac4048cfc2150ce247dc7c2951a74/qualification/MC-INDEPENDENT-AUDIT-001/evidence/EXECUTIONS.md).

Les rapports originaux restent **intacts et séparés**. Cette consolidation n'est pas une troisième expertise indépendante.

## 1. Verdict

**MAINTENABLE_WITH_MAJOR_RESERVATIONS.** Conserver l'architecture à deux machines, le transport HOGP, le canal de position HTTPS/HMAC, l'agent C# passif, le contrôleur Python, les états `EXECUTED/CONFIRMED/UNKNOWN`, l'anti-rejeu durable et le catalogue API centralisé. Pas de réécriture générale. Priorité à la sûreté des transitions de boutons, aux attentes bornées et aux limites de ressources.

Les deux audits concordent sur la qualité du découplage et sur le défaut de bornage HOGP. Codex apporte des reproductions logicielles pour trois défauts que ChatGPT n'avait pas détectés. ChatGPT identifie des défauts de coordination et de cycle de vie qui ne figuraient pas dans la liste prioritaire de Codex.

## 2. Matrice contradictoire

| ID consolidé | Source | Constat | Preuve | Priorité | Arbitrage |
|---|---|---|---|---|---|
| C-01 | Les deux | `NativeHogpTransport` attend `readline()` sans deadline; moteur WinRT potentiellement bloquant; `stderr` non drainé | Code + reproduction Codex d'un processus muet | **P1** | Corriger en premier, prévoir arrêt hors canal bloqué et état incertain |
| C-02 | Codex | `press/release` incertain avec `continue` peut laisser masque bouton à 1 et contrôleur actif | Reproduction en mémoire : `UNKNOWN`, `controller_stopped=False`, `controller_buttons=1` | **P1** | Quarantaine/arrêt fail-safe quelle que soit la politique métier |
| C-03 | Codex | Captures écrites avant contrôle strict du quota; `prune` peut échouer sans refuser l'upload | Code `capture.py`, tests de suppression refusée | **P1** | Admission avant écriture, quotas fichiers temporaires compris, échec fermé |
| C-04 | Codex | Serveur LAN sans timeout explicite de lecture/handshake ni plafond des connexions actives | Code `position_server.py`; impact non reproduit | **P1 préventif** | Borner temps/connexions; tests de clients lents et reprise du feedback |
| C-05 | ChatGPT | `stop` global n'appelle pas `SequenceRunner.stop()` | Code `command_server.py`; conséquence dynamique non reproduite | **P1/P2 à qualifier** | Tester états MOVING/WAITING/PAUSED puis corriger coordination, HID prioritaire |
| C-06 | Codex | `ActionExecutor.close()` quitte la boucle sans vider la file | Reproduction : action en file reste `ACCEPTED` | **P2** | Annuler/drainer les actions en attente, état terminal durable |
| C-07 | ChatGPT | Échec d'initialisation de serveur ne ferme pas explicitement les serveurs précédents | Code `app.py` | **P2** | Nettoyage inverse des ressources, `shutdown/server_close`, injection de pannes |
| C-08 | ChatGPT | Mise à jour agent Windows peut échouer après remplacement sans rollback automatique | Code `Update-InteractivePositionAgent.ps1` | **P2** | Tests transactionnels, restauration bornée, pas de modification de protections |
| C-09 | Les deux | Deux implémentations HOGP, dont C++ historique non inclus dans le MSIX actif | `Build-HogpPackage.ps1`, sources HOGP | **P2** | Cartographier usages, archiver seulement après preuve d'inutilité |
| C-10 | Les deux | Tests textuels et lacunes sur les chemins de panne; 7 diagnostics environnementaux | 188 tests logiciels Codex PASS; 7 non exécutés; 21 tests textuels recensés | **P2** | Séparer suites, opt-in matériel, tests comportementaux et CI |
| C-11 | ChatGPT | Deux séquenceurs indépendants, coordination partiellement dupliquée | `sequence.py`, `actions.py` | **P3** | Convergence seulement si gain prouvé, sans troisième moteur |
| C-12 | Les deux | `actions.py` et `PositionAgent.cs` concentrent plusieurs responsabilités | Revue statique | **P3** | Extraction ciblée après stabilisation, pas de refonte |
| C-13 | Codex | Polygones très fins parfois non échantillonnables | Reproduction 7/20 graines pour polygone valide extrême | **P3** | Échantillonnage déterministe/robuste, tests de géométries extrêmes |
| C-14 | Codex | `api_catalog._add` écrase une clé avant la vérification de doublons; paramètres inconnus tolérés | Code `api_catalog.py` | **P3** | Rejeter doublons à l'insertion; traiter paramètres inconnus selon compatibilité |
| C-15 | Codex | Chemins SDK/Build Tools absolus dans les scripts | Scripts de build | **P2/P3** | Découverte contrôlée des outils, builds reproductibles |
| C-16 | ChatGPT | Planning/roadmap/reprise/README contiennent statuts historiques présentés comme actuels | Documents au commit de référence | **P2 documentaire** | Nettoyage ciblé avec historique conservé |
| C-17 | ChatGPT | Persistance actions/captures et utilitaires PowerShell présentent répétitions techniques | Revue statique | **P3 optionnel** | Mutualiser seulement les primitives prouvées, sans fusion des données |

**Niveaux de preuve :** C-01, C-02, C-06 reproduits en simulation par Codex; C-03, C-04, C-05, C-07 et C-08 démontrés comme propriétés du code, mais effets opérationnels non qualifiés sur les machines. Aucun essai HID ni capture réelle dans les audits.

## 3. Comparaison des méthodes et limites

**ChatGPT :** inventaire GitHub, inspection statique, pas de test exécuté; a mieux souligné l'arrêt de la séquence historique, l'initialisation partielle et le rollback.  
**Codex :** inventaire du checkout, lecture des chemins actifs, compilation C# warnings-as-errors, syntaxe PowerShell, `generate_api_reference.py --check`, **188/188 tests logiciels PASS** sur **195 définis**; sept diagnostics matériels non lancés; reproductions en mémoire de HOGP muet, bouton incertain et file non drainée. Aucun MSIX natif reconstruit ni qualification sur les deux machines.  
**Arbitrage :** les preuves Codex renforcent les priorités sans établir la sûreté matérielle complète. L'absence d'un constat dans l'un des rapports ne l'invalide pas.

## 4. Plan global de correction — lots et critères de sortie

### R0 — Baseline et garde-fous (prérequis transversal)

- Figer le SHA de base, documenter API/états/limites et relever tests avant changement.
- Rendre l'exécution matérielle explicitement opt-in; ne jamais déclencher HID/capture réelle par les tests logiciels.
- Préparer doubles de processus muet, transport ambigu, client HTTPS lent, disque/quota, panne de démarrage et fermeture.
- Aucun changement de production, appairage, ACL, politiques Windows, secrets ou ports exposés.

**Sortie :** tests de reproduction initialement rouges/contrôlés sur le SHA de base, inventaire des comportements publics, matrice de risques validée.

### R1 — Sûreté des actions et de l'arrêt (P1)

**C-02, C-05, C-06.** Traiter les transitions de bouton incertaines indépendamment de `error_policy=continue`; arrêter/quarantainer les actions suivantes, marquer `UNKNOWN` quand l'effet est ambigu, ne jamais rejouer. Coordonner l'arrêt global des séquenceurs sans retarder la publication de l'intention d'arrêt HID. Drainer et annuler les actions en file lors de `close()`.

**Sortie :** tests simulés de press/release/hold/drag/click incertains, arrêt global pendant MOVING/WAITING/PAUSED, file pleine et action suspendue; aucun nouveau rapport après arrêt, états terminaux cohérents; 0 reprise automatique ambiguë.

### R2 — Bornes du transport HOGP et du serveur LAN (P1)

**C-01, C-04.** Borner démarrage, lecture, commandes et arrêt du processus HOGP, drainer stderr, gérer réponses partielles et processus mort. Prévoir un chemin de terminaison hors du canal bloqué et signaler explicitement l'incertitude d'un bouton à distance. Borner handshake, corps HTTP, connexions actives et files du serveur LAN sans altérer TLS/HMAC ni la fraîcheur du feedback.

**Sortie :** faux moteurs muets/partiels/stderr saturé et clients LAN lents ne bloquent pas indéfiniment les threads ni l'arrêt; bornes documentées et mesurées; absence de commandes rejouées.

### R3 — Quotas, ressources et déploiement (P1/P2)

**C-03, C-07, C-08.** Admission des captures avant écriture, prise en compte fichiers temporaires/index/orphelins, comportement explicite si suppression refusée. Nettoyage de tous les serveurs à chaque échec d'initialisation et fermeture complète au shutdown. Mise à jour/rollback agent Windows testés sur échecs intermédiaires, en conservant tâches et protections.

**Sortie :** quota dur sous défaillance simulée; aucun fichier non compté ni ressource serveur orpheline; rollback vérifiable sans toucher à la cible réelle.

### R4 — Tests et reproductibilité (P2)

**C-10, C-15.** Séparer tests unitaires/intégration/hardware (opt-in explicite); CI logicielle compatible avec les limites Windows; compiler l'agent C# et analyser PowerShell; améliorer tests comportementaux des protocoles; découvrir SDK/Build Tools de façon contrôlée.

**Sortie :** commande logicielle reproductible sans radio ni session cible, tests de panne intégrés, versions d'outils et résultats publiés.

### R5 — Refactoring minimal et rationalisation (P2/P3)

**C-09, C-11, C-12, C-13, C-14, C-17.** Identifier chemins HOGP actifs/historiques; décider archivage sur preuves. Réduire la duplication de validation des actions sans modifier la compatibilité API. Extraire des responsabilités de `actions.py` uniquement si tests/profil de couplage justifient. Réviser polygones fins; corriger la détection des doublons au moment de l'ajout au catalogue. Pas de fusion immédiate des séquenceurs ni de framework nouveau.

**Sortie :** chaque extraction réduit effectivement la complexité et conserve contrats et performances; suppressions historiques précédées de preuves d'absence d'usage.

### R6 — Documentation, planning et reprise (transversal et final)

**C-16.** Mettre à jour README, architecture, roadmap, planning, reprise et décisions en séparant état courant et archives. Référencer les audits et les résultats réels, sans annoncer comme résolus les P1 avant qualification.

**Sortie :** une seule version courante des statuts, preuves historiques préservées, état de production distinct du SHA GitHub.

## 5. Ordonnancement, effort et gouvernance

| Lot | Dépendances | Effort indicatif | Risque | Décision |
|---|---|---|---|---|
| R0 | Aucune | Faible à moyen | Faible | Préparer avant correctifs |
| R1 | R0 | Moyen | Élevé (sûreté HID) | Prioritaire |
| R2 | R0, coordination avec R1 | Moyen à élevé | Élevé | Prioritaire |
| R3 | R0, interfaces R1/R2 stables | Moyen | Moyen | Avant extension fonctionnelle |
| R4 | R0; enrichissement pendant R1–R3 | Moyen | Faible à moyen | Intégrer au fil de l'eau |
| R5 | R1–R4 qualifiés | Moyen à élevé | Moyen à élevé | Découper en petites PR |
| R6 | Commencer dès maintenant, finaliser après chaque lot | Faible à moyen | Faible | Documentation continue |

Efforts qualitatifs, non chiffrés en jours. Les quatre P1 de Codex (C-01 à C-04) constituent des portes obligatoires avant nouvelle extension fonctionnelle importante.

**Exécution :** une PR par lot cohérent, SHA et preuves, tests simulés, revue indépendante, fusion uniquement sur accord explicite. En cas de découverte d'un défaut plus grave, reclasser et documenter. Aucune fusion de PR #11 implicite.

## 6. Non-régression et conditions de déploiement

- Conserver le contrôle HID passif côté cible, l'appairage, le descripteur HOGP actuel, TLS/HMAC, DPAPI, journaux, identifiants réservés et politique de non-rejeu.
- Tester les corrections en simulation avant toute qualification Windows.
- **Aucun HID réel, aucune capture réelle ni accès à la cible sans autorisation explicite et surface de test sûre.**
- Séparer qualification du code, fusion GitHub, synchronisation du clone mini-PC et activation des processus : quatre états distincts.
- Documenter les issues `UNKNOWN`, la libération non confirmée des boutons, les limites de latence et les erreurs persistantes.
- Après R1–R3, décider explicitement si une qualification matérielle limitée est nécessaire ; ne pas la présumer.

## 7. Décisions et suivi

1. Conserver les deux audits indépendants sans réécriture.
2. Utiliser cette matrice consolidée comme base du planning correctif.
3. Ne pas fusionner la PR #11 sans décision dédiée.
4. Ne pas modifier la production pendant la phase documentaire.
5. Ne pas revendiquer un `PASS` opérationnel global avant correction et qualification des quatre P1.
6. Archiver chaque preuve et mettre à jour roadmap/planning/reprise au moment de chaque validation.

**Verdict de comparaison :** concordance forte sur l'architecture, complémentarité significative des défauts, preuves Codex plus fortes sur la sûreté opérationnelle. **Verdict produit consolidé : MAINTENABLE_WITH_MAJOR_RESERVATIONS.**
