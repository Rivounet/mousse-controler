# Procédure de mise en service — non exécutée

Cette procédure sépare les autorisations d'installation, d'activation et de
qualification matérielle. Chaque étape s'arrête en cas de preuve ambiguë.

## 1. Préconditions

1. Vérifier HEAD `0706aa9a86a2a5c2777a099ead1d0cec4b50ebb3`, arbre propre et
   rapport `full-local` PASS.
2. Vérifier l'intégrité des deux sauvegardes et l'espace disque.
3. Depuis la session propriétaire, relever état, dernière exécution et dernier
   résultat de `MousseControler-HOGP`, sans la démarrer.
4. Confirmer l'absence de processus Mousse/HOGP et de `RECOVERY_REQUIRED`.
5. Inventorier passivement PositionAgent et sa sauvegarde sur la cible.

## 2. Signature

1. Recevoir le PFX original par le canal secret approuvé.
2. Comparer son certificat public au signataire MSIX 1.0.0.2.
3. Sous autorisation, importer la clé dans `CurrentUser\My` du compte de build.
4. Reconstruire le MSIX 1.0.0.3 avec `-CertificateThumbprint`.
5. Vérifier signature, identité, version, contenu et SHA-256.
6. Relancer `full-local` et mettre à jour le manifeste de staging.

## 3. Sauvegarde immédiate

Arrêter ici si les empreintes courantes diffèrent des inventaires. Sinon,
refaire juste avant installation une sauvegarde atomique de : tâche,
configuration, journal + `.ids`, index + PNG, package installé, PositionAgent,
sa sauvegarde et tout marqueur de récupération.

## 4. Installation MSIX

Sous autorisation d'installation, tâche arrêtée et aucun moteur actif : installer
le package signé 1.0.0.3 comme mise à jour de la même identité. Vérifier version,
éditeur, signature, manifeste, alias et fichiers installés avant toute activation.

## 5. PositionAgent

Exécuter d'abord `Update-InteractivePositionAgent.ps1 -Action Plan`. Si le plan
confirme tâche, chemin, session et sauvegarde, autoriser séparément `Install`.
Tout échec doit restaurer le binaire précédent ou laisser
`RECOVERY_REQUIRED`, jamais poursuivre vers l'activation.

## 6. Migration atomique de configuration

1. Vérifier que tâche et processus sont arrêtés.
2. Copier la configuration proposée dans un fichier temporaire voisin sous
   `ProgramData`.
3. Relire JSON, déchiffrer DPAPI sans afficher les valeurs et vérifier les ACL.
4. Remplacer atomiquement `controller.json` sur le même volume.
5. Ne jamais déplacer séparément journal et `.ids`, ni index et PNG.

## 7. Réinscription et activation progressive

Sous autorisation d'activation, lancer le gestionnaire depuis le worktree
qualifié avec la configuration `ProgramData`. Cette action réinscrit puis
démarre la tâche ; ne pas l'utiliser pendant les phases de simple préparation.

Vérifier successivement : définition et principal, chemin du worktree qualifié,
processus et session, alias 1.0.0.3, serveurs locaux, journal + `.ids`, index,
absence d'erreur de récupération et commande locale `status`. Ne déclencher
aucune action HID pendant ce contrôle.

## 8. Qualification matérielle

Mandat distinct : consentement explicite, annonce de prise de souris, arrêt
d'urgence vérifié, puis HOGP, reconnexion, position, actions et captures
autorisées. Les preuves historiques ne remplacent pas cette requalification.

## 9. Rollback

1. Arrêt contrôlé puis confirmation de disparition des processus.
2. Restaurer la configuration sauvegardée et les persistances par ensembles.
3. Restaurer PositionAgent par son mécanisme transactionnel.
4. Restaurer le MSIX 1.0.0.2 signé selon la procédure Windows autorisée de
   remplacement de version ; ne jamais forcer une rétrogradation pendant qu'il
   est actif.
5. Restaurer la définition de tâche et vérifier les empreintes.
6. Ne redémarrer qu'après santé complète ; sinon conserver
   `RECOVERY_REQUIRED`.
