# Roadmap — Mousse-controler

## État au 27 novembre 2026 — convergence architecturale

- Robustesse R0–R5 intégrée ; R6 documentaire consolidé.
- PR #22–#24 fusionnées : préparation opérationnelle, signature MSIX v2 et procédures Codex qualifiées. `main` de référence : `e5553f2ff3342b16546128e4a351b57f2e2801dc`.
- Qualification locale Windows `full-local` : 286/286 PASS sur le SHA logiciel final de la PR #24, selon Codex. Sept diagnostics matériels exclus.
- La mise en service non matérielle est attestée par `OPERATIONAL_PASS` dans la
  PR #26. Le contrôleur corrigé a ensuite été déployé de façon réversible et la
  validation matérielle complète a été exécutée avec consentement immédiat.
- Un audit ultérieur a constaté que la tâche active chargeait un worktree
  modifié, en dehors du modèle de releases documenté. Cette observation ne
  retire pas les preuves historiques, mais interdit de qualifier le runtime
  actuel par son seul HEAD Git.

## Validation opérationnelle réalisée

1. MSIX 1.0.0.3 signé et PositionAgent qualifié conservés ; contrôleur de la
   PR #26 activé avec sauvegarde préalable et rollback vers `fc88e330…`.
2. API authentifiée, WebSocket, télémétrie, persistance et anti-rejeu vérifiés.
3. Actions souris, déplacements confirmés, capture privée, arrêt d'urgence et
   redémarrage contrôlé vérifiés sur les deux machines.
4. Le rapport consolidé est
   [MC-FINAL-VALIDATION-001](../qualification/MC-FINAL-VALIDATION-001/RAPPORT.md).

## Précision HID — PR #26

Le scénario matériel initial conserve son verdict historique `MATERIAL_FAIL` : un rapport
relatif de 10 unités HID a produit 9 pixels écran. La priorité est de publier et
qualifier logiciellement la boucle fermée. La validation finale démontre ensuite
que `move_relative_confirmed` atteint exactement ses cibles et retourne au point
initial ; elle ne réinterprète pas l'unité HID brute comme un pixel.

## Convergence en cours

1. Encapsuler les protocoles dans des adaptateurs et centraliser les cas
   d'usage dans un service applicatif.
2. Attribuer le HID par un coordinateur exclusif commun aux actions, séquences
   et commandes historiques.
3. Publier position et topologie atomiquement.
4. Préparer le contrôleur depuis un SHA propre dans une release immuable,
   vérifier les empreintes au démarrage et interdire les worktrees aux tâches.
5. Qualifier `full-local`, publier une PR Draft, puis décider séparément de la
   fusion et de l'activation avec rollback.

## Après convergence

C-09 et C-17 restent différés ; C-12 ne justifie pas une décomposition plus
fine sans mesure. Aucune extension produit automatique. GitHub Actions et CI
externe restent exclus ; tests locaux Windows et preuves versionnées. La PR #11
reste indépendante et non fusionnée.
