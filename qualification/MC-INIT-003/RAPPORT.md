# MC-INIT-003 — artefacts Git et releases versionnées

19 novembre 2026 — rapport Codex pour revue indépendante ChatGPT. Livrable local de fondations J4 ; aucune validation de déploiement distant revendiquée. Le mandat fourni dans la conversation n’a pas été copié dans GitHub.

## 1. État Git et dépendance

Au début : checkout propre de la PR #2, SHA `cf3c37200541d3291f6b506731e14ce020bcf630`, aucun commit non publié détecté. Main local `6033e0d99e391528f3c131818dde1a19dd32f0f8` ; fetch a trouvé `bd55aaaa1a8dd9825128b758aff6b22873871d47`. Main a été avancé en fast-forward après contrôle de propreté et d’ascendance, sans fusion des PR. Les nouvelles instructions et revues de main ont été lues directement depuis origin/main.

PR #1 : Draft non fusionnée, tête `8886cab1230039add8e2712a5114c4e312c0f49b`. PR #2 : Draft non fusionnée, tête `cf3c37200541d3291f6b506731e14ce020bcf630`. Leur état a été vérifié via le connecteur GitHub.

Branche créée : `feat/mc-init-003-versioned-deployment`, depuis la tête de la PR #2. **La PR MC-INIT-003 cible `feat/mc-init-002-remote-qualification`, pas main.** Les scripts MC-INIT-002 sont donc hérités de cette dépendance encore non fusionnée ; ils ne sont pas supposés présents dans main. Le diff propre à MC-INIT-003 n’édite aucun fichier officiel ni fichier hérité. Après décision sur la PR #2, la base de comparaison devra être réexaminée explicitement ; aucun retarget/merge automatique.

Commit technique préparé et testé : `1a438e1422b05a5a77f4f35c860aaf0eb165feb9`. La tête finale de publication, qui ajoute les preuves, est fournie dans la PR et le compte rendu. Les fichiers d’architecture officiels ne sont pas modifiés. Les mandats anciens présents dans le checkout hérité ne sont ni réintroduits dans main ni modifiés par ce diff ; l’état documentaire récent de main est distinct de cette base empilée.

## 2. Architecture retenue

Préparation locale : sélection explicite de blobs d’un commit Git complet, ZIP déterministe et manifeste externe, empreintes de l’archive et de chaque fichier. Préparation hors du dépôt source, sans lire les copies de travail des fichiers sélectionnés.

Organisation cible conservée : source facultative, staging, releases, state, logs. Les releases sont identifiées par `<SHA_40>-<HASH_64>`, chacune contenant un bundle et les fichiers vérifiés. Les données d’exécution et journaux sont hors releases. Aucune release n’est nettoyée ou modifiée en place par le moteur.

Le modèle utilise **un snapshot `state/active.json` contenant ensemble active et previous**, ainsi que phase et identité modèle ; il remplace la paire de pointeurs séparés envisagée, afin de n’avoir qu’un point de publication atomique. Pas de lien symbolique Windows. Les phases stable/pending/recovery_required rendent une interruption explicite. Le verrou exclusif par dossier interdit deux opérations coopérantes et protège également les lectures de status. Un verrou abandonné exige une inspection manuelle et n’est jamais supprimé automatiquement.

Le stockage de releases est réel mais **local**, dans une racine marquée `mousse-controler-sim`. Le moteur applicatif est **simulé** : ses PID et dates sont des identités fictives persistées en JSON. Aucune commande model ne lance ou n’arrête un processus Windows réel. Ce modèle teste la logique de versionnement et les échecs ; il ne qualifie pas Windows/SSH comme superviseur.

## 3. Fonctions réellement livrées

| Interface | Fonctionnement observé |
|---|---|
| deployment.py sync --dry-run | Lit un commit complet et un dépôt propre, calcule en mémoire les fichiers et le hash, affiche cible et contrôles/blocages ; aucun fichier de sortie ni connexion distante |
| deployment.py sync | Prépare réellement artifact.zip et manifest.json localement ; remote_contacted=false et remote_synced=false |
| model init/ingest | Crée un stockage local explicitement simulé, vérifie et enregistre une release sans écraser une existante |
| model deploy/status/stop | Activation, santé, identité et arrêt du moteur **simulé**, avec état et journaux réels locaux |
| model rollback/recover | Retour à une release précédente et reprise après interruption dans le **modèle local** |
| Ancien remote.py | Conservé intégralement ; ses interfaces distantes non implémentées restent des refus explicites |

