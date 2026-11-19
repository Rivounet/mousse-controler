# MC-INIT-002 — qualification du canal distant

19 novembre 2026 — rapport Codex pour revue indépendante ChatGPT. Statut proposé : fondations qualifiées avec réserves ; aucune clôture de jalon déclarée par Codex.

## 1. Git initial et publication

Début : branche docs/mc-init-001-evidence au SHA `8886cab1230039add8e2712a5114c4e312c0f49b`, arbre propre et aucun commit non publié détecté. Main local était à `86ed1088bc1e2ae7984c4c4ccfd0bb0af8755b02`. Fetch puis contrôle d’ascendance ont permis son fast-forward vers `6033e0d99e391528f3c131818dde1a19dd32f0f8`. Branche de travail : `feat/mc-init-002-remote-qualification`, créée depuis ce main. PR #1 vérifiée Draft et non fusionnée ; ses preuves n’ont pas été intégrées à cette branche.

Les documents officiels ont été lus, sans édition. Seuls scripts/remote et qualification/MC-INIT-002 sont ajoutés. Le SHA de tête publié est fourni par la PR Draft et le compte rendu ; il ne peut pas être inclus dans son propre contenu. Le [plan de synchronisation](evidence/sync-dry-run.json) identifie précisément le commit local réellement utilisé pour ce test de plan, qui précède les corrections du processus. Aucun SHA n’a été déployé sur le mini-PC.

## 2. Canal distant réellement testé

Python 3.12 local pilote les clients OpenSSH Windows ; Windows PowerShell 5.1 distant est invoqué explicitement derrière cmd.exe. Pas de paquet, agent ou modification système ajouté. Les scripts distants transitent par EncodedCommand ; aucun fichier script n’est installé sur l’hôte.

| Vérification | Verdict | Observation |
|---|---|---|
| Identité et clé | PASS | Hôte attendu comparé ; StrictHostKeyChecking=yes, UpdateHostKeys=no ; authentification publickey, mots de passe et interaction clavier désactivés |
| Exécution non interactive | PASS | -T, BatchMode et -NonInteractive ; doctor JSON valide |
| UTF-8 | PASS | « été — témoin » et flux accentués restitués sans perte |
| stdout/stderr/code | PASS | Sonde volontaire : stdout « été stdout », stderr « échec stderr », code 37 exact |
| Timeout client | PASS | Délai client 1 seconde pour attente distante bornée à 4 secondes ; erreur explicite CLIENT_TIMEOUT |
| Arrêt immédiat de la commande après timeout | NON_EXÉCUTÉ | Le client ne garantit pas la fin immédiate du processus distant ; la sonde s’achève au plus tard après son attente bornée |
| SFTP lecture seule | PASS | pwd/quit, code 0 ; chemin du profil expurgé |
| Racine et permissions | PASS avec réserve | Racine initialement absente, parent lisible, aucun ancêtre reparse point observé ; jeton SSH administrateur |

Preuves : [SSH et encodage](evidence/ssh-readonly.json). L’identité vérifiée est celle déjà approuvée dans known_hosts ; aucune nouvelle attestation indépendante. Les erreurs PowerShell peuvent arriver en CLIXML sur stderr : conservation brute locale, code de retour contrôlé ; aucun parseur général de CLIXML n’est livré.

## 3. Architecture et droits minimaux

Le chemin exact de projet proposé et approuvé a été conservé dans le protocole local d’autorisation ; la publication utilise `<RACINE_AUTORISÉE>` pour éviter de publier des chemins privés. Organisation proposée, non déployée :

```text
<RACINE_AUTORISÉE>/
    source/       copie Git facultative, sans travaux écrasés
    staging/      réception temporaire et vérification de hash
    releases/     artefacts immuables par SHA et hash
    state/        manifestes actif/précédent et futur verrou
    logs/         sorties et résultats, sans secrets
```

Seuls la racine, staging et un dossier témoin unique ont été temporairement créés après accord, puis retirés s’ils étaient vides. Source, releases, state et logs n’ont pas été créés.

