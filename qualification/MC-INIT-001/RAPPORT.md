# Mousse-controler — Rapport de qualification MC-INIT-001
> Édition de publication MC-INIT-001-PUBLICATION, 19 novembre 2026. Rapport historique expurgé, sans nouveau diagnostic matériel ni nouvelle connexion au mini-PC. Les constats ci-dessous datent de MC-INIT-001 ; les chemins entre chevrons sont des marqueurs, pas des chemins utilisables. Les preuves publiées sont sélectionnées et ne constituent pas les journaux bruts complets. Voir [MANIFESTE.md](MANIFESTE.md).

> État Git de publication : arbre initial propre, aucune divergence ; fast-forward autorisé de `main` depuis `84dbade9fe74ed8c38f4aa1b089a44c194dfa288` vers `86ed1088bc1e2ae7984c4c4ccfd0bb0af8755b02`, puis création de `docs/mc-init-001-evidence`. Aucun document officiel modifié. Les états Git « finaux » et les propositions documentaires dans le rapport sont ceux du diagnostic antérieur ; la documentation officielle a depuis évolué sous la responsabilité de ChatGPT.

Date : 19 novembre 2026, Europe/Paris
Destinataire : ChatGPT, pour revue indépendante
Statut proposé : mandat d’inventaire livré avec réserves ; J1 non validé.

## 1. État initial et final du dépôt

Le répertoire `<RACINE_PROJET>` était vide et ne constituait pas un dépôt Git. Aucun clone portant ce nom n’a été trouvé dans l’inventaire borné de `<RACINE_PROJETS>` (profondeur 2). Cette recherche n’est pas un inventaire exhaustif de tous les disques et profils.

Commande : git ls-remote https://github.com/Rivounet/mousse-controler.git
Référence au démarrage : HEAD et refs/heads/main = 84dbade9fe74ed8c38f4aa1b089a44c194dfa288 ; aucune autre référence annoncée.
Commande : git clone https://github.com/Rivounet/mousse-controler.git repository
Clone créé : `<CLONE_LOCAL>`
origin fetch/push : https://github.com/Rivounet/mousse-controler.git
Branche locale : main, au SHA initial ci-dessus ; aucun changement préexistant, commit local non publié ou branche locale supplémentaire observé.

Commandes : git -C repository status --short --branch ; remote -v ; branch -avv ; log --all --not --remotes --oneline ; fsck --full.
Résultats : arbre propre, aucun commit non publié détecté, fsck sans erreur affichée.

Pendant le diagnostic, GitHub a avancé vers 1527797a555b97ae2bced2b1864f1a010422cb9a. Un git fetch origin a récupéré ces commits sans déplacer main. Le diff main..origin/main concerne exclusivement README, AGENTS, DECISIONS, PLANNING et les nouveaux documents REPRISE et MANDATS/MC-INIT-001. Ces documents ont été examinés. Ils ne changent pas le périmètre autorisé.

État final : main local reste à 84dbade… ; origin/main vaut 1527797… ; le clone contient donc la référence distante observée mais son checkout main n’est plus à jour. Ne pas présenter ces deux références comme identiques. Une future reprise pourra avancer main uniquement en fast-forward après nouveau contrôle de propreté et du mandat. Aucun push, commit, branche, PR, merge ni modification documentaire officielle n’a été réalisé par Codex.

Documents lus : AGENTS.md, README.md, ROADMAP.md, PLANNING.md, ARCHITECTURE.md, ACCES-DISTANT-ET-SYNCHRONISATION.md, DEPLOIEMENT.md, TESTS.md, DECISIONS.md ; puis nouveautés REPRISE.md et MANDATS/MC-INIT-001.md via le diff récupéré.

## 2. Diagnostic du PC Windows de développement et cible HID

Preuve : evidence/windows-inventory.json ; commandes dans Inventory-ReadOnly.ps1, conservé uniquement en local ; sélection publiée décrite dans MANIFESTE.md.

