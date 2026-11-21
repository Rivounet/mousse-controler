# Roadmap — Mousse-controler

## État au 21 novembre 2026

- Robustesse R0–R5 intégrée ; R6 documentaire consolidé.
- PR #22–#24 fusionnées : préparation opérationnelle, signature MSIX v2 et procédures Codex qualifiées. `main` de référence : `e5553f2ff3342b16546128e4a351b57f2e2801dc`.
- Qualification locale Windows `full-local` : 286/286 PASS sur le SHA logiciel final de la PR #24, selon Codex. Sept diagnostics matériels exclus.
- La mise en service sur les deux machines est **autorisée mais non encore attestée** ; ne pas la déclarer achevée sur la seule base du dépôt.

## Priorité immédiate — mise en service opérationnelle

1. Préflight et sauvegarde des états réels des deux machines.
2. Confiance limitée du certificat public MSIX v2 vérifié et installation du MSIX 1.0.0.3 signé.
3. Mise à jour transactionnelle de PositionAgent, synchronisation du contrôleur, configuration et tâches Mousse-controler.
4. Activation progressive et qualification de santé/API/WebSocket/communication **sans HID ni capture** ; preuve des SHA réellement actifs.
5. Verdict `OPERATIONAL_PASS` seulement si les contrôles autorisés sont réellement réussis ; sinon `PARTIAL` ou `ROLLBACK_REQUIRED`.
6. Qualification matérielle distincte après consentement explicite, avec arrêt d'urgence, mouvements HID et captures uniquement dans ce cadre.

## Précision HID — PR #26

Le scénario matériel initial conserve son verdict `MATERIAL_FAIL` : un rapport
relatif de 10 unités HID a produit 9 pixels écran. La priorité est de publier et
qualifier logiciellement la boucle fermée, puis seulement sur autorisation
distincte de la déployer et d'exécuter un aller/retour minimal sans clic,
défilement ni capture supplémentaire.

## Après mise en service

Les sujets C-09/C-11/C-12/C-17 restent différés ; aucune extension produit automatique. GitHub Actions et CI externe restent exclus ; tests locaux Windows et preuves versionnées. La PR #11 reste indépendante et non fusionnée.
