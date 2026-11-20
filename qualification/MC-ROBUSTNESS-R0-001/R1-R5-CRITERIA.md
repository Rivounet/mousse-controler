# Critères de sortie proposés pour R1 à R5

Ces critères dérivent du rapport de consolidation et des reproductions R0. Ils
n'autorisent aucune correction dans la présente PR.

## R1 — sûreté des actions et arrêt

- press/release/hold/drag/click incertains testés sous chaque politique d'erreur ;
- transition ambiguë => `UNKNOWN` et quarantaine/arrêt indépendamment de
  `continue`, sans rejeu ;
- arrêt global coordonne exécuteur moderne et séquenceur historique dans les
  états MOVING, WAITING et PAUSED ;
- file pleine, file non vide à `close()` et action suspendue finissent dans un
  état terminal durable ;
- zéro nouveau rapport après l'intention d'arrêt ; suite logicielle complète PASS.

## R2 — bornes HOGP et serveur LAN

- deadlines documentées et mesurées pour démarrage, lecture, commande et arrêt ;
- processus muet, réponse partielle, mort et `stderr` saturé ne bloquent ni
  appelant ni fermeture ;
- chemin d'arrêt indépendant du verrou/canal bloqué ;
- handshake, lecture du corps, connexions actives et file d'attente bornés ;
- client lent/tronqué refusé, clients sains suivants servis, TLS/HMAC inchangés ;
- aucune commande ambiguë rejouée.

## R3 — quotas, ressources et déploiement

- quota dur vérifié avant admission et incluant temporaires, index et orphelins ;
- refus de suppression conserve `DELETE_FAILED`, chemin et possibilité de retry ;
- redémarrage réconcilie tous les fichiers sans oubli ni faux `DELETED` ;
- toute création partielle/fermeture défaillante nettoie best-effort toutes les
  ressources, avec erreur finale observable ;
- mise à jour et rollback testés par injection à chaque étape, restauration
  bornée et état `recovery required` explicite ;
- aucune cible réelle requise pour la porte logicielle.

## R4 — tests et reproductibilité

- commandes distinctes pour unité, intégration simulée et matériel opt-in ;
- commande logicielle unique incapable par construction de toucher radio/session ;
- CI Windows exécute caractérisations, build C# et analyse PowerShell ;
- découverte contrôlée des SDK/Build Tools, sans chemin unique implicite ;
- versions, durées, exclusions et preuves publiées automatiquement.

## R5 — refactoring minimal

- chaque extraction a une mesure avant/après de complexité ou duplication ;
- aucun changement de protocole, état, performance ou compatibilité sans contrat ;
- code HOGP historique supprimé seulement après preuve d'absence d'usage ;
- aucune troisième implémentation de séquenceur ;
- géométries extrêmes et doublons du catalogue couverts par tests comportementaux ;
- petites PR indépendantes, rollback Git simple et suite complète PASS.
