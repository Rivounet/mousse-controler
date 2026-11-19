# Protocole proposé — lancement Windows par SSH

**Préparation seulement. NON_EXÉCUTÉ pendant MC-INIT-003.** Le précédent accord MC-INIT-002 ne couvre aucune nouvelle écriture. Une nouvelle autorisation doit précéder création, lancement, suppression ou modification d’état. Les chemins génériques ci-dessous devront être développés en chemins exacts et les commandes complètes montrées à l’utilisateur avant cet accord.

## Méthodes comparées

| Méthode | Intérêt | Réserves et décision |
|---|---|---|
| Commande au premier plan dans SSH | Sorties et codes directement collectables, arrêt lié au canal | Pas de promesse de survie à la déconnexion ; premier choix pour tests courts sous supervision |
| Start-Process dans la session SSH | Disponible, processus témoin déjà arrêté dans une session unique en MC-INIT-002 | Sa survie après fermeture du canal n’a pas été démontrée ; ne pas en faire un superviseur durable |
| Win32_Process.Create via CIM | Candidat à étudier avec contrôle d’identité et journaux dédiés | Contexte de session et droits à relever ; aucun usage interactif/Bluetooth présumé. Pas un résultat matériel acquis |
| Tâche planifiée ou service | Supervision indépendante potentielle | Modifie un état système persistant ; exclu de ce mandat sans décision séparée |

Microsoft décrit la fin d’un processus Start-Process à la fermeture d’une session distante et recommande d’attendre sa fin si nécessaire. Cela motive le protocole ; ce n’est pas une preuve spécifique à l’hôte SSH actuel. Les règles Win32 des job objects indiquent notamment le cas des créations Win32_Process.Create ; leur résultat sur le mini-PC reste à mesurer. Sources primaires consultées le 19 novembre 2026 : [Start-Process 5.1](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process?view=powershell-5.1), [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

## Préconditions et autorisation à préparer

1. Choisir un identifiant unique, une racine dédiée autorisée et un sous-répertoire `staging/MC-INIT-003-<ID>`. Développer les chemins exacts du dossier, `probe.log` et `process.json` dans un protocole local ; ne rien réutiliser sans inspection. Présenter aussi tous les fichiers locaux de préparation/récupération et leur contenu.
2. Vérifier en lecture seule identité SSH stricte, nom de machine, session et privilèges, état des chemins et ancêtres sans reparse point. Relever l’existence initiale et les ACL, sans les changer. Interdire les écritures hors de ce dossier.
3. Préparer les commandes intégrales : création exclusive des seuls dossiers manquants, processus témoin masqué, écriture des deux seuls fichiers prévus, lecture de son identité et journaux, arrêt borné, transfert SFTP de retour, effacement contrôlé. Les commandes ne doivent pas contenir de secret ni de changement de configuration.
4. Obtenir l’accord explicite pour ces chemins et ces opérations, avec nettoyage et risques. Sans accord : s’arrêter au protocole, résultats distants NON_EXÉCUTÉS.

## Expérience bornée, après cet accord uniquement

1. Créer les dossiers prévus, sans écrasement et avec liste exacte des créations. Recontrôler chemins/ACL et absence de fichiers préexistants. Ne pas créer source/releases/state ni toucher à une version applicative.
2. Lancer une attente PowerShell maximale de 60 secondes, fenêtre masquée. Le témoin ne fait qu’écrire un démarrage et des battements UTC dans probe.log UTF-8, puis se termine. Inclure un identifiant unique dans la commande encodée. Pas de Bluetooth, réseau applicatif, tâche ou service installé.
3. Tester d’abord une méthode, puis une seconde si autorisée. Pour chaque processus : capturer PID, CreationDate CIM, StartTime Get-Process, exécutable, commande complète et SessionId ; ne pas comparer les précisions de deux API différentes comme s’il s’agissait de la même représentation.
4. Fermer complètement la connexion SSH de lancement. Revenir via une nouvelle connexion après un délai court et comparer l’identité ; relever vivant/disparu, session et progression du journal. Un ALREADY_EXITED ne prouve pas l’arrêt contrôlé ni la persistance.
5. Si le processus est encore vivant : vérifier de nouveau toutes ses identités, puis arrêter uniquement celui-là et constater son absence. Une identité différente interdit l’arrêt ; l’attente bornée limite l’orphelin possible à 60 secondes.
6. Après arrêt ou expiration, calculer SHA-256 des deux fichiers distants, les télécharger par SFTP et comparer octets/empreintes. Le retour local doit être neuf, sans écraser un précédent résultat. Conserver les preuves brutes localement et expurger chemins/comptes/PIDs avant publication.
7. Nettoyer seulement les fichiers de ce témoin dont l’origine et le hash sont confirmés ; supprimer seulement les dossiers effectivement créés et restés vides, sans récursivité. Toute donnée inconnue bloque le nettoyage. Recontrôler l’absence du processus et l’état initial des chemins préservés.

## Interruptions et critères

Une perte SSH ne prouve ni arrêt ni survie. Après interruption : reconnecter, relire identité et journaux ; ne pas relancer un doublon automatiquement. Attendre l’expiration si l’identité manque, sans Stop-Process par nom ni balayage destructif. Un fichier partiel/inconnu reste conservé et signalé. Aucun service tiers ou session utilisateur n’est interrompu.

Chaque cas reçoit PASS / FAIL / NON_EXÉCUTÉ : méthode, session, survie à déconnexion, code, logs intègres, arrêt et absence finale. Même en cas de PASS de ce témoin, ne pas extrapoler à une future application BLE, à son contexte interactif ou à un service permanent. Cette qualification n’est pas l’activation d’une release Git ni un rollback applicatif.
