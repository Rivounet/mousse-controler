# Plan de synchronisation réversible — non exécuté

## Préconditions communes

- clone concerné : `C:\Projets\Mousse-controler\source` ;
- SHA source observé : `34b2612bef260db382251601c103886dd76dd12a` ;
- SHA cible proposé : `fe4def1dd6f5a895a81ec60e52b480bb5fbc9421` ;
- obtenir un mandat explicite pour chaque phase ci-dessous ;
- confirmer arbre propre, espace disque, absence de processus et état réel des
  tâches avant toute mutation ;
- inventorier et sauvegarder séparément `runtime/`, `state/`, `logs/`,
  `releases/`, les artefacts ignorés de `source/out/` et toute persistance
  découverte ;
- ne jamais intégrer les secrets, captures ou états opérationnels dans Git.

## 1. Synchronisation Git

1. Capturer branche, HEAD, références, fichiers ignorés utiles et empreintes.
2. Créer une sauvegarde récupérable du clone et des artefacts hors Git.
3. Actualiser les références distantes sous mandat, vérifier que la cible exacte
   est toujours `fe4def1…`, puis positionner une branche contrôlée sur ce SHA.
4. Ne pas écraser les répertoires opérationnels séparés.

**Rollback :** restaurer le clone sauvegardé ou revenir par une branche dédiée
au SHA source, sans `reset --hard` sur un travail inconnu.

## 2. Construction des artefacts

1. Exécuter la qualification logicielle/build prescrite sur le SHA cible.
2. Reconstruire MSIX et PositionAgent dans un nouveau répertoire d'artefacts.
3. Consigner tailles, versions et SHA-256 ; comparer au package installé sans
   exiger une identité bit-à-bit si le contrat ne la garantit pas.
4. Conserver les anciens artefacts jusqu'à qualification du remplacement.

**Rollback :** supprimer seulement le nouveau staging identifié ; conserver les
artefacts précédents intacts.

## 3. Mise à jour des configurations

1. Sauvegarder la configuration et son empreinte.
2. Remplacer le chemin C++ historique par l'alias officiel
   `mousse-hogp-packaged.exe`.
3. Déclarer explicitement `action_journal` et `capture_directory` dans un
   emplacement opérationnel sauvegardé.
4. Préserver ensemble journal et `.ids`, ainsi que l'index et les images selon
   leur contrat de rétention.
5. Valider syntaxe, chemins, permissions minimales et absence de secret dans les
   journaux de preuve.

**Rollback :** restauration atomique de la configuration sauvegardée ; aucune
activation si les empreintes ou persistances sont ambiguës.

## 4. Installation

1. Inspecter d'abord les tâches et le package réellement installés avec les
   droits de lecture autorisés.
2. Installer uniquement les artefacts qualifiés et signés, sous mandat dédié.
3. Pour PositionAgent, utiliser la transaction prévue avec sauvegarde vérifiée,
   staging et marqueur de récupération.
4. Ne modifier ni certificat, magasin de confiance, ACL ni pare-feu sans mandat
   spécifique.

**Rollback :** package/configuration précédents et binaire PositionAgent
`.previous` vérifiés ; conserver `RECOVERY_REQUIRED` si la restauration échoue.

## 5. Activation

1. Vérifier sessions, tâches, processus, ports et absence de concurrence.
2. Démarrer seulement les tâches approuvées, une composante à la fois.
3. Confirmer SHA/chemin réellement chargés, état du package et journaux bornés.
4. Arrêter et restaurer immédiatement en cas d'identité ou persistance ambiguë.

**Rollback :** arrêt contrôlé, restauration des configurations et artefacts,
puis vérification qu'aucun processus candidat ne demeure.

## 6. Qualification matérielle

Phase séparée exigeant accord explicite, annonce de prise de souris et mécanisme
d'arrêt. Vérifier HOGP, reconnexion, position réelle, actions et captures
autorisées sans réutiliser automatiquement les preuves historiques.

## Critères de vérification finale

- HEAD et artefacts correspondent au SHA cible approuvé ;
- arbre Git propre et persistances hors Git intactes ;
- transport configuré PowerShell/WinRT, package et alias vérifiés ;
- tâches et processus identifiés dans les sessions attendues ;
- journal, `.ids`, index et politique de conservation cohérents ;
- aucun `RECOVERY_REQUIRED` non traité ;
- rollback testé dans le périmètre autorisé ;
- qualification logicielle puis matérielle consignées séparément.


