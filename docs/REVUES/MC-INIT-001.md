# Revue MC-INIT-001 — 19 novembre 2026

**Verdict final : PASS_WITH_RESERVATIONS pour MC-INIT-001 (qualification initiale), PASS pour la publication des preuves par la PR #1.**
**J1 : partiellement qualifié, non validé.**

## Périmètre et source

Sources : rapport initial fourni dans la conversation, puis [PR #1](https://github.com/Rivounet/mousse-controler/pull/1) au SHA `8886cab1230039add8e2712a5114c4e312c0f49b` : 10 fichiers de rapport, manifeste et preuves expurgées directement consultés dans GitHub. **La lecture des preuves est indépendante de leur production**, sans réexécution des diagnostics sur les machines. Les sorties brutes exclues pour confidentialité restent non auditables depuis GitHub.

## Constats du rapport

- Clone local créé sous `C:\Projets\Mousse-controler\repository`, état propre et `git fsck` sans erreur affichée ; pas de push, branche, commit ou PR Codex.
- `main` local conservé à `84dbade9fe74ed8c38f4aa1b089a44c194dfa288`, `origin/main` récupéré à `1527797a555b97ae2bced2b1864f1a010422cb9a`. **Ne pas considérer le checkout local comme à jour** ; revérifier l'état Git avant un fast-forward.
- PC développement/cible : Windows 11 Famille x64, Ryzen 5 5500U, ~7,38 Gio RAM utilisable, ~19,53 Gio libres sur C:, contrôleur Bluetooth Realtek.
- mini-pc-backend : Windows 11 Pro x64, Celeron N5105, ~15,85 Gio RAM utilisable, ~337,52 Gio libres sur C:, Bluetooth Realtek.
- SSH par clé, exécution non interactive, sortie distante et consultation SFTP **déclarés fonctionnels** ; `cmd.exe` est le shell SSH par défaut, PowerShell 5.1 fonctionne explicitement.
- Les deux contrôleurs renvoient `true` pour le rôle périphérique BLE WinRT. **Aucun serveur GATT, appairage ni rapport HID n'a été testé.**
- Services et sessions préexistants préservés ; aucune installation ni reconfiguration distante déclarée.

## Réserves et risques

1. **Preuves relues dans GitHub** : dix fichiers et leur manifeste inspectés, fichiers JSON analysables, neuf empreintes SHA-256 concordantes après restitution des fins de ligne Windows CRLF lors du contrôle textuel. Les originaux expurgés et les tests matériels n'ont pas été réexécutés ; la confidentialité ne peut pas être certifiée exhaustivement.
2. **J1 incomplet** : transfert SFTP aller-retour, empreintes, répertoire dédié et droits d'écriture, arrêt d'un processus test, reprise et rollback non exécutés.
3. **Privilèges** : la session SSH distante est administrateur ; préférer les droits minimaux pour le déploiement courant.
4. **Contexte Windows** : PowerShell 5.1 distant, `cmd.exe` par défaut ; gestion des chemins, encodage UTF-8 et erreurs à qualifier.
5. **Bluetooth** : `IsPeripheralRoleSupported=true` ne prouve pas la publication d'un service HOGP ni la reconnaissance d'une souris Windows.
6. **Persistance** : aucune preuve qu'un processus BLE WinRT lancé via SSH survive à la déconnexion ou dispose du contexte de session nécessaire.
7. **Sécurité des preuves** : conserver localement les inventaires complets ; ne pas publier publiquement les clés d'hôte, adresses privées, noms de comptes, chemins sensibles ou autres métadonnées non nécessaires.

## Décision et suite

- **MC-INIT-001** : **PASS_WITH_RESERVATIONS** après examen du rapport et des preuves publiées. **MC-INIT-001-PUBLICATION** : **PASS** pour la publication documentaire. La [PR #1](https://github.com/Rivounet/mousse-controler/pull/1) est **Draft**, non fusionnée ; revue COMMENT publiée sur GitHub, sans fusion.
- **J1** : non clos. **J2** : non qualifié.
- **Aucune autorisation implicite** d'installer un service, modifier SSH/pare-feu, effectuer un appairage Bluetooth, créer une API ou fusionner une PR.
- **[MC-INIT-002](../MANDATS/MC-INIT-002.md)** préparé : qualification du canal distant, scripts et transfert témoin sous contrôle. **Point d'arrêt : aucune écriture ni création sur mini-pc-backend sans autorisation explicite de l'utilisateur.** Conserver les changements techniques en branche/PR Draft et préserver `main`.
- Références Git historiques : `main` local en retard après MC-INIT-001, puis fast-forward propre rapporté dans `evidence/git-publication.txt` vers `86ed1088bc1e2ae7984c4c4ccfd0bb0af8755b02`. À l'examen, la base de PR #1 correspond au SHA `86ed1088...`, la tête à `8886cab...`. Ne pas interpréter ces états historiques comme un état local courant.
