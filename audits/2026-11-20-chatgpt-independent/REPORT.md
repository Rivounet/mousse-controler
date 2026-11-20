# Mousse-controler — Rapport indépendant ChatGPT : audit architectural et qualité du code

**Date :** 20 novembre 2026  
**Auteur :** ChatGPT  
**Référence auditée :** `main` au commit `d19db664bc1e7d83ab1d289f89373f9e327a482b` (fusion PR #10)  
**Statut :** rapport définitif de revue statique ; constats opérationnels non encore qualifiés par injection de panne.  
**Confidentialité méthodologique :** document de comparaison, à ne pas communiquer à Codex avant la remise de son propre audit.  
**Portée de la branche :** stockage isolé, sans PR, sans fusion dans `main`.

## 1. Objet et méthode

Audit hybride : inventaire global du dépôt, revue statique approfondie des composants critiques et revue ciblée des composants historiques. Aucun changement applicatif, test HID réel, capture, déploiement ni synchronisation des machines.

Inventaire GitHub : arbre récursif du commit de référence, 216 entrées (fichiers et dossiers). Fichiers examinés notamment : `app.py`, `controller.py`, `transport.py`, `command_server.py`, `actions.py`, `sequence.py`, `capture.py`, `position_server.py`, `api_catalog.py`, `src/hogp-powershell/hogp.ps1`, `src/hogp/main.cpp`, `src/hogp-launcher/main.cpp`, `src/position-agent/PositionAgent.cs`, scripts Windows de build/déploiement/qualification, et tests associés.

**Limite :** revue statique du code et de la documentation, sans exécution indépendante des 195 tests ni qualification dynamique sur Windows. Les modules secondaires ont été inventoriés mais pas tous relus ligne par ligne. Les conséquences matérielles évoquées sont des risques, pas des incidents démontrés.

## 2. Verdict

**PASS_WITH_RESERVATIONS.** Conserver l'architecture actuelle, améliorer prioritairement les chemins de défaillance et la coordination des arrêts, puis simplifier de manière sélective. Pas de refonte générale recommandée.

Atouts : séparation des deux machines et des canaux Bluetooth/LAN ; `MouseController` isolant les émissions HID ; `PositionAgent` observateur sans injection souris ; `ActionExecutor` avec file, journal et anti-rejeu ; `CaptureBroker` avec quotas, index et suivi des suppressions ; catalogue API déclaratif central ; tests logiciels déjà substantiels. Ne pas confondre tests publiés et validation indépendante.

## 3. Matrice des constats

| ID | Priorité | Observation vérifiable | Qualification / décision |
|---|---|---|---|
| ARCH-01 | P1 | `transport.py` : `_read_result()` appelle `stdout.readline()` sans délai maximal ; `_command()` attend sous verrou ; `stop()` utilise le même canal ; `stderr=PIPE` sans drainage visible. `hogp.ps1` utilise `GetAwaiter().GetResult()` pour les opérations WinRT ; le C++ historique utilise `.get()`. | Risque de blocage ; qualifier par moteur muet et corriger avec délais, supervision et récupération sans rejeu. |
| ARCH-02 | P1 | `command_server.py::_command_stop()` appelle `ActionExecutor.emergency_stop()` (ou directement le contrôleur) mais pas `SequenceRunner.stop()` ; `CommandGateway._sequence` est indépendant. | Coordination d'état incomplète confirmée dans le code ; mesurer l'effet pendant une séquence historique, conserver priorité arrêt HID. |
| ARCH-03 | P2 | `app.py::serve()` crée successivement serveurs HTTPS, HTTP, WebSocket ; le `except` initial ferme actions et contrôleur, sans fermeture explicite des serveurs précédemment créés. Le `finally` normal appelle `shutdown()` sans `server_close()` explicite. | Corriger le cycle de vie des ressources, tester les échecs à chaque étape. |
| ARCH-04 | P2 | `sequence.py::SequenceRunner` et `actions.py::ActionExecutor` gèrent séparément pauses, annulations, attentes et états. | Duplication conceptuelle ; convergence graduelle éventuelle, sans fusion immédiate. |
| ARCH-05 | P2 | `Update-InteractivePositionAgent.ps1` vérifie SHA, sauvegarde et tâche, mais les erreurs après remplacement ne sont pas toutes encadrées par un rollback automatique. | Tester les échecs intermédiaires et fiabiliser la restauration sans modifier protections Windows. |
| ARCH-06 | P2 | Les tests couvrent commandes, arrêt du contrôleur, actions, journal et captures ; absence de scénarios spécifiques identifiés pour HOGP muet, échec partiel des trois serveurs, arrêt d'une séquence historique via `stop`. Certains tests vérifient surtout des chaînes de code. | Ajouter des tests comportementaux d'injection de panne. |
| ARCH-07 | P2 | `docs/REPRISE.md`, `PLANNING.md`, `ROADMAP.md` présentent encore J7/PR #10 en Draft ou à publier après sa fusion ; `README.md` conserve un statut historique contradictoire pour PR #8. | Nettoyage documentaire séparé, conservation des preuves historiques. |
| ARCH-08 | P3 | `actions.py` (~940 lignes) rassemble registre, persistance, événements, exécution et validations métier. | Découpage prudent après stabilisation et tests ; taille seule non fautive. |
| ARCH-09 | P3 | `PositionAgent.cs` (~652 lignes) réunit position, topologie, HTTPS, certificat, captures, reconnexion et cycle de vie. | Simplification facultative, sans modification du rôle passif. |
| ARCH-10 | P3 | Journal JSONL et ledger `.ids` dans `ActionRegistry` ; index atomique JSON dans `CaptureBroker`. Écritures `fsync`/temporaire et récupération ont des similitudes. | Mutualiser uniquement primitives techniques éprouvées, pas les modèles métier. |
| ARCH-11 | P3 | `src/hogp-powershell/hogp.ps1` est inclus dans le MSIX qualifié par `Build-HogpPackage.ps1`; `src/hogp/main.cpp` fournit une autre implémentation HOGP. | Clarifier le statut du C++ historique ; ne pas supprimer sans cartographie des usages. |
| ARCH-12 | P3 | Scripts PowerShell de maintenance/qualification répètent identification de tâches, processus, chemins et attentes bornées. | Petites fonctions communes si gain prouvé ; éviter un framework nouveau. |

## 4. Analyse des points critiques

### ARCH-01 — Transport HOGP

Le blocage est possible avant même la partie de `stop()` qui utilise `process.wait(timeout=5)`, car les appels `release_all()` et `_command("stop")` attendent eux-mêmes des réponses. Le timeout de démarrage stocké dans `NativeHogpTransport` ne borne pas le `readline()` observé. Prévoir supervision du processus, timeout par opération, drainage des flux, arrêt forcé contrôlé et état `UNKNOWN` si l'émission d'une action non idempotente est incertaine. Terminer le processus ne prouve pas le relâchement distant des boutons.

### ARCH-02 — Arrêt global

Le contrôleur publie déjà une intention d'arrêt avant l'attente du verrou et bloque les émissions ultérieures. Le constat ne démontre donc **pas** que la souris continue à bouger après `stop`. Le défaut porte sur la supervision de `SequenceRunner` et la cohérence de ses états. Tester le cas `MOVING`, `WAITING`, `PAUSED` et l'arrêt concurrent avant de corriger.

### ARCH-03 — Initialisation et arrêt

Adopter une fermeture en ordre inverse d'acquisition des ressources, couvrir les exceptions pendant l'initialisation, pendant le lancement des threads et lors de l'arrêt. Éviter qu'une exception de nettoyage empêche les autres fermetures.

### ARCH-04 — Deux séquenceurs

`SequenceRunner` gère zones et trajectoires ; `ActionExecutor` gère séquences d'actions, journal, événements et anti-rejeu. Leurs fonctionnalités ne sont pas interchangeables. Conserver les API publiques ; considérer `ActionExecutor` comme moteur principal à long terme uniquement si une migration progressive prouve la compatibilité.

### ARCH-05 — Rollback

Le script cible vérifie la tâche attendue, SHA-256, sauvegarde et refus d'états ambigus. Les étapes de remplacement, redémarrage et contrôle d'état doivent être éprouvées par simulations d'échecs. Ne pas désactiver Smart App Control/WDAC ni modifier les ACL.

## 5. État de la qualité

**Architecture :** favorable ; frontières Bluetooth/LAN/API à conserver.  
**Lisibilité :** acceptable ; modules longs et responsabilités concentrées à simplifier prudemment.  
**Sécurité :** mécanismes de chiffrement, HMAC, TTL, idempotence et anti-rejeu présents ; la revue n'est pas un audit de sécurité exhaustif.  
**Robustesse :** principale dette, surtout opérations bloquantes et cycle de vie.  
**Tests :** 195/195 PASS rapportés par Codex sur la PR #10, pas réexécutés lors de cet audit ; couverture des défaillances à renforcer.  
**Documentation :** statuts de jalons contradictoires avec GitHub, à corriger.

## 6. Plan proposé

| Lot | Contenu | Risque de régression | Porte de validation |
|---|---|---|---|
| R1 — Robustesse critique | HOGP muet/timeouts/états incertains ; coordination `stop` des deux moteurs | Élevé | Tests simulés, revue indépendante, aucun HID réel sans accord |
| R2 — Cycle de vie | Serveurs, ressources, fermeture, rollback Windows, tests d'injection | Moyen | Tests de panne et restauration, pas de déploiement implicite |
| R3 — Rationalisation | Réduction duplication des séquenceurs, séparation ciblée des responsabilités `actions.py` | Moyen à élevé | Contrats inchangés, non-régressions exhaustives |
| R4 — Documentation et historique | États roadmap/planning/reprise, inventaire HOGP C++ et scripts historiques, nettoyage limité | Faible à moyen | Revue des usages avant suppression |

Ne pas introduire de framework générique, changer de langage, refondre le BLE ou fusionner les modèles de persistance sans bénéfice démontré.

## 7. Tests à ajouter

1. Processus HOGP vivant mais muet, stdout incomplet, stderr saturé, arrêt pendant une commande.
2. `stop` global pendant séquence historique en mouvement, attente et pause.
3. Échec à chaque création de serveur et fermeture de ressources déjà acquises.
4. File d'actions pleine et action suspendue pendant arrêt.
5. Déploiement cible interrompu après remplacement du binaire, puis restauration.
6. Journal d'actions partiel, redémarrage et anti-rejeu ; suppression de capture refusée et état persistant.

Commencer par simulations sans souris réelle.

## 8. Décisions recommandées

Conserver Python comme orchestrateur, l'agent C# passif, le moteur BLE HOGP et le catalogue API central. Conserver les mécanismes de sécurité et les données existantes. Ne pas fusionner immédiatement les deux séquenceurs ni supprimer l'implémentation C++ sans preuves d'inutilité. Corriger d'abord la robustesse, puis simplifier. Aucune nouvelle prise de souris, capture réelle, modification de production ou fusion GitHub sans approbation explicite.

## 9. Conclusion et limites

**Verdict : PASS_WITH_RESERVATIONS.** L'architecture peut continuer à évoluer sans réécriture générale. La priorité est la gestion des défaillances et la coordination des arrêts. Les constats statiques ne démontrent pas d'incident matériel ; les hypothèses d'impact doivent être vérifiées par des tests ciblés.

**Note de méthode pour la contre-expertise :** conserver ce document hors du périmètre communiqué à Codex. Ne comparer les analyses qu'après réception de son rapport complet, en séparant accords, divergences, nouvelles observations, preuves et recommandations.