OS : Windows 11 Famille x64, 10.0.26300, build 26300.
Matériel : ASUS VivoBook X513UA/M513UA, Ryzen 5 5500U, 6 cœurs / 12 threads, environ 7,38 Gio de RAM utilisable. Mémoire libre observée : environ 0,90 Gio ; valeur instantanée, sans test de charge.
Disque C : environ 195,31 Gio, dont 19,53 Gio libres au relevé.
Shell Codex : PowerShell Core 7.6.9 x64 fourni par le runtime Codex ; processus local non administrateur lors du relevé.
Codex Desktop : chemins des processus observés sous OpenAI.Codex_26.1111.2228.0 ; runtime PowerShell sous OpenAI.CodexPrimaryRuntime 26.1112.611.0. Il s’agit d’une exécution Windows native avec bac à sable, pas d’une session Linux.
Versions exécutées : Git 2.54.0.windows.1 ; Python 3.12.10 ; Node v26.12.1 ; GitHub CLI 2.95.0. npm, VS Code, py, ssh/scp/sftp et wsl sont trouvés dans PATH ; leur présence ne qualifie pas tous leurs usages. OpenSSH local : 9.5p2, LibreSSL 3.8.2. dotnet non trouvé dans PATH.
Réseau : Wi-Fi Realtek 8821CE actif, débit de liaison observé 325 Mbps, sans mesure de débit utile ni de stabilité. Connexions GitHub HTTPS et SSH mini-PC démontrées.
Bluetooth : Realtek USB VID_13D3/PID_3556, état PnP OK ; pilote 1.1072.2312.2502, daté du 13 février 2025. Des entrées PnP historiques ont l’état Unknown : ce n’est pas une preuve d’indisponibilité du contrôleur actif.
Services : bthserv actif ; ssh-agent actif ; TermService et WinRM arrêtés. Aucun serveur entrant local supplémentaire nécessaire pour la maintenance du mini-PC.
Répertoire de développement retenu : clone dédié sous `<CLONE_LOCAL>`. Les preuves restent dans le dossier frère qualification, hors dépôt.

Les requêtes CIM/réseau et GitHub ont d’abord échoué dans le bac à sable. Les relances autorisées hors de cette restriction ont fonctionné. Aucun changement système n’a été nécessaire.

## 3. Diagnostic de mini-pc-backend

Preuves : evidence/mini-pc-inventory.json et evidence/remote-access.txt.
Accès : alias SSH existant mini-pc-backend, réseau privé, compte [EXPURGÉ], clé déjà configurée. Aucun secret n’a été lu. BatchMode, IdentitiesOnly et StrictHostKeyChecking sont activés.
Identité retournée : Mini-PC-Backend ; compte [EXPURGÉ]. Empreinte ED25519 [EXPURGÉE] : correspondance entre known_hosts local et clé publique hôte lue sur le mini-PC. Cela confirme la continuité avec l’identité déjà approuvée, sans nouveau canal indépendant d’attestation.
OS : Windows 11 Professionnel x64, 10.0.26300.
Matériel : Intel Jasper Lake, Celeron N5105 à 2 GHz, 4 cœurs / 4 threads, environ 15,85 Gio de RAM utilisable, 7,24 Gio libres au relevé.
Disque C : environ 475,65 Gio, dont 337,52 Gio libres.
Shell SSH par défaut : cmd.exe. PowerShell Windows 5.1.26100.9818 x64 fonctionne en l’appelant explicitement. L’essai initial uname a échoué car l’hôte est Windows ; il n’a entraîné aucune modification.
Outils exécutés : Git 2.54.0.windows.1 ; Python 3.12.10 ; Node v26.12.1 ; gh 2.94.0. OpenSSH/scp/sftp disponibles ; pwsh trouvé via un alias WindowsApps, version/exécution non qualifiées. dotnet absent de PATH et du chemin standard `<CHEMIN_STANDARD_DOTNET>`.
Permissions : le jeton de la session SSH est administrateur. Aucun besoin d’administration n’est démontré pour les futures opérations de routine ; ce compte n’est pas un compte de déploiement à privilèges minimaux.
Stratégie PowerShell distante : CurrentUser RemoteSigned ; autres portées Undefined au relevé. Aucun changement de stratégie réalisé.
Réseau : Wi-Fi Realtek 8821CE actif, liaison 390 Mbps ; Ethernet déconnecté ; interfaces virtuelles Hyper-V/WSL présentes. Cela ne démontre pas le passage du Bluetooth physique vers une VM ou WSL.
Accès/services à préserver : sshd actif automatique ; RustDesk actif automatique ; TermService actif ; WinRM arrêté. Docker Desktop, Ollama et plusieurs Python sont actifs, notamment pour un autre projet. Ports observés : SSH et RDP, ainsi que des applications existantes ; numéros applicatifs et inventaire réseau complet conservés uniquement en local. Aucun port n’est réservé au futur projet à ce stade.
Une session utilisateur RDP active a été constatée ; aucune interaction avec elle.

