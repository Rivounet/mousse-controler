# Reprise — Mousse-controler

**État documentaire au 28 novembre 2026.**

## Source de vérité

- Le SHA exact de `main` au moment de la porte de qualification est la seule
  source admissible pour construire la release.
- Une release active antérieure, même saine, n'est pas une preuve pour le
  `main` courant.
- Les qualifications historiques réalisées avec `MonOrdinateur` ne qualifient
  pas `DESKTOP-NPIHO8K`.
- La production `mini-pc-backend` est préservée. Le chantier like-prod utilise
  une instance HOGP, une configuration et des tâches de qualification distinctes.

## Architecture à reprendre

- `MouseApplicationService` sépare les protocoles du métier ;
- `OperationCoordinator` possède l'unique voie de commande locale ;
- `PositionAgent --config` publie uniquement télémétrie et captures ; la
  reconnexion HOGP est un mode et une tâche distincts ;
- toute sélection Bluetooth mutante exige le nom exact et l'empreinte SHA-256
  de l'identité WinRT attendue ;
- le moteur HOGP exige exactement un abonné actif autorisé et lui envoie la
  notification de manière ciblée ;
- la release contrôleur est construite depuis les objets d'un SHA propre,
  vérifiée avant lancement et exécutée avec `python -B` ;
- un arrêt protocolaire non acquitté mais suivi d'une terminaison confirmée est
  publié comme `last_stop_outcome=forced`; seul un processus non terminé impose
  `recovery_required` ;
- les actions matérielles exigent une paire de baux de qualification fraîche,
  croisée et liée au même `run_id` et au même SHA.

## Porte de qualification like-prod

1. Obtenir un arbre propre et exécuter
   `python -B scripts/qualification/qualify.py --profile full-local`.
2. Construire les artefacts et la release immuable depuis ce SHA, puis vérifier
   les manifestes et empreintes avant transfert.
3. Acquérir un bail `backend` sur `mini-pc-backend` et un bail `target` sur
   `DESKTOP-NPIHO8K` avec `Manage-QualificationLease.ps1`. Les deux statuts
   doivent désigner l'autre machine, le même `run_id` et le même SHA.
4. Utiliser uniquement les tâches `MC-HID-EXEC-001` et l'instance HOGP de
   qualification. Ne pas démarrer ni repointer la tâche de production.
5. Inspecter l'identité du périphérique backend depuis la cible avant pairage,
   puis imposer cette empreinte pour `Pair` et `Connect`. Enrôler séparément
   l'empreinte de la cible observée par le moteur HOGP côté backend.
6. Exiger `authorized_subscriber=True`, `subscriber_count=1`, l'empreinte
   attendue, une session `Active`, `buttons=0`, une position fraîche et aucune
   action active.
7. Ouvrir la surface sûre visible et exécuter le scénario borné avec
   `qualify_mouse_actions_runtime.py`, qui refuse d'agir sans la paire de baux.
8. Arrêter le témoin, l'agent, le contrôleur et l'advertising de qualification ;
   prouver l'absence de processus/tâche résiduel, puis libérer les deux baux.
9. Archiver les preuves expurgées au SHA exact. Fusion, synchronisation de
   `main` et éventuel déploiement de production restent des portes distinctes.

## Reprise après incident

Ne jamais rejouer une action non idempotente à issue ambiguë. Un bail expiré ne
se renouvelle pas : arrêter les composants de qualification, constater leur
état, puis acquérir un nouveau run. Si `termination_failed=True` ou
`recovery_required=True`, ne pas relancer avant disparition vérifiée du processus
HOGP. Les jetons de bail, secrets DPAPI, identités WinRT brutes et captures non
expurgées ne sont pas des artefacts Git.