Les ACL héritées ont été lues après création, sans modification. Elles accordent notamment Modify aux utilisateurs authentifiés ; le compte actuel est administrateur. Un futur compte standard dédié, sans privilèges administratifs courants, avec droits limités à la racine du projet et identité SSH distincte serait préférable. Sa création et toute restriction d’ACL nécessitent un mandat séparé. La simple lisibilité d’ACL ne prouve pas un droit d’écriture ; ici seule la création bornée autorisée l’a éprouvé pour le compte actuel.

Transport retenu : SSH/SFTP existants. Pas de WinRM, port LAN, service supplémentaire ou clé GitHub à distribuer. La synchronisation future viserait un SHA complet et un artefact haché, préparé en staging avant activation. Le verrou exclusif, les manifestes actif/précédent, la santé applicative et le rollback sont à implémenter ultérieurement ; ils ne sont pas qualifiés par ce mandat.

## 4. Scripts et opérations implémentées

Voir le [guide technique](../../scripts/remote/README.md).

- `remote.py doctor` : diagnostic distant en lecture seule, contrôle d’identité/JSON/UTF-8, chemins et points de réanalyse, ACL parent, token administrateur et versions.
- `status` : diagnostic d’environnement ; active_sha=null et santé applicative explicitement NON_EXÉCUTÉ, sans prétendre lire un service inexistant.
- `sync --dry-run` : plan **local** pour un commit complet connu et un arbre propre ; aucun artefact ni contact distant. Répétition déterministe testée ; ce n’est pas une synchronisation exécutée.
- `test --probe streams|sftp|timeout` : sondes fixes en lecture seule, avec doctor préalable.
- `verify_transfer` : primitive locale de contrôle de résultat et SHA-256, utilisée dans la qualification ; refuse un transfert en erreur même si les octets reçus semblent corrects.
- `plan_witness.py` : génération **locale** du témoin, de son hash et des commandes préparées ; aucune opération réseau lancée par le générateur. Les modèles stop et nettoyage nécessitent les identités observées, et refusent une identité manquante.
- `logs`, `stop`, `deploy`, `rollback` et `sync` sans dry-run : interfaces explicitement non implémentées, code 3 / NON_EXÉCUTÉ avant tout appel distant. Le stop du témoin ci-dessous est une procédure de qualification spécifique, pas un stop applicatif général.

Paramètres réels dans une configuration locale hors Git ; aucune clé, compte ou adresse dans le code. Chemins absolus dédiés exigés, pas de UNC, traversée, flux alternatif, métacaractère ou racine disque. Les fragments distants compatibles 5.1 sont encodés, sans passer par un shell local. Le timeout tue/récupère le client local ; son budget est par sous-processus. Les appels en lecture seule n’ont pas besoin de verrou d’écriture. La future mutation concurrente exigera des contrôles supplémentaires contre les courses de fichiers ; le contrôle des liens n’est pas un verrou.

## 5. Tests locaux

Commande : `python -B -m unittest discover -s scripts/remote -p test_remote.py -v`.

**31 tests PASS** ; [sortie complète](evidence/tests-local.txt). Mocks SSH/SFTP sans réseau : erreurs et refus d’accès, code 255, mauvais UTF-8/JSON/hôte, délai, exécutable absent, chemins interdits et reparse points. Transfert interrompu et hash incorrect refusés. Plan de synchro stable sans réseau, SHA inconnu/arbre sale refusés, mutation non implémentée refusée. Générateur de témoin sans effets réseau ; création exclusive, suppression du seul témoin protégée par hash, stop conditionné à l’identité. Un vrai sous-processus **local** confirme flux UTF-8/code 37 et timeout, sans réseau. Les tests ne simulent pas une chaîne deploy/rollback complète qui n’existe pas.

## 6. Transfert et processus réels après autorisation

Un point d’arrêt a présenté à l’utilisateur les chemins exacts, commandes et risques, puis son accord explicite a autorisé uniquement ce test. Le protocole et son accord détaillé restent locaux ; leur portée est résumée ici.

