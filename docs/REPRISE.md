# Reprise — Mousse-controler

**État documentaire au 27 novembre 2026.**

## Références

- Base de fusion auditée : `origin/main` après la PR #26, commit de fusion
  `5ed7045823a0d7b8c7c6418ca5586008e35ba2d2`.
- Le commit `e6c426be6daf95c88bd6d27e084cf829bd61156d`, ancien sommet de la PR #26,
  est intégré à cette base.
- Livraison de convergence : `MC-ARCHITECTURE-CONVERGENCE-001`, PR #27 depuis
  `refactor/mc-architecture-convergence-001`.
- PR #11 : audit historique Draft, non fusionnée.

## État opérationnel observé

L'audit initial du 27 novembre a trouvé la tâche `MousseControler-HOGP` sur le
worktree modifié `mc-hid-precision-001`. Ce runtime non reproductible a été
remplacé par une release immuable construite depuis des objets Git, vérifiée
avant lancement et contrôlée sans nouvelle action HID ni capture. Les preuves
de qualification, d'activation et de santé sont publiées dans la PR #27.

Le MSIX HOGP et PositionAgent ne sont pas modifiés par le chantier
d'architecture. Les preuves matérielles de `MC-FINAL-VALIDATION-001` restent
historiques ; aucune nouvelle commande HID ni capture n'est autorisée sans
consentement immédiat distinct.

## Convergence implémentée

- couche `MouseApplicationService` entre protocoles et composants métier ;
- `OperationCoordinator` unique couvrant chaque opération logique ;
- commandes historiques refusées si une action ou séquence possède le HID ;
- position et topologie publiées atomiquement par `PositionStore` ;
- release contrôleur construite depuis les blobs d'un SHA propre, avec
  manifeste et empreintes vérifiés par le gestionnaire et le lanceur ;
- lancement planifié depuis une source mutable refusé.

## Porte de livraison appliquée à la PR #27

1. Vérifier un arbre Git propre sur la branche de convergence.
2. Exécuter `python -B scripts/qualification/qualify.py --profile full-local`.
3. Publier la branche et une PR Draft avec rapport et preuves expurgées.
4. Ne fusionner qu'après décision explicite du propriétaire.
5. Après fusion ou SHA explicitement retenu, préparer une release immuable avec
   `scripts/runtime/controller_release.py prepare`.
6. Sauvegarder tâche, configuration, journal + `.ids` et index + captures ;
   vérifier la release et le rollback avant de repointer la tâche.
7. Contrôler processus, API/WebSocket, authentification, feedback frais,
   `subscribed=True`, `buttons=0` et absence d'action active, sans HID/capture.

La sauvegarde opérationnelle créée avant migration doit être conservée comme
point de retour historique ; la release active doit toujours provenir d'un SHA
propre et vérifié.
