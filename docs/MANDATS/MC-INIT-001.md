# Mandat Codex Desktop — MC-INIT-001

**Phase :** démarrage *from scratch* — qualification initiale J1.
**Dépôt :** https://github.com/Rivounet/mousse-controler
**Statut :** exécuté selon le rapport ; [revue](../REVUES/MC-INIT-001.md) PASS_WITH_RESERVATIONS ; preuves sélectionnées dans la [PR #1 Draft](https://github.com/Rivounet/mousse-controler/pull/1), non fusionnée.
**Type :** investigation non destructive, préparation du développement, sans code applicatif.

## Contexte et rôle

Développer localement sur le PC Windows avec Codex Desktop ; exécuter ultérieurement le projet sur `mini-pc-backend` qui doit émettre des commandes Bluetooth HID à destination de ce même PC Windows. Le PC cible n'installe aucun agent récepteur. Lire `README.md`, `AGENTS.md`, `docs/REPRISE.md`, `docs/ROADMAP.md`, `docs/PLANNING.md`, `docs/ARCHITECTURE.md` et `docs/ACCES-DISTANT-ET-SYNCHRONISATION.md`.

## Mission

### A. Dépôt Git et initialisation locale

- Vérifier répertoire local et existence éventuelle d'un clone ; cloner dans un répertoire dédié **uniquement si nécessaire**, sans écraser d'existant.
- Vérifier `origin`, `main`, SHA distant/local, statut de travail, branches et modifications préexistantes.
- Rendre le projet consultable localement. Ne pas créer de branche, de PR ou de commit sans changement justifié.

### B. Inventaire local Windows

- Documenter Windows, architecture, versions Git/PowerShell/outils de développement, réseau et adaptateur Bluetooth côté PC cible.
- Identifier les outils déjà disponibles pour contacter le mini-PC ; ne pas modifier de configuration.

### C. Inventaire distant mini-pc-backend

- Chercher un canal d'accès **déjà autorisé**, sans présumer de SSH/WinRM.
- S'il existe, vérifier en lecture seule OS, CPU/RAM, stockage, réseau, pile et contrôleur Bluetooth, versions Git/outils, services existants, droits et répertoires de déploiement possibles.
- Rechercher les indices de support du rôle BLE périphérique, serveur GATT et HID ; **ne pas confondre indices et démonstration réelle**.
- Si l'accès n'est pas possible, décrire le blocage, les prérequis et les options, sans forcer l'accès.

### D. Proposition de système de synchronisation et déploiement

- Comparer les transports sûrs compatibles avec les environnements observés.
- Proposer une procédure versionnée de connexion, synchronisation par SHA, séparation clone Git/releases, déploiement test, état, journaux, tests distants, arrêt et retour arrière.
- Préciser gestion des secrets, préconditions, idempotence, verrou, santé, interruption réseau et plan de restauration.
- **Ne pas installer/configurer un service, ouvrir un port, ni écrire les scripts complets de déploiement à ce stade.**

### E. Pré-étude HID

- Identifier les bibliothèques/piles plausibles au vu des systèmes et contrôleurs réellement observés.
- Consigner les incompatibilités, dépendances et tests de faisabilité ultérieurs.
- Ne pas réaliser d'appairage ni de mouvement/clic HID durant ce mandat.

## Limites Git et sécurité

Pas de reset/clean destructif, force-push, écrasement de travail, fusion, modification de `main`, ni modifications système non approuvées. Aucun secret dans rapport ou Git. Les documents officiels relèvent de ChatGPT : transmettre les propositions de correction plutôt que les modifier.

## Suivi et livrable

Annoncer le périmètre et les risques ; fournir des points d'étape à la fin de A, B, C et D, avec temps écoulé et blocages.

Remettre **un rapport de qualification** indiquant : dépôt et SHA vérifiés, état Git local, inventaires local/distant, moyens d'accès et limitations, matériel/compatibilité Bluetooth connus vs inconnus, options de synchronisation/déploiement, stratégie de sécurité/rollback, commandes exécutées, résultats et recommandations pour le prochain mandat.

**Fin de mandat :** rapport soumis à ChatGPT pour revue indépendante. Ne pas démarrer automatiquement le prototype ou l'installation de services.