Chemins : `<RACINE_PROJETS>` existe, appartient au compte distant, et les utilisateurs authentifiés disposent notamment de droits Modify hérités. Une racine dédiée `<RACINE_PROJET>` est plausible mais n’a pas été créée. Pour secrets/état, préférer un emplacement privé du compte et vérifier les ACL exactes avant usage. Les droits d’écriture n’ont pas été éprouvés par création de fichier.
Aucun clone Mousse-controler trouvé dans les racines et profondeurs inventoriées. Plusieurs clones d’autres projets existent ; ils n’ont été ni modifiés ni synchronisés. Absence globale de clone non démontrée hors de ce périmètre.
git ls-remote distant vers le dépôt officiel fonctionne et retourne le SHA 1527797… : lecture GitHub qualifiée, capacité de push et gestion d’identifiants non recherchées.

## 4. Bluetooth : preuves et limites de faisabilité

Mini-PC : Realtek USB VID_0BDA/PID_C821, PnP OK, pilote 1.1061.2312.2501 (date brute conservée dans l’inventaire). Le modèle commercial exact et la version radio Bluetooth ne sont pas déduits du seul identifiant USB.
Commande : lecture WinRT BluetoothAdapter.GetDefaultAsync() puis IsCentralRoleSupported, IsPeripheralRoleSupported, IsLowEnergySupported, IsClassicSupported. Code exact : evidence/Read-BluetoothCapability.ps1.
Résultat sur les deux PC : quatre indicateurs à true. Preuves : evidence/mini-pc-bluetooth-capability.txt et evidence/windows-bluetooth-capability.txt.
Cette lecture n’a créé aucun serveur GATT, démarré aucune publicité ou recherche BLE, effectué aucun appairage et émis aucun rapport HID.

Conclusion : prérequis BLE périphérique annoncé favorable sur le mini-PC ; aucun NO-GO matériel établi. La faisabilité HID native Windows reste NON QUALIFIÉE. Inconnues : création effective du service HID 0x1812, Report Map, notifications, permissions applicatives, appairage/bonding, reconnaissance souris native par la cible, contexte SSH vs session interactive, maintien de l’émission après déconnexion SSH, reconnexion et arrêt sûr.

Sources primaires consultées le 19 novembre 2026 :

- Microsoft BluetoothAdapter.IsPeripheralRoleSupported : https://learn.microsoft.com/en-us/uwp/api/windows.devices.bluetooth.bluetoothadapter.isperipheralrolesupported?view=winrt-28000
- Microsoft serveur GATT : https://learn.microsoft.com/en-us/windows/apps/develop/devices-sensors/gatt-server
- Exemple Microsoft VirtualKeyboard : https://github.com/microsoft/BluetoothLEExplorer/blob/master/BluetoothLEExplorer/BluetoothLEExplorer/Models/VirtualKeyboard.cs
- Profil Bluetooth SIG HOGP : https://www.bluetooth.com/specifications/specs/hid-over-gatt-profile/

Microsoft fournit des API serveur GATT et un exemple HID clavier. Ce sont des indices techniques pour étudier une souris, pas une preuve sur ce matériel. La documentation serveur GATT réserve certains services au système, dont Device Information ; vérifier les conséquences pour le profil retenu. Le support du rôle périphérique ne certifie pas la conformité HOGP.

## 5. Analyse des accès distants

OpenSSH : solution recommandée, déjà opérationnelle, authentification par clé et identité hôte vérifiée. Exécution non interactive et collecte stdout/stderr démontrées. Prévoir PowerShell explicite car le shell par défaut est cmd.exe ; ne pas envoyer de commandes Linux.
SFTP : test en lecture seule avec @('pwd','ls','quit') | sftp -b - mini-pc-backend ; succès, répertoire distant `<REPERTOIRE_UTILISATEUR>`. Preuve evidence/remote-access.txt. Upload, download avec hash et nettoyage réversible NON EXÉCUTÉS pour rester dans le diagnostic distant en lecture seule ; J1 n’est donc pas complet.
RDP/RustDesk : recours interactif existant pour les problèmes de session et la récupération ; ils ne remplacent pas les scripts reproductibles. Aucune nouvelle connexion graphique ouverte.
WinRM : arrêté, pas de motif pour l’activer puisque SSH répond au besoin. SMB et un nouvel agent de déploiement n’apportent aucun bénéfice établi ici.

## 6. Proposition de synchronisation et de déploiement — non implémentée

Transport : OpenSSH Windows natif, SFTP pour artefacts et journaux ; configuration d’hôte et clés hors Git. Conserver le contrôle strict d’identité. Ne pas distribuer une clé GitHub de développement au mini-PC : la lecture distante du dépôt fonctionne déjà ; un artefact poussé depuis le poste local évite de nouveaux secrets distants.