Témoin UTF-8 de 63 octets, identifiant unique, SHA-256 `1bf9a33ba5c8b4a59dabb33a09541316eb9499b76aaa6b07cb9e74c2df92f99a`. Création exclusive de trois répertoires initialement absents, lecture des ACL ; une tentative de réutilisation du dossier a échoué avec code 1 attendu, sans écrasement. Upload SFTP code 0, hash distant identique, download code 0, égalité du hash et des octets. Puis nouvelle vérification de chemin/hash, suppression du seul témoin, suppression des seuls répertoires créés restés vides, sans récursivité.

Processus témoin : Windows PowerShell masqué, sans port ni Bluetooth, attente maximale 120 secondes. Premier essai : ALREADY_EXITED avant stop, donc arrêt contrôlé non démontré ; la fermeture du canal est une explication possible, pas une cause prouvée. Essai dans une session SSH unique : refus intermédiaire de sécurité dû à une comparaison de précisions de dates, puis correction décrite ci-dessous. Dernier essai : ALIVE_CONFIRMED, STOPPED, ABSENT_CONFIRMED, code 0, stderr vide. PID, dates CIM et StartTime, exécutable et commande ont été vérifiés avant le seul arrêt ; identifiants expurgés de la publication.

Preuves : [résultats réels et tentatives](evidence/witness-roundtrip.json), [commandes expurgées](evidence/commandes-temoin.md). Les scripts générés sont versionnés par leur générateur ; leur orchestration de ce test et les sorties brutes restent locales. Ils ne constituent pas un service de déploiement.

## 7. Problèmes et corrections

1. Dates CIM et Get-Process : leurs chaînes n’avaient pas la même précision, produisant un faux refus « PID reused ». La protection a refusé l’arrêt. Le générateur relève désormais séparément CreationDate CIM et StartTime du processus créé ; chaque valeur est comparée à la même API avant arrêt. Les deux contrôles sont conservés.
2. `WaitForExit` renvoyait True sur stdout : le stop avait réussi, mais le validateur de sortie attendait trois marqueurs exactement. La sortie booléenne a été supprimée avec `[void]`, puis le test réel a été rejoué avec succès. Les sorties intermédiaires ne sont pas cachées.
3. Le collecteur initial marquait globalement PASS après ALREADY_EXITED : ce statut ne suffisait pas pour qualifier stop. L’extraction publiée le reclasse explicitement ; le PASS final vient de la preuve complémentaire ALIVE/STOPPED/ABSENT.
4. Encodage : stdout/stderr explicitement UTF-8, décodage strict local ; sorties CLIXML d’erreur conservées localement. Les preuves et scripts de ce lot imposent LF via .gitattributes pour rendre les hashes du manifeste reproductibles dans Git.

## 8. État final, risques et limites

Lecture finale : racine dédiée absente et aucun processus correspondant aux commandes témoins observé. Témoin local et retour conservés avec les preuves brutes. Aucune commande n’a visé une application, session ou service tiers ; aucune installation, ACL, pare-feu, SSH, stratégie PowerShell ou Bluetooth n’a été modifié. Cette conclusion repose sur la portée des commandes et les contrôles ciblés, pas sur une comparaison exhaustive de tout le disque ou de tous les processus.

L’authentification utilise toujours le compte administrateur existant. La présence d’ACL héritées larges nécessite un arbitrage avant exploitation durable. Persistance d’application après déconnexion SSH, statut applicatif, transfert d’artefact par SHA réel, santé, anti-concurrence de déploiement, rollback applicatif, endurance et HID : **NON_EXÉCUTÉS**. Le transfert témoin qualifie l’intégrité du canal pour ce petit fichier, pas la performance de gros artefacts. Aucun mouvement, appairage ou publicité BLE.

## 9. Suite et revue

Soumettre cette PR Draft et son manifeste à ChatGPT ; ne pas fusionner. Les fondations J1 disposent maintenant de preuves réelles de transfert réversible, collecte et arrêt contrôlé dans une même session. La clôture de J1 appartient à la revue indépendante. Définir ensuite un lot ciblé pour la synchronisation par SHA et le modèle de lancement, avec choix de droits et contexte d’exécution ; ne pas commencer automatiquement le développement HID ni un déploiement persistant.

Le [manifeste](MANIFESTE.md) détaille chaque origine, expurgation, fichier local exclu et empreinte publiée.