Sécurité des artefacts : SHA complet existant, état Git propre avant/après lecture, préfixes de fichiers explicitement sélectionnés, refus des liens et sous-modules, collisions de casse et noms Windows dangereux. Les blobs sont lus par leurs identifiants Git, sans conversion des fins de ligne. Un fichier ignoré présent localement n’entre pas dans l’archive. Les fichiers de configuration/clé connus et certains marqueurs de secrets sont refusés ; cette détection ciblée ne certifie pas l’absence de tout secret et la sélection reste à revoir.

Intégrité : contenu, tailles, modes et hash de chaque entrée contrôlés ; archive canonique reconstruite et comparée ; fichiers non listés ou éléments supplémentaires refusés. Une version existante identique est réutilisée ; une version altérée est conservée et refusée. Un transfert déclaré en erreur ne peut pas enregistrer de release, même si les octets sembleraient complets. Le transfert réseau de release n’est pas implémenté : ingest reçoit un bundle local jouant le rôle de bundle reçu.

Activation modèle : vérification candidate et références conservées, intention durable avant arrêt, démarrage/identité/santé, publication du snapshot. Sur échec : arrêt de la candidate identifiée et restauration vérifiée ; l’opération initiale reste FAIL. En cas d’échec de restauration : recovery_required et refus de deploy. Sans ancienne version : retour à l’état inactif. Les identifiants d’opération permettent de retrouver un démarrage modèle interrompu avant publication et évitent les doublons lors de recover.

Guide et commandes : [DEPLOYMENT.md](../../scripts/remote/DEPLOYMENT.md). Aucun package externe ajouté ; Python 3.12 et Git existants suffisent.

## 4. Tests locaux exécutés

Commande : `python -B -m unittest discover -s scripts/remote -p 'test_*.py' -v`, avec MC_TEST_TMP pointant vers un répertoire local court, hors dépôt.

**69 tests PASS : 31 hérités inchangés et 38 nouveaux.** Les tests utilisent de vrais dépôts Git et fichiers temporaires ; le runtime reste simulé, aucun SSH. Couverture : SHA invalide/inconnu/ancien valide, dépôt propre/index modifié/arbre modifié/non suivi, fichier ignoré exclu, artefact déterministe, hash erroné, bundle incomplet, sélection interdite, mode lien/sous-module, casse, transfert interrompu, release déjà présente/altérée, répertoire hors modèle, concurrence réelle entre deux threads via verrou système de fichiers, verrou abandonné préservé, échec de start/activation/santé, absence de précédente, rollback explicite défaillant, restauration défaillante, interruption après intention/après démarrage, reprise sans doublon, processus modèle absent ou identité différente.

Premier passage : 65 tests, 19 erreurs de nouveaux tests de releases causées par des chemins temporaires Windows longs. Correction : contrôle du budget de destination finale avant copie et répertoire court configurable pour les nouveaux tests. Passage suivant : 65 PASS, puis ajout de quatre cas de non-régression et durcissement : 69 PASS. Dernier passage sur le commit technique : 69 PASS. Les traces initiales contenant des chemins personnels restent locales ; [historique expurgé](evidence/tests-history.json) et [sortie finale](evidence/tests-local.txt) sont publiés.

Le refus de longues destinations est conservateur (240 caractères) ; aucun réglage Windows de chemins longs n’a été modifié. Les 31 tests existants et leurs fichiers n’ont pas été édités.

## 5. Démonstration sur les commits réels du projet

Préparation locale de deux versions avec sélection `scripts/remote` : `cf3c37200541d3291f6b506731e14ce020bcf630` et `1a438e1422b05a5a77f4f35c860aaf0eb165feb9`.

Nouvel artefact : 10 fichiers, 101481 octets, SHA-256 `bf5d0098c39b67c490a4fa78b72cb3d20e4a63576465ae7e86a78075a339e428`. Deux reconstructions ont donné des octets d’archive et de manifeste identiques. Réutilisation du bundle : REUSED_IDENTICAL. Activation modèle de la première puis de la seconde, rollback vers la première avec santé simulée positive, arrêt puis status ABSENT. Aucun de ces artefacts n’a été transféré ou exécuté sur mini-pc-backend.

