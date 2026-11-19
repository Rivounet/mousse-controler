# Accès distant, synchronisation et déploiement — contrat cible

**Statut : spécification à qualifier en J1 ; aucun outil distant n'est présumé installé ni fonctionnel.**

## Objectif

Depuis **Codex Desktop sur le PC Windows**, disposer d'un moyen **stable, sécurisé, contrôlable et automatisable** pour :
- accéder à l'espace de travail du projet sur **mini-pc-backend** ;
- synchroniser une version Git identifiée du projet ;
- déployer et démarrer cette version sur le mini-PC ;
- exécuter les tests et récupérer les preuves, journaux et erreurs ;
- connaître exactement la version active et **revenir à la précédente**.

La cible Windows du Bluetooth HID ne reçoit **aucun agent applicatif** pour la souris. Le canal de maintenance distant concerne **mini-pc-backend uniquement**.

## Source de vérité et copies de travail

- **GitHub (`Rivounet/mousse-controler`)** : référence versionnée officielle.
- **PC Windows de développement** : clone principal utilisé par Codex, branches de travail et commits.
- **mini-pc-backend** : clone/miroir de travail pour les opérations Git si utile, **distinct des dossiers d'exécution**, et versions déployées isolées.

Le mini-PC ne devient pas un second dépôt faisant autorité : ne pas traiter son clone comme une branche principale concurrente. Aucun `git reset --hard`, `git clean -fdx`, `git pull` aveugle, écrasement de fichiers modifiés ou publication implicite vers GitHub. En cas de modifications non attendues sur le mini-PC, **arrêt et diagnostic avant toute synchronisation**.

## Choix du transport (à décider après inventaire)

1. Identifier OS et version du mini-PC, services déjà disponibles, authentification, réseau, droits, stockage, Git, outils de copie et de supervision.
2. Comparer une connexion chiffrée et authentifiée appropriée : **OpenSSH/SFTP** si disponible et compatible ; **PowerShell Remoting / WinRM** seulement si justifié et sécurisé ; autres options uniquement si nécessaires.
3. Établir l'identité réelle de l'hôte, restreindre le compte et les chemins accessibles, utiliser des secrets hors Git, limiter l'exposition au réseau de confiance.
4. N'installer ni serveur, ni service persistant, ni règle de pare-feu sans décision explicite.
5. Prouver la connexion, lecture de métadonnées, transfert réversible, commande non destructive et collecte de sortie avant autoriser un déploiement.

**Ne pas choisir le transport ou des chemins système avant le diagnostic J1.** L'accès réseau et les privilèges sont des prérequis à démontrer, pas des hypothèses.

## Structure logique sur mini-pc-backend

Les chemins réels seront choisis après inventaire :

```text
<racine-projet-autorisee>/
    source/       # clone Git de référence (éventuel)
    releases/     # versions immuables, identifiées par SHA
    active/       # référence/manifest de la version lancée
    logs/         # logs déploiement et exécution, secrets masqués
    state/        # état de déploiement, verrous, métadonnées
```

Les dossiers d'exécution sont séparés de la copie Git. Si les conditions d'OS ne permettent pas une activation atomique par lien ou renommage, utiliser une procédure d'arrêt + remplacement contrôlé + reprise, avec retour arrière explicite.

## Interface logique des scripts (noms indicatifs)

Un jeu de scripts dans `scripts/remote/` sera développé par Codex **après qualification J1**, avec paramètres externes de configuration, sans secrets committés :

| Action | Effet contrôlé |
|---|---|
| `doctor` | Diagnostics en lecture seule (identité, OS, permissions, Git, espace, transport, état) |
| `sync --ref <SHA> --dry-run` | Simuler l'arrivée d'une version vérifiée ; aucune modification |
| `sync --ref <SHA>` | Préparer le code de la révision exacte sans écraser de travail |
| `deploy --ref <SHA> --dry-run` | Montrer les opérations, prérequis et risques sans déployer |
| `deploy --ref <SHA>` | Construire/transférer une version isolée, activer puis vérifier |
| `status` | Version Git et version active, état service, dernier résultat, santé |
| `test` | Lancer les tests explicitement autorisés sur mini-PC, sans événement HID non supervisé |
| `logs` | Rapatrier les traces horodatées et expurgées |
| `rollback` | Rétablir la version précédente connue fonctionnelle |
| `stop` | Arrêt contrôlé de l'application de test et, si présent, de l'émission HID |

Un système où l'artefact est construit localement puis transféré peut être préférable à un `git pull` sur mini-PC. **Le choix final doit néanmoins permettre l'inspection et la synchronisation de la copie distante si celle-ci existe**, et assurer la traçabilité du SHA déployé.

## Exigences de robustesse

- **Préconditions vérifiées** : hôte attendu, dossier autorisé, état Git, version de référence, dépendances, espace disque, droits, état de l'application, secrets requis.
- **Révision exacte** : une opération cible un **SHA immuable**, avec manifeste et empreinte des artefacts ; pas de déploiement fondé sur un nom de branche mouvant.
- **Idempotence** : rejouer la même opération ne doit pas dégrader l'état ou dupliquer un service.
- **Exclusion mutuelle** : interdire deux déploiements ou tests conflictuels simultanés (verrou avec récupération sûre après interruption).
- **Staging** : préparer et vérifier une version avant activation ; préserver la version antérieure jusqu'à qualification.
- **Contrôle post-déploiement** : délai borné, contrôle de processus/port/état API pertinents ; si échec, rollback et verdict FAIL, jamais PASS.
- **Échecs explicites** : perte réseau, version inconnue, état Git sale, manque de droits, espace insuffisant et service indisponible font échouer sans suppression destructive.
- **Traçabilité** : horodatage, identifiant d'opération, SHA demandé, SHA observé sur mini-PC, résultat, commandes résumées, tests, logs, rollback effectué ou non.
- **Sécurité** : clés/tokens hors dépôt, droits minimaux, validation de l'hôte, secrets masqués, aucune API de souris exposée involontairement ; port/pare-feu seulement après autorisation.
- **Réversibilité** : retour arrière testé, et procédure de récupération manuelle si l'accès distant est perdu.

## Qualification obligatoire du système de déploiement

1. Un `doctor` sans effet de bord réussit et identifie l'hôte.
2. Une synchronisation test sur révision exacte est attestée par SHA.
3. Une nouvelle version est activée, ses tests et logs sont rapatriés vers Codex Desktop.
4. Une seconde exécution identique est sans effet indésirable.
5. Des erreurs simulées (connexion coupée, révision absente, dossier non autorisé, état Git sale) échouent sans détruire de données.
6. Un déploiement volontairement défaillant déclenche un rollback observable, ou reste bloqué sans altérer la version active.
7. La version active et la version précédente sont identifiables depuis le PC Windows.

Toute commande modifiant l'environnement réel requiert le périmètre et l'autorisation correspondants. **Aucun script d'accès distant n'est encore implémenté.**

## Responsabilités

- **Codex Desktop** : diagnostic, proposition de transport, implémentation des scripts, exécution des tests sur mini-PC, preuves.
- **ChatGPT** : spécifications documentaires, examen du diff, analyse indépendante des preuves, mise à jour du planning et verdict.
- **Utilisateur** : validation des modifications système (activation d'un serveur distant, pare-feu, droits, permanence) et des choix de périmètre.
