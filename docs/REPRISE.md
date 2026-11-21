# Reprise — Mousse-controler

**État documentaire au 21 novembre 2026.**

## Référence GitHub et livraison

- `main` vérifié après fusion de la PR #24 : `e5553f2ff3342b16546128e4a351b57f2e2801dc`.
- PR #22, #23 et #24 : fusionnées. PR #11 : audit historique Draft, non fusionnée.
- Environnement Codex : `ENVIRONMENT_READY`, dernier SHA qualifié avant fusion `87da81c6e000262d5f72676f44acbe7e8ea0c36f`, `full-local` 286/286 PASS selon Codex ; sept diagnostics matériels exclus.
- SSH hors sandbox exact et inspection des tâches qualifiés ; voir `scripts/operations/README.md`.
- MSIX HOGP 1.0.0.3 signé en staging avec certificat v2 protégé ; **nouvelle confiance et installation non encore prouvées**. PositionAgent construit, pas de preuve de mise à jour opérationnelle après la PR #24.

## Autorisation utilisateur

Le 21 novembre 2026, l'utilisateur a autorisé l'installation contrôlée du certificat public MSIX v2 vérifié, du package signé, la mise à jour PositionAgent, la synchronisation du contrôleur, la migration des tâches/configurations Mousse-controler, l'activation progressive et les contrôles de santé/communication sur `mini-pc-backend` et `MonOrdinateur`. Sauvegarde et rollback obligatoires. **Aucun HID réel, mouvement de souris ni capture sans consentement distinct au moment des essais.** Defender, Smart App Control et les protections générales Windows restent inchangés. Aucune fusion de nouvelle PR implicite.

## État opérationnel observé avant déploiement

- Tâche contrôleur mini-PC : `Ready`, dernier résultat `1`, aucun processus ni port de commande actif lors de la preuve Codex.
- PositionAgent distant : tâche `Running`, processus en session 2, binaire historique vérifié par SHA ; **pas encore la preuve du nouveau binaire installé**.
- Journal, registre anti-rejeu `.ids` et index captures retrouvés et sauvegardés ; configurations DPAPI préservées.
- Nouveau certificat public non encore approuvé et MSIX 1.0.0.3 non encore installé au moment des preuves.
- Aucune preuve de fonctionnement bout en bout sur les nouvelles versions ; verdict **DEPLOYMENT_AUTHORIZED_NOT_YET_VERIFIED**.

## Reprise et critères de clôture

1. Lire `AGENTS.md`, `scripts/operations/README.md`, `docs/DEPLOIEMENT.md` et les preuves `qualification/MC-CODEX-ENVIRONMENT-001/`.
2. Contrôler l'état Git, les tâches et processus dans leurs contextes autorisés ; sauvegarder à nouveau les persistances et installations avant mutation.
3. Vérifier la signature et la confiance du certificat public v2, installer MSIX, actualiser PositionAgent et le contrôleur, puis activer progressivement selon le mandat autorisé.
4. Vérifier les SHA **réellement chargés**, l'état des deux tâches, les sessions, l'API/WebSocket, l'authentification, la communication et le rollback sans action HID/capture.
5. Produire `OPERATIONAL_PASS` uniquement avec preuves sur les versions actives ; signaler explicitement `MATERIAL_QUALIFICATION_PENDING`. En cas de panne, restaurer ou marquer `RECOVERY_REQUIRED`.

Les rapports historiques restent valables dans leur périmètre ; les qualifications R1–R5 n'ont pas été refaites sur matériel. Ne pas inférer un déploiement de la fusion GitHub.
