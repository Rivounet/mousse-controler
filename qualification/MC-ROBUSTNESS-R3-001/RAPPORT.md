# MC-ROBUSTNESS-R3-001 — rapport de qualification

Date : 21 novembre 2026

Base obligatoire : `a938b7455638c71846a20f7c4dc6c6c1f887e6e6`

Branche : `fix/mc-robustness-r3-001`

## Verdict

**PASS_WITH_RESERVATIONS** pour la qualification logicielle R3.

C-03, C-07 et C-08 sont corrigés et couverts par des tests déterministes. La
qualification emploie uniquement des doubles, le loopback local et des fichiers
temporaires. Aucun accès à `MonOrdinateur`, tâche planifiée réelle, rapport HID,
capture d'écran, radio, déploiement ou configuration de production n'a eu lieu.

## C-03 — quota dur des captures

- admission sous verrou avant création du PNG ;
- calcul du pic physique incluant l'image temporaire, l'index atomique, l'index
  courant, les orphelins, les fichiers temporaires et les index invalides
  conservés ;
- vérification séparée de l'espace disque libre ;
- téléversements concurrents sérialisés jusqu'au commit de l'index ;
- temporaire d'index unique, sans soustraction anticipée d'un fichier existant ;
- instrumentation de chaque étape et assertion du plafond sur l'occupation
  physique réellement mesurée ;
- refus explicite `CaptureQuotaError`, demande `FAILED` et aucun PNG créé ;
- réconciliation au redémarrage des PNG et temporaires non indexés en
  `DELETE_FAILED`, sans suppression automatique ;
- index invalide préservé sous `.capture-index.invalid-<id>.json`, puis index
  sain reconstruit ;
- refus de suppression toujours traçable et retentable.

## C-07 — cycle de vie des ressources

- chaque serveur est enregistré dès sa création ;
- fermeture en ordre inverse ;
- `shutdown()` seulement pour un serveur dont le thread a démarré,
  `server_close()` pour tout serveur créé ;
- attente des threads bornée à six secondes et timeout rendu observable ;
- fermeture du moteur d'actions et arrêt du contrôleur toujours tentés ;
- toutes les erreurs de nettoyage sont agrégées dans `RuntimeCleanupError` ;
- l'erreur d'initialisation ou d'exécution initiale reste accessible dans
  `primary` et par chaînage d'exception ;
- fermeture idempotente.

## C-08 — mise à jour transactionnelle de PositionAgent

- sauvegarde vérifiée par SHA-256 avant remplacement ;
- staging et binaire installé vérifiés par SHA-256 ;
- marqueur transactionnel atomique avec phase, empreintes, nombre de tentatives
  et dernière erreur ;
- confirmation seulement après état `Running` et présence du processus attendu ;
- panne après remplacement : restauration et redémarrage de la version
  précédente, deux tentatives maximum ;
- échec de restauration ou de redémarrage : marqueur durable
  `RECOVERY_REQUIRED` et nouvelle installation refusée ;
- rollback explicite vérifié par empreinte et conservation de la version
  remplacée ;
- injection de panne accessible uniquement au harness isolé lorsque
  `MC_POSITION_AGENT_TRANSACTION_TEST=1`.

## Correctif de revue B1/B2/B3

- **B1 :** les quatre états physiques sont formalisés et observés : image
  temporaire avec index courant, image finale avec index courant, image finale
  avec index courant et index temporaire, puis image finale avec nouvel index.
  Aucun octet existant n'est retranché avant un remplacement atomique effectif.
- **B2 :** l'état initial de tâche et le nombre de processus sont persistés. Une
  panne de préparation après arrêt redémarre et valide l'ancien agent s'il était
  actif ; une reprise non démontrée garde `RECOVERY_REQUIRED` et bloque Install.
- **B3 :** le rollback préserve d'abord la version courante et prépare la
  sauvegarde dans un staging vérifié. Les pannes avant mutation remettent l'état
  initial en service ; les pannes après mutation compensent depuis la copie
  préservée en deux essais, ou conservent tous les éléments avec
  `RECOVERY_REQUIRED`.

## Compatibilité et périmètre

Les protocoles HOGP, HID, HTTPS/HMAC, API et WebSocket ne sont pas modifiés.
Les quotas configurés ne sont pas augmentés. Le script continue de cibler
exclusivement la tâche `MousseControler-PositionAgent` et le binaire
`PositionAgent.exe`. Aucune dépendance externe n'est ajoutée.

## Réserves

1. Le verrou du quota est interne au processus ; une écriture concurrente par
   un processus externe reste détectée au prochain calcul mais ne peut être
   réservée atomiquement avec lui.
2. Un épuisement ou une panne du disque entre contrôle et commit peut encore
   interrompre la transaction ; l'état et les fichiers restants sont alors
   conservés pour réconciliation, sans prétendre à une transaction matérielle.
3. Le harness PowerShell qualifie le vrai script et les opérations de fichiers,
   mais remplace les cmdlets de tâche/processus. Il ne prouve ni les ACL ni le
   comportement réel du planificateur Windows sur la cible.
4. Les threads qui refusent de s'arrêter après six secondes produisent une
   erreur agrégée ; Python ne permet pas de tuer sûrement un thread arbitraire.
5. Aucune qualification matérielle ou de production n'a été réalisée.

## Rollback

Le rollback Git consiste à revenir au parent du commit R3. Le script conserve
sa sauvegarde `.mc-mouse-actions.previous` pour un rollback explicite. Aucun
état de production n'a été modifié pendant cette qualification.
