# Fondations distantes MC-INIT-002

Python 3.12 standard sur le poste local orchestre les clients OpenSSH Windows déjà installés. Les fragments distants utilisent Windows PowerShell 5.1 explicitement, via `-EncodedCommand`, sans modifier le shell SSH ni les stratégies PowerShell. PowerShell 7 peut lancer les commandes ci-dessous. Aucun package supplémentaire requis.

Créer une configuration **locale hors dépôt**, sans secrets : `host` (alias SSH existant), `expected_computer` (nom d’hôte attendu), `root` (racine Windows dédiée se terminant par Mousse-controler), `timeout` (0,5 à 60 secondes). La racine doit avoir été examinée ; une configuration ne constitue pas une autorisation d’écriture. Les comptes, clés et adresses restent dans la configuration SSH existante, hors Git.

```powershell
python -B scripts/remote/remote.py --config <CONFIG_LOCALE> doctor
python -B scripts/remote/remote.py --config <CONFIG_LOCALE> status
python -B scripts/remote/remote.py --config <CONFIG_LOCALE> sync --dry-run --ref <SHA_COMPLET> --repository .
python -B scripts/remote/remote.py --config <CONFIG_LOCALE> test --probe streams
python -B scripts/remote/remote.py --config <CONFIG_LOCALE> test --probe sftp
python -B scripts/remote/remote.py --config <CONFIG_LOCALE> test --probe timeout
python -B -m unittest discover -s scripts/remote -p test_remote.py -v
```

| Opération | État réel |
|---|---|
| doctor | Lecture d’identité, versions, jeton admin, existence racine/parent, lisibilité ACL parent, points de réanalyse, UTF-8. Aucun test d’écriture. |
| status | Même diagnostic ; version/processus/santé applicative explicitement inconnus. |
| sync --dry-run | Plan local déterministe pour un commit complet connu et un arbre propre. Aucun contact distant, artefact ou transfert. Préconditions distantes non vérifiées par ce plan. |
| test streams | Doctor préalable, stdout/stderr Unicode fixes, code distant 37 volontaire. Le CLI retourne 37 : succès du test à interpréter avec le protocole. |
| test sftp | Doctor préalable, commandes pwd/quit seules. La sortie peut contenir un chemin personnel : garder le brut local. |
| test timeout | Doctor préalable, attente distante bornée à 4 secondes, délai client 1 seconde. Le client expire ; l’arrêt immédiat de la commande distante n’est pas garanti. |
| logs, stop, deploy, rollback, sync sans dry-run | Non implémentés ; code 3 / NON_EXÉCUTÉ avant tout appel distant. |

Codes : 0 pour une opération implémentée réussie ; 2 pour erreur locale/transport/précondition, dont délai ; 3 pour interface non implémentée ; code distant de la sonde streams remonté tel quel. Les sorties sont JSON UTF-8. L’identité attendue est contrôlée via SSH à hôte connu et nom de machine ; ce n’est pas une attestation indépendante. Mot de passe et interaction clavier sont désactivés, authentification préférée publickey, aucune mise à jour automatique des clés d’hôte.

Les permissions sont **observées**, pas réduites. Les lectures de chemins recontrôlent les ancêtres ; elles ne verrouillent pas le système de fichiers contre une modification concurrente. Les futures écritures nécessiteront leur propre validation et verrou exclusif. Le budget de délai est par sous-processus, pas global (une sonde inclut doctor puis sa commande). Les diagnostics ne créent pas de répertoire, n’installent rien et ne touchent pas au Bluetooth.

## Préparation du témoin, sans exécution distante

```powershell
python -B scripts/remote/plan_witness.py --config <CONFIG_LOCALE> --output <NOUVEAU_DOSSIER_LOCAL>
```

Cette commande crée uniquement un témoin local UTF-8, son hash, des commandes PowerShell et deux lots SFTP **locaux** pour examen. Elle ne lance aucun client réseau. Le plan contient des chemins réels : ne pas le committer. `build_plan` et les tests couvrent sa structure ; les commandes de mutation sont **préparées et non qualifiées**.

Après autorisation distincte : vérifier identité/hôte et tous les chemins, exécuter le précontrôle, créer le dossier unique sans réutiliser un dossier existant, transférer le témoin, comparer son hash distant, télécharger et comparer le hash local, puis seulement supprimer le témoin si son hash est inchangé. En cas d’erreur, préserver les données inattendues et les preuves. Les répertoires créés sont enregistrés ; aucun nettoyage récursif n’est prévu. Le témoin local et son retour doivent rester disponibles pour revue.

Le processus de test préparé attend 120 secondes puis s’arrête de lui-même. Son arrêt anticipé exige PID, date de création, ligne de commande et exécutable observés, et une nouvelle vérification de l’identité du processus. Le modèle de stop est volontairement incomplet jusqu’à obtention de ces valeurs ; il refuse de s’exécuter en l’état. Ni cette préparation ni les sondes SSH ne prouvent la persistance d’une application BLE après déconnexion.
