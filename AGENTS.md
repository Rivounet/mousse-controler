# Instructions de travail — Codex Desktop

Ces consignes s'appliquent à toute intervention dans `Rivounet/mousse-controler`.

## Rôle et lieux

- **Développer en local** sur le PC Windows avec Codex Desktop.
- **Déployer et exécuter les tests matériels** sur `mini-pc-backend` via un canal distant qualifié et des scripts versionnés, **pas via des manipulations manuelles non reproductibles**.
- Le PC Windows de développement est aussi la **cible Bluetooth HID**. Aucun agent récepteur spécifique au projet ne doit y être installé.
- **ChatGPT détient la responsabilité de la documentation de référence et des revues de code**. Proposer les corrections documentaires dans le compte rendu ; ne pas déclarer de jalon validé sans revue.

## Pour chaque mandat

1. Lire `docs/REPRISE.md` (état et mandat courant), puis `README.md`, `docs/ROADMAP.md`, `docs/PLANNING.md`, `docs/ARCHITECTURE.md` et les documents concernés.
2. Vérifier branche, état Git et fichiers préexistants. Ne jamais écraser des changements non liés.
3. Annoncer objectif, périmètre, risques et critères de réussite avant les modifications.
4. Faire une modification ciblée et testable. Utiliser une branche de travail et une PR pour les changements applicatifs ; ne pas pousser de code directement sur `main`.
5. Distinguer tests locaux, déploiement de test et **preuves matérielles sur le mini-PC**.
6. Fournir les résultats, commandes, SHA, fichiers modifiés, échecs, réserves et instructions de rollback.
7. Soumettre le diff et les preuves à ChatGPT pour revue indépendante ; **ne pas fusionner sans arbitrage explicite**.

## Sécurité / opérations

- Diagnostic initial **en lecture seule**. Aucun accès distant, port, outil ni droit administrateur n'est présumé disponible.
- Ne pas installer de service persistant, modifier le pare-feu, reconfigurer Bluetooth ou toucher à un service existant sans autorisation pertinente.
- Ne jamais publier de secrets ou d'identifiants, y compris dans les logs.
- L'API doit rester protégée ; éviter toute exposition réseau non justifiée.
- Ne pas émettre de clics/mouvements Bluetooth sans session de test autorisée et mécanisme d'arrêt effectif.
- Préserver la possibilité de retour arrière sur mini-PC. Ne pas faire de `git reset --hard`, `git clean -fdx`, `git pull` aveugle ni écraser des modifications inconnues dans la copie distante.
- Avant tout déploiement, vérifier identité de l'hôte, SHA exact, état de la copie Git distante, permissions, espace disque et disponibilité du rollback ; après déploiement, relever le SHA réellement actif.
- Implémenter un mode `--dry-run`, des vérifications préalables, un verrou anti-déploiements concurrents, un contrôle de santé, une collecte de logs et un rollback sécurisé ; tester l'idempotence et les erreurs.
- Indiquer l'état d'avancement et le temps écoulé aux étapes clés d'un travail long ; signaler les blocages.

## Principes de conception

Privilégier les composants indépendants : réception API, validation/ordonnancement, adaptateur HID. Préférer un adaptateur simulé pour les tests unitaires. Ne pas supposer que Bluetooth Windows peut fonctionner comme périphérique HID tant que J2 ne l'a pas démontré. Éviter frameworks, services et abstractions non nécessaires au MVP.

## Sources de vérité

- Roadmap : `docs/ROADMAP.md`
- Tâches et états : `docs/PLANNING.md`
- Architecture : `docs/ARCHITECTURE.md`
- Déploiement : `docs/DEPLOIEMENT.md`
- Accès distant et synchronisation : `docs/ACCES-DISTANT-ET-SYNCHRONISATION.md`
- Tests / revue : `docs/TESTS.md`
- Décisions : `docs/DECISIONS.md`
- Reprise : `docs/REPRISE.md`
- Mandat initial : `docs/MANDATS/MC-INIT-001.md`

## Mandats, revue et GitHub

- **ChatGPT fournit les mandats Codex** avec objectifs, périmètre autorisé, critères de validation, risques et format des preuves.
- **ChatGPT supervise Git/GitHub** : état de `main`, branches, PR, SHA, changements préexistants, cohérence local/distant et absence de fusion implicite.
- Codex exécute le mandat dans le périmètre autorisé et publie une PR **Draft** pour les changements applicatifs, sans fusion ; il fournit à ChatGPT les traces de validation.
- Démarrage *from scratch* : commencer par vérifier le clone Git local et les environnements ; ne pas supposer que le mini-PC ou une connexion distante sont prêts.
- Aucun `push --force`, rebase destructif, nettoyage irréversible, reset de travail non committé, modification de `main` ni fusion sans mandat explicite.

## Publication obligatoire des livrables de revue

- **Codex publie sur GitHub les rapports et preuves utiles de chaque mandat**, dans une branche dédiée et une PR Draft, afin que ChatGPT les consulte directement sans transfert manuel par l'utilisateur.
- Convention : `qualification/<MANDAT>/RAPPORT.md` et `qualification/<MANDAT>/evidence/` pour les preuves sélectionnées, reproductibles et expurgées. Les scripts utiles au produit restent dans leurs dossiers techniques appropriés.
- Avant toute publication, examiner les fichiers et **exclure** secrets, clés, empreintes d'hôte non nécessaires, comptes, chemins privés, adresses réseau privées, journaux sensibles et artefacts volumineux ou binaires inutiles. Conserver localement les preuves brutes non publiables et indiquer leur existence, sans exposer leur contenu.
- Rapporter l'URL de PR, la branche, le SHA publié et la liste des preuves, en distinguant résultats vérifiés, déclarés et non exécutés. Ne jamais pousser directement sur `main` ni fusionner sans arbitrage.
- Si la publication est bloquée, documenter la cause et demander une décision ; **ne pas imposer à l'utilisateur un transfert manuel de fichiers comme procédure normale**.
