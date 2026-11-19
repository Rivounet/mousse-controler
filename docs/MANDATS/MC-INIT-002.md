# Mandat Codex Desktop — MC-INIT-002

**Objet : qualifier et commencer à outiller le canal de synchronisation/déploiement distant, sans HID.**
**Jalon : J1 ; puis préparation J4.**
**Statut : exécuté ; [revue indépendante](../REVUES/MC-INIT-002.md) PASS_WITH_RESERVATIONS ; [PR #2](https://github.com/Rivounet/mousse-controler/pull/2) Draft, non fusionnée. La qualification du témoin a été autorisée lors de l'exécution ; cette autorisation n'est pas étendue aux mandats futurs.**

## Prérequis

- Lire `AGENTS.md`, `docs/REPRISE.md`, `docs/ROADMAP.md`, `docs/PLANNING.md`, `docs/ACCES-DISTANT-ET-SYNCHRONISATION.md` et la [revue MC-INIT-001](../REVUES/MC-INIT-001.md).
- [PR #1](https://github.com/Rivounet/mousse-controler/pull/1) : preuves MC-INIT-001 examinées, publication acceptable, **PR encore Draft non fusionnée**. Ne pas intégrer son contenu par inadvertance dans une autre branche ou demander sa fusion sans décision explicite.
- Contrôler `git status`, `main`, `origin/main`, branches et SHA avant toute opération. Préserver les originaux et les travaux non publiés.
- Accès SSH/SFTP existant vers **mini-pc-backend** ; shell distant par défaut `cmd.exe`, PowerShell 5.1 utilisable explicitement ; l'identité d'hôte déjà approuvée doit rester vérifiée.
- Ne pas confondre le rôle BLE périphérique déclaré favorable avec une capacité HID démontrée.

## Phase A — conception et vérifications non destructives (autorisées par le mandat)

1. Vérifier les prérequis du canal SSH (identité hôte, non-interactivité, codes retour et délais, outils présents, règles d'encodage et d'échappement des commandes Windows) **en lecture seule**.
2. Documenter l'emplacement de projet **proposé**, sans créer encore de dossier distant : racine dédiée, `staging/`, `releases/`, `logs/`, `state/`, éventuelle copie Git `source/`. Le dossier de travail et les artefacts exécutables doivent être séparés.
3. Proposer une stratégie de droits minimaux : l'accès SSH courant est administrateur ; éviter de banaliser l'exécution privilégiée et de toucher aux ACL existantes.
4. Spécifier le protocole de test minimal : fichier témoin unique à contenu connu, upload SFTP, téléchargement, vérification SHA-256 des deux côtés, effacement exclusivement du témoin après double contrôle d'identité/chemin, vérification de l'absence d'altération de dossiers non liés.
5. Préparer l'interface des scripts `doctor`, `sync --dry-run`, `status`, `test`, `logs`, `stop` et, plus tard, `deploy`/`rollback`, sans affirmer les opérations non testées comme fonctionnelles.
6. Prévoir tests automatisés locaux (mock de SSH/SFTP), gestion des codes d'erreur, timeouts, versions SHA, refus des chemins hors racine, anti-concurrence, idempotence et protection des secrets.

**Point d'arrêt obligatoire :** avant la première création de fichier/répertoire, upload, suppression ou lancement de processus sur mini-pc-backend, présenter la liste exacte des chemins et commandes, la méthode de nettoyage et les risques à l'utilisateur. **Aucune écriture distante sans son accord explicite.**

## Phase B — qualification réversible, seulement après autorisation explicite

1. Créer uniquement la racine/répertoire témoin expressément approuvé et contrôler ses ACL effectives ; ne pas modifier celles de dossiers existants.
2. Effectuer un upload puis download SFTP du fichier témoin, avec comparaison SHA-256 et journal de l'opération. Supprimer **uniquement le témoin créé par ce mandat** après validation ; ne jamais faire de nettoyage récursif général.
3. Vérifier lancement, code de retour, collecte de stdout/stderr et arrêt d'un processus **de test inoffensif, sans Bluetooth, sans service persistant**, selon le périmètre autorisé.
4. Tester rejouabilité sans doublon, cas d'échec non destructifs (fichier manquant, refus d'accès simulé, mauvais hash, timeout simulé). Ne pas interrompre un service ou une session existante.
5. Produire une qualification claire : PASS / FAIL / NON_EXÉCUTÉ par cas, SHA, sorties expurgées et limites.

## Git et livrables

- Choisir une branche dédiée `feat/mc-init-002-remote-qualification` à partir de `main` vérifié. Aucune modification de `main` par Codex, aucun force-push ni rebase destructif.
- Les scripts de contrôle local et distants sont versionnés dans un répertoire adapté (par exemple `scripts/remote/`). Pas d'installation d'agent/service Windows supplémentaire sans décision.
- Publier un rapport et des preuves **expurgées** dans `qualification/MC-INIT-002/`, avec manifeste. Publier la branche dans une PR **Draft** ; aucune fusion.
- Ne pas publier de compte, chemins personnels, adresse IP privée, empreinte SSH, jeton ou clé privée ; les preuves complètes restent sur les machines.

## Livrable de revue

Présenter : PR URL, SHA tête/base, fichiers modifiés, contrat du canal distant, commandes réellement exécutées, résultats et erreurs, état final du mini-PC, preuves d'absence d'impact hors périmètre, limites et rollback/suppression du témoin.

**Critère de sortie J1 :** SSH confirmé, identité et droits qualifiés, aller-retour SFTP avec SHA-256, absence de modification non liée, collecte de résultats et comportement réversible démontrés. La robustesse complète `deploy`/`rollback` reste un objectif de J4, non implicite.

**Interdits :** aucun appairage, événement HID, ouverture réseau, installation persistante, changement de pare-feu/SSH/PowerShell, modification de service existant ni déploiement applicatif de production.