Organisation proposée sous une racine dédiée autorisée : source/ optionnel, releases/`<SHA>`-<hash-artefact>/, logs/, state/, staging/. Les sources, exécutables et données ne partagent pas le même dossier. Aucun de ces chemins n’a été créé sur le mini-PC.

Cycle proposé :

1) doctor : identité, versions, droits effectifs, espace, chemins résolus, processus/ports, absence de déploiement concurrent, état Git distant s’il existe. Refuser tout chemin inattendu et tout clone sale, sans nettoyage automatique.
2) sync --ref `<SHA>` --dry-run : vérifier l’objet Git exact et annoncer les opérations. Construire localement un artefact depuis ce commit, sans fichiers non suivis ; manifeste avec SHA Git complet, dépendances verrouillées, empreinte SHA-256 et identifiant d’opération. Une empreinte identifie le contenu mais ne remplace pas l’authentification du transport.
3) sync : transférer en staging, vérifier hash et manifeste, puis finaliser la release isolée. Si le même identifiant existe avec un hash différent, échouer ; si identique et complet, réutiliser. Si un clone source distant devient utile, fetch puis préparer un checkout isolé du SHA, sans pull aveugle ou reset de travaux.
4) deploy : acquérir un verrou exclusif à création atomique ; traiter les verrous abandonnés par contrôle d’état, pas par suppression aveugle. Préparer la release avant arrêt de la version précédente. Journaliser previous/candidate ; effectuer une activation contrôlée, sans présumer des droits de création de liens symboliques Windows. Ne pas affirmer que plusieurs écritures de manifestes forment une transaction atomique.
5) lancement : exécution à la demande, sans nouveau service persistant. Qualifier préalablement le contexte de session exigé par WinRT Bluetooth et la survie à la déconnexion SSH. Ne pas promettre un lancement matériel fiable sous SSH avant cette preuve.
6) status/test : PID et heure de création du processus, release/hash/SHA réellement chargés, santé bornée sur loopback et résultat des tests autorisés. Un nom de dossier ou git rev-parse seul ne prouve pas la version active. Séparer tests simulés, état API et preuve HID matérielle.
7) logs/stop : rapatrier stdout/stderr et journaux expurgés avec codes de sortie et horodatage ; arrêt applicatif prioritaire puis éventuelle terminaison du seul PID validé après délai. La déconnexion du canal ne doit pas laisser une file HID active sans expiration ; mécanisme d’arrêt local indépendant à prévoir.
8) rollback : si santé échoue, arrêter la candidate, réactiver et vérifier la précédente ; conserver les preuves et retourner FAIL même si restauration réussie. Au premier déploiement, absence de version précédente = arrêt sûr, pas faux succès de rollback.

L’API future écouterait loopback avec authentification. Un tunnel SSH ponctuel pourrait permettre les tests locaux sans ouvrir de nouveau port LAN, après qualification. Secrets hors artefacts et logs. Les ACL actuelles de `<RACINE_PROJETS>` sont larges : une restriction ou un compte dédié serait une modification système à soumettre, pas une action de ce mandat.

Cas à tester ensuite : réexécution identique, concurrence, réseau interrompu à chaque phase, espace insuffisant, artefact incomplet, mauvais SHA, clone sale, santé en échec, processus recyclé, premier déploiement et échec du rollback. Aucun service de déploiement ni script complet de cette chaîne n’a été développé.

## 7. Solutions HID et outils recommandés

Windows natif BLE/HOGP : piste prioritaire cohérente avec les deux indicateurs périphériques positifs. C# / WinRT et GattServiceProvider offrent une voie directe vers les API documentées et l’exemple Microsoft. SDK .NET et outils Windows adaptés seraient à installer seulement après choix et autorisation ; pas de dépendance ni de version figée avant qualification du modèle de paquet, des capacités Bluetooth et du contexte d’exécution. Le mini-PC pourrait recevoir ultérieurement un exécutable autonome si le modèle retenu le permet.
Python 3.12 déjà présent : utile pour diagnostics ou API ; l’usage en serveur GATT/HID Windows exige une projection WinRT et une bibliothèque réellement compatible à vérifier. Une bibliothèque cliente BLE ne suffit pas à émuler une souris. Node déjà présent n’est pas un critère suffisant pour choisir la pile Bluetooth.
Linux / BlueZ : alternative d’architecture à examiner si la voie Windows échoue. Aucun hôte Linux Bluetooth ni passage USB vers WSL n’est qualifié ; ne pas basculer l’OS, attacher la radio ou introduire une VM durant cette phase.
Module BLE HID externe : alternative de matériel programmable si besoin, soumise à arbitrage séparé ; aucun achat, fournisseur ni composant précis sélectionné.
Bluetooth Classic HID : support Classic annoncé mais émission HID non démontrée et distincte du rôle hôte. Aucun avantage établi sur HOGP dans l’environnement actuel.

