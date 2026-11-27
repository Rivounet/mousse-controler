# Reprise — Mousse-controler

**État documentaire au 27 novembre 2026.**

## Références

- Référence locale `origin/main` :
  `ff94a765da0a6f0f01276366662eed180e8fad61`.
- Dernier socle fonctionnel observé : branche PR #26 au commit
  `e6c426be6daf95c88bd6d27e084cf829bd61156d`, quatre commits devant cette
  référence locale.
- Chantier courant : `MC-ARCHITECTURE-CONVERGENCE-001` sur
  `refactor/mc-architecture-convergence-001`.
- PR #11 : audit historique Draft, non fusionnée.

## État opérationnel observé

La tâche `MousseControler-HOGP` était active le 27 novembre et pointait vers le
worktree `mc-hid-precision-001`. Quatre fichiers suivis avaient été modifiés
avant le lancement du processus. Le runtime est donc fonctionnellement observé
mais non reconstructible à partir du seul SHA et ne doit pas être présenté
comme une release qualifiée.

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

## Porte de livraison

1. Vérifier un arbre Git propre sur la branche de convergence.
2. Exécuter `python -B scripts/qualification/qualify.py --profile full-local`.
3. Publier la branche et une PR Draft avec rapport et preuves expurgées.
4. Ne fusionner qu'après décision explicite.
5. Après fusion ou SHA explicitement retenu, préparer une release immuable avec
   `scripts/runtime/controller_release.py prepare`.
6. Sauvegarder tâche, configuration, journal + `.ids` et index + captures ;
   vérifier la release et le rollback avant de repointer la tâche.
7. Contrôler processus, API/WebSocket, authentification, feedback frais,
   `subscribed=True`, `buttons=0` et absence d'action active, sans HID/capture.

Le worktree actif ne doit être ni nettoyé ni écrasé : il constitue le point de
retour historique jusqu'à une activation séparément autorisée et vérifiée.
