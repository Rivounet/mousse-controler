# Revue de code et preuves — MC-INIT-002

**Date :** 19 novembre 2026.
**PR :** [#2 Draft](https://github.com/Rivounet/mousse-controler/pull/2), tête `cf3c37200541d3291f6b506731e14ce020bcf630`, base `6033e0d99e391528f3c131818dde1a19dd32f0f8`.
**Verdict : PASS_WITH_RESERVATIONS.**
**Décision J1 : VALIDÉ AVEC RÉSERVES pour les fondations d'accès distant et transfert réversible.** L'automatisation complète des releases, l'exécution après déconnexion SSH et le rollback relèvent de J4, non qualifié.

## Sources examinées et contrôles

- Lecture directe sur GitHub des 14 fichiers ajoutés dans `scripts/remote/` et `qualification/MC-INIT-002/`, du diff et des métadonnées PR. Aucun autre fichier modifié dans cette PR.
- Trois modules Python examinés : `remote.py`, `plan_witness.py`, `test_remote.py`. Exposition des seules opérations de lecture/diagnostic ; refus explicite de `sync` réel, `deploy`, `rollback`, `logs` et `stop` général.
- **13 empreintes SHA-256 sur 13** conformes au manifeste, après normalisation UTF-8/LF prescrite par `.gitattributes`. JSON des preuves consultés.
- 31 tests locaux **déclarés PASS** dans `tests-local.txt` ; code des tests relu. **La suite n'a pas été réexécutée indépendamment.** Aucun statut CI automatisé associé au commit n'a été observé.
- Flux SSH/UTF-8, code distant 37, timeout local, transfert réversible SFTP d'un témoin de 63 octets avec égalité de hash, suppression bornée et absence finale de la racine attestés par preuves sélectionnées.
- Processus témoin : erreurs intermédiaires consignées, correction puis `ALIVE_CONFIRMED / STOPPED / ABSENT_CONFIRMED`, code 0, **dans une session SSH unique**. Ne prouve aucune persistance après déconnexion.
- Contrôles de confidentialité ciblés sur contenu publié sans anomalie manifeste ; les sorties brutes exclues du dépôt public ne sont pas auditables ici.

## Réserves

1. Compte SSH actuellement administrateur ; ACL héritées larges. Les droits minimaux sont encore à traiter, sans changement implicite de comptes ni d'ACL.
2. `sync --dry-run` produit un plan local, sans création d'artefact ni vérification distante. Aucune release Git par SHA réellement déployée.
3. Délai par sous-processus ; timeout du client SSH sans garantie d'arrêt immédiat du traitement distant. L'arrêt et la récupération après panne doivent être conçus pour J4.
4. Les validations préalables de chemins ne sont pas un verrou : toute future mutation doit protéger contre la concurrence et les reparse points apparus entre vérification et utilisation.
5. `test --probe streams` renvoie volontairement le code 37 ; son interprétation doit être explicite dans les outils d'automatisation.
6. Les sorties SFTP peuvent exposer des chemins privés : conserver le brut local et prévoir une expurgation systématique avant publication.
7. Le témoin SFTP ne qualifie ni des artefacts plus volumineux, ni le lancement autonome, la santé, les mises à jour en place, le rollback ou Bluetooth HID.

## Git et décision

- PR #1 des preuves MC-INIT-001 : Draft, non fusionnée.
- PR #2 : Draft, non fusionnée ; revue COMMENT enregistrée sur GitHub, sans approbation de fusion ni déclenchement automatique.
- Aucun contrôle direct des machines par ChatGPT ; les preuves brutes restent locales.
- **MC-INIT-002 : PASS_WITH_RESERVATIONS**, fin du mandat. **J1 : VALIDÉ AVEC RÉSERVES**, pour le périmètre de qualification de l'environnement et du canal de transfert.
- **J4 : À faire**. Construire la synchronisation par SHA et le mécanisme versionné de release avant toute prétention de déploiement robuste.
- **J2 : NON QUALIFIÉ** malgré les indicateurs BLE favorables. Aucun appairage, publicité GATT ou mouvement HID.
- Les écritures distantes et modifications système d'un futur mandat restent soumises à autorisation explicite.
