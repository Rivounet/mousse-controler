# Revue MC-INIT-001 — 19 novembre 2026

**Verdict : PASS_WITH_RESERVATIONS sur le rapport transmis ; vérification indépendante des fichiers de preuves non réalisée.**
**J1 : partiellement qualifié, non validé.**

## Périmètre et source

Source examinée : `MC-INIT-001-RAPPORT.txt`, fourni dans la conversation ChatGPT le 19 novembre 2026, 140 lignes. Les preuves annoncées par Codex (inventaires, scripts diagnostics, captures WinRT, vérifications SSH/SFTP, état Git) **ne sont pas jointes** à cette revue ; les résultats ci-dessous sont des constats rapportés, pas une réexécution indépendante.

## Constats du rapport

- Clone local créé sous `C:\Projets\Mousse-controler\repository`, état propre et `git fsck` sans erreur affichée ; pas de push, branche, commit ou PR Codex.
- `main` local conservé à `84dbade9fe74ed8c38f4aa1b089a44c194dfa288`, `origin/main` récupéré à `1527797a555b97ae2bced2b1864f1a010422cb9a`. **Ne pas considérer le checkout local comme à jour** ; revérifier l'état Git avant un fast-forward.
- PC développement/cible : Windows 11 Famille x64, Ryzen 5 5500U, ~7,38 Gio RAM utilisable, ~19,53 Gio libres sur C:, contrôleur Bluetooth Realtek.
- mini-pc-backend : Windows 11 Pro x64, Celeron N5105, ~15,85 Gio RAM utilisable, ~337,52 Gio libres sur C:, Bluetooth Realtek.
- SSH par clé, exécution non interactive, sortie distante et consultation SFTP **déclarés fonctionnels** ; `cmd.exe` est le shell SSH par défaut, PowerShell 5.1 fonctionne explicitement.
- Les deux contrôleurs renvoient `true` pour le rôle périphérique BLE WinRT. **Aucun serveur GATT, appairage ni rapport HID n'a été testé.**
- Services et sessions préexistants préservés ; aucune installation ni reconfiguration distante déclarée.

## Réserves et risques

1. **Preuves non relues** : joindre les fichiers de diagnostic pertinents (expurgés des métadonnées sensibles) pour confirmer les résultats et lever la réserve de traçabilité.
2. **J1 incomplet** : transfert SFTP aller-retour, empreintes, répertoire dédié et droits d'écriture, arrêt d'un processus test, reprise et rollback non exécutés.
3. **Privilèges** : la session SSH distante est administrateur ; préférer les droits minimaux pour le déploiement courant.
4. **Contexte Windows** : PowerShell 5.1 distant, `cmd.exe` par défaut ; gestion des chemins, encodage UTF-8 et erreurs à qualifier.
5. **Bluetooth** : `IsPeripheralRoleSupported=true` ne prouve pas la publication d'un service HOGP ni la reconnaissance d'une souris Windows.
6. **Persistance** : aucune preuve qu'un processus BLE WinRT lancé via SSH survive à la déconnexion ou dispose du contexte de session nécessaire.
7. **Sécurité des preuves** : conserver localement les inventaires complets ; ne pas publier publiquement les clés d'hôte, adresses privées, noms de comptes, chemins sensibles ou autres métadonnées non nécessaires.

## Décision et suite

- **MC-INIT-001** : travail de diagnostic déclaré réalisé dans le périmètre ; **PASS_WITH_RESERVATIONS** sur rapport.
- **J1** : non clos. **J2** : non qualifié.
- **Aucune autorisation implicite** d'installer un service, modifier SSH/pare-feu, effectuer un appairage Bluetooth, créer une API ou fusionner une PR.
- Préparer **MC-INIT-002** après examen des preuves : tester sur une racine dédiée explicitement autorisée un fichier témoin, transfert aller-retour avec SHA-256, nettoyage borné, codes d'erreur, exécution et arrêt d'un processus sans HID, récupération des logs, idempotence et comportements en échec. Conserver les changements techniques en branche/PR Draft et préserver `main`.
- Mettre à jour cette revue si les preuves sont reçues ; séparer alors les résultats vérifiés des déclarations du rapport.