Preuves : [manifeste de l’artefact](evidence/artifact-manifest.json), [plan sans écriture](evidence/dry-run.json), [démonstration locale](evidence/demo-local.json), [journal du modèle](evidence/demo-events.jsonl). Les ZIP, fichiers extraits, état et journaux bruts locaux restent hors Git ; pas d’artefact binaire inutile dans la PR. Le SHA préparé est celui du code, pas celui du futur commit de publication des preuves, et aucun n’est présenté comme déployé.

## 6. Lancement Windows distant

L’étude compare premier plan SSH, Start-Process, candidat CIM Win32_Process.Create et supervision système. **Aucune nouvelle connexion, écriture, suppression ou exécution distante pendant MC-INIT-003.** L’accord du témoin MC-INIT-002 n’a pas été réutilisé.

Le [protocole de lancement](PROTOCOLE-LANCEMENT.md) définit l’expérience bornée, les journaux, l’identité du processus, la fermeture/réouverture de SSH, les comparaisons de hash et le nettoyage. Il exige de présenter à nouveau les chemins et commandes exacts puis d’attendre une autorisation distincte avant toute mutation. À ce stade, c’est un protocole d’expérience, pas un exécuteur opérationnel ni une autorisation sollicitée pour des chemins encore non développés.

Microsoft décrit une fin possible du processus Start-Process en session distante à la fermeture de celle-ci ; les règles des job objects motivent l’étude d’un lancement via CIM. Ces sources ne démontrent pas le comportement du mini-PC actuel. Sources et limites sont liées dans le protocole ; aucun contournement de configuration ni service installé. La survie à une déconnexion, les sessions Windows, journaux applicatifs distants et arrêt d’une application future restent NON_EXÉCUTÉS.

## 7. Limites et risques

- Le backend applicatif et sa santé sont simulés. Le verrou et les remplacements de fichiers sont testés localement ; pas de garantie de déploiement Windows distant, de réseau dégradé réel, de coupure électrique ou de stabilité longue durée.
- Le verrou ne protège que les outils coopérants. Les contrôles de liens/jonctions et hashes ne neutralisent pas un administrateur hostile changeant les chemins entre vérification et utilisation. Les releases sont immuables par contrat et contrôle d’intégrité, sans changement d’ACL.
- Un arrêt brutal du processus de contrôle peut laisser un verrou et du staging ; pas de suppression automatique. Le snapshot et le journal guident une récupération contrôlée. fsync et remplacement de snapshot ne sont pas une transaction matérielle couvrant plusieurs fichiers.
- La préparation d’un artefact n’est pas sa signature : la confiance repose aussi sur la revue du commit, la sélection et le futur transport authentifié. Une sélection de scripts techniques ne représente pas un exécutable applicatif prêt pour production.
- Compte SSH existant administrateur selon MC-INIT-002, non requalifié aujourd’hui. La préparation et le modèle n’exigent aucun privilège administrateur ; pour le futur transport, proposer un compte standard et des droits limités à la racine dédiée, sans créer le compte ni modifier ses ACL. Les besoins CIM et le contexte BLE devront être mesurés séparément avant décision.
- La PR dépend de la PR #2 non fusionnée. Aucun changement de main distant, aucune fusion, aucun force-push, aucune édition du référentiel officiel ou du mandat dans GitHub.

## 8. Suite recommandée

Revue indépendante du diff propre à MC-INIT-003 et des preuves par ChatGPT. Décider séparément de l’intégration des PR existantes et de la base future. Après revue : développer les chemins/commandes du protocole témoin pour autorisation, qualifier le lancement distant et le contexte de session, puis seulement concevoir le transport réel d’une release et le backend applicatif avec santé/stop fiables. Ne pas extrapoler le modèle local à un rollback distant validé. Aucun développement Bluetooth HID engagé.

Le [manifeste de publication](MANIFESTE.md) donne les fichiers, origines, empreintes et exclusions ; la PR et le compte rendu identifient le SHA publié et sa base réelle.