Outils immédiats suffisants : Git, OpenSSH, SFTP, PowerShell 5.1 distant et 7 local. Pour les futurs scripts, rester compatible 5.1 ou qualifier explicitement pwsh ; ne pas supposer que son alias est un runtime disponible. Dépendances futures à verrouiller après décision, avec builds et tests simulés reproductibles.

## 8. Réserves, erreurs rencontrées et absence de modifications non autorisées

- J1 : commandes SSH et sorties collectées PASS ; SFTP listing PASS ; transfert aller-retour, écriture dédiée, synchronisation distante, exécution d’une release, santé/stop/rollback NON EXÉCUTÉS.
- J2 : indicateurs WinRT favorables ; preuve d’émulation HID NON EXÉCUTÉE.
- Identité SSH vérifiée contre la confiance existante ; privilèges distants excessifs pour une exploitation minimale.
- Mémoire et stockage locaux disponibles limités pour des builds lourds ; pas de mesure d’endurance.
- Services et sessions existants observés ; aucune interruption, installation, ouverture de port, modification Bluetooth, stratégie PowerShell ou configuration SSH.
- Échec de citation Linux uname sur l’hôte Windows, erreur initiale de guillemets SSH, puis limite Windows de longueur avec EncodedCommand : corrigés en transmettant les scripts diagnostics sur stdin. Les scripts n’ont pas été copiés sur le mini-PC.
- Lancement local Windows PowerShell avec -File refusé par la politique effective de ce processus ; la lecture via stdin a fonctionné. Les stratégies relevées n’expliquent pas entièrement ce refus : qualifier plus tard la signature/zone du fichier et le contexte de lancement. Aucun Bypass ni changement de politique effectué.
- Quelques caractères accentués distants ont été remplacés lors de la collecte ; résultats numériques et booléens exploitables. Stabiliser UTF-8 dans la future chaîne versionnée.
- Deux inventaires sont des instantanés, sans garantie sur les états futurs. La référence GitHub a évolué pendant le mandat ; toujours refaire les contrôles avant la suite.

## 9. Mandat suivant proposé et éléments de revue

Priorité : faire relire ce rapport et les preuves par ChatGPT, puis préparer un mandat ciblé de qualification J1. Autoriser explicitement une racine distante dédiée et un fichier témoin pour transfert aller-retour avec hash et nettoyage limité à ce témoin. Qualifier les codes d’erreur, délais, contexte PowerShell, état Git, collecte et arrêt d’un processus de test sans HID. Définir ensuite un petit lot de scripts versionnés en branche dédiée et PR Draft, avec dry-run et tests d’échec ; aucun déploiement persistant implicite.

En parallèle de la conception, préparer le protocole J2 : lecture de capacités déjà acquise, puis création GATT/publicité/appairage et enfin événement HID uniquement dans un futur mandat autorisé, en session supervisée avec arrêt effectif. La pile et les éventuelles installations devront être arbitrées avant mise en œuvre.

Corrections documentaires proposées à ChatGPT : refléter Windows 11 Pro, SSH/SFTP existants, contrôleur Realtek et indicateur périphérique positif ; conserver explicitement J1 partiel et J2 non démontré. Mentionner les deux SHA et le checkout local délibérément conservé. Aucune de ces corrections n’a été appliquée par Codex au référentiel officiel.

Fichiers livrés hors Git : ce rapport, deux scripts diagnostics en lecture seule, deux inventaires, deux résultats WinRT, contrôles d’accès, listing SFTP, preuve Git finale. Les inventaires contiennent des métadonnées techniques locales (chemins, identifiants matériels, adresses privées), aucun secret d’authentification ; ils restent locaux et ne sont pas destinés à un commit public sans sélection des extraits utiles.

Retour arrière du mandat : aucun état applicatif distant à restaurer ; seuls le nouveau clone local et les fichiers qualification ont été créés. Aucun fichier préexistant n’a été remplacé. Ne pas supprimer ces preuves avant revue.

## Annexe de publication

L’inventaire des publications, les origines et les exclusions sont dans [MANIFESTE.md](MANIFESTE.md). Le script WinRT publié est une pièce historique, non exécutée durant la publication. Le script d’inventaire large reste local car il collecte des métadonnées exclues. La section historique « fichiers livrés hors Git » décrit la livraison initiale ; seules les éditions sélectionnées du manifeste sont maintenant publiées. MC-INIT-002 n’a pas été commencé.
