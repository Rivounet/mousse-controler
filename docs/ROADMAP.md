# Roadmap — Mousse-controler

## État au 21 novembre 2026 — validation finale

- Robustesse R0–R5 intégrée ; R6 documentaire consolidé.
- PR #22–#24 fusionnées : préparation opérationnelle, signature MSIX v2 et procédures Codex qualifiées. `main` de référence : `e5553f2ff3342b16546128e4a351b57f2e2801dc`.
- Qualification locale Windows `full-local` : 286/286 PASS sur le SHA logiciel final de la PR #24, selon Codex. Sept diagnostics matériels exclus.
- La mise en service non matérielle est attestée par `OPERATIONAL_PASS` dans la
  PR #26. Le contrôleur corrigé a ensuite été déployé de façon réversible et la
  validation matérielle complète a été exécutée avec consentement immédiat.

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

## Après mise en service

Les sujets C-09/C-11/C-12/C-17 restent différés ; aucune extension produit automatique. GitHub Actions et CI externe restent exclus ; tests locaux Windows et preuves versionnées. La PR #11 reste indépendante et non fusionnée.
