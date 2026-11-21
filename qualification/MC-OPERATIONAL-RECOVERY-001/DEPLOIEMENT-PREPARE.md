# Déploiement préparé — non autorisé

## Dossier local

`staging/MC-OPERATIONAL-RECOVERY-001/` contient :

- artefacts PositionAgent et MSIX courant non signé ;
- MSIX historique signé pour rollback seulement ;
- configuration contrôleur proposée et configuration agent préservée ;
- configuration contrôleur originale de rollback ;
- manifeste avec tailles, empreintes, qualification et blocages.

Ce dossier contient des secrets protégés et reste hors GitHub.

## Prérequis avant décision

1. Fournir le certificat de signature approuvé avec sa clé privée sans le
   publier ni modifier les magasins de confiance hors mandat.
2. Refaire le package, le signer et vérifier identité, chaîne et SHA-256.
3. Relancer `full-local` sur le SHA exact destiné au déploiement.
4. Obtenir une lecture autorisée des tâches mini-PC et cible.
5. Vérifier session interactive, version PositionAgent, sauvegarde cible et
   absence de `RECOVERY_REQUIRED`.
6. Obtenir une autorisation distincte d'installation puis d'activation.

## Ordre futur

1. **Préflight :** SHA, signatures, espace disque, ports, tâches, processus,
   persistances et rollback.
2. **Sauvegarde :** configuration, journal + `.ids`, index + images et binaires.
3. **Installation :** package signé, puis PositionAgent transactionnel ; aucun
   démarrage implicite.
4. **Configuration :** promouvoir atomiquement la copie proposée.
5. **Activation mini-PC :** tâche interactive contrôlée, une seule instance.
6. **Activation cible :** seulement en session console vérifiée.
7. **Santé :** chemins et SHA chargés, tâches, processus, ports loopback,
   journal/index valides et absence de récupération requise.
8. **Qualification matérielle :** mandat distinct, accord de prise de souris,
   mécanisme d'arrêt et aucune capture non explicitement autorisée.

## Arrêt et rollback futurs

- publier l'intention d'arrêt, utiliser la commande locale authentifiée puis
  arrêter la tâche gérée ;
- vérifier la disparition des processus avant remplacement ;
- restaurer configuration, package et PositionAgent depuis les copies vérifiées ;
- restaurer les persistances par ensembles cohérents ;
- si une restauration n'est pas prouvée, conserver `RECOVERY_REQUIRED` et ne
  pas redémarrer.
