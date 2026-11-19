# MC-INIT-003 — préparation locale et modèle de releases

Cette interface complète MC-INIT-002 sans modifier son CLI ni ses 31 tests. Python 3.12 et Git existants suffisent. **Aucun transport de release, lancement Windows ou rollback distant n’est livré.** Les commandes `model` manipulent un vrai système de fichiers local avec un moteur applicatif explicitement simulé ; elles ne lancent aucun processus et n’ouvrent aucune connexion réseau.

## Artefact depuis un commit exact

```powershell
python -B scripts/remote/deployment.py sync --repository . --ref <SHA_40> --include scripts/remote --config <CONFIG_LOCALE> --dry-run
python -B scripts/remote/deployment.py sync --repository . --ref <SHA_40> --include scripts/remote --config <CONFIG_LOCALE> --output <NOUVEAU_BUNDLE_LOCAL>
```

Le fichier de configuration garde le format MC-INIT-002, hors Git. Les répertoires de bundle sont hors du dépôt source ; leur parent doit déjà exister. L’état Git doit être propre (index, fichiers suivis et non suivis). Des fichiers ignorés peuvent exister : seuls les blobs suivis du SHA demandé et explicitement sélectionnés sont lus, jamais leurs copies de travail. Un SHA ancien peut être préparé depuis un checkout plus récent propre.

Sélection : préfixes relatifs explicites répétés via `--include`, sans glob. Chaque préfixe doit sélectionner au moins un fichier. Refus des liens Git/sous-modules, collisions de casse, chemins Windows dangereux, fichiers de clés/configuration connus et marqueurs de secrets identifiés. Cette détection ciblée ne remplace pas une revue du contenu autorisé. Fichiers ASCII de chemin, taille maximale 32 Mio par fichier et 128 Mio de contenu par artefact.

Le ZIP stocké sans compression a un ordre, une date et des attributs fixes. Les octets Git sont conservés, y compris leurs fins de ligne ; le mode Git original est enregistré dans le manifeste, mais les attributs du ZIP sont normalisés. Le manifeste externe contient SHA Git, hash de l’archive, sélection et taille/hash/mode de chaque fichier. Refaire la préparation donne les mêmes octets. Réutiliser un bundle existant exige une égalité intégrale ; un bundle incomplet ou différent est préservé et refusé.

Le dry-run calcule réellement fichiers et empreinte en mémoire, sans créer de bundle. Il affiche la cible de staging envisagée et les contrôles distants encore NON_EXÉCUTÉS. `sync` prépare **localement** le bundle ; `remote_synced=false` reste explicite. Les chemins de sa sortie et de la configuration restent privés. Un hash garantit l’intégrité d’un contenu, pas son auteur : la chaîne de confiance Git/revue/SSH reste nécessaire.

## Modèle local de releases

Choisir une racine locale neuve dont le nom final est exactement `mousse-controler-sim`. Le marqueur de simulation et les répertoires sont créés par `init` ; un répertoire existant arbitraire n’est pas importé. Les liens/jonctions sont refusés dans les ancêtres.

```powershell
python -B scripts/remote/deployment.py model --root <SANDBOX_LOCAL> init
python -B scripts/remote/deployment.py model --root <SANDBOX_LOCAL> ingest --bundle <BUNDLE_LOCAL>
python -B scripts/remote/deployment.py model --root <SANDBOX_LOCAL> deploy --release <SHA_40>-<HASH_64>
python -B scripts/remote/deployment.py model --root <SANDBOX_LOCAL> status
python -B scripts/remote/deployment.py model --root <SANDBOX_LOCAL> stop
python -B scripts/remote/deployment.py model --root <SANDBOX_LOCAL> rollback
python -B scripts/remote/deployment.py model --root <SANDBOX_LOCAL> recover
```

Structure : source facultative, staging par opération, releases `<SHA_40>-<HASH_64>` contenant bundle et fichiers vérifiés, state, logs. Les releases ne sont jamais modifiées ou supprimées par le moteur. Intégrité recontrôlée à l’ingestion, avant activation et avant restauration. Une release identique est réutilisée ; une release altérée ou contenant des éléments non listés est refusée. Les étapes incomplètes restent en staging pour diagnostic. Le budget conservateur de chemin Windows est 240 caractères, vérifié aussi sur la destination finale, sans supposer l’activation des chemins longs.

`state/active.json` est l’autorité unique contenant **active et previous dans le même enregistrement**, ainsi que phase et identité du processus modèle. Pas de paire de pointeurs à remplacer séparément ; pas de lien symbolique. `runtime-model.json` stocke uniquement des identités fictives, sans lien avec les PID Windows. `logs/events.jsonl` journalise les intentions et résultats. Les données d’exécution sont hors releases.

Un verrou exclusif par dossier protège aussi les lectures de status contre les écritures coopérantes. Le propriétaire est vérifié avant suppression du seul marqueur de verrou puis du dossier vide. Aucun verrou abandonné n’est effacé automatiquement : après arrêt brutal laissant un verrou, l’opérateur doit examiner l’état et le propriétaire avant une récupération séparément autorisée. La récupération `recover` traite l’état pending/recovery_required **après** disponibilité du verrou ; elle ne contourne pas un verrou existant.

Activation : intention persistée, arrêt de l’ancienne identité, démarrage modèle de la candidate, santé, remplacement atomique du snapshot. En cas d’échec, la candidate identifiée est arrêtée, l’ancienne release vérifiée puis relancée si nécessaire. L’opération initiale reste FAIL même si restauration réussie. Si la restauration échoue, état recovery_required et refus d’un nouveau deploy. Sans précédente, un échec de première activation laisse le modèle inactif. Le rollback explicite active la précédente et conserve la version quittée comme précédente.

Des identifiants d’opération persistés permettent de retrouver un démarrage modèle interrompu avant publication de son état et de rejouer une restauration sans doublon. La journalisation n’est pas une transaction multi-fichiers ; le snapshot indique l’état à examiner après interruption. Remplacements et fsync de fichiers ne constituent pas une garantie d’endurance contre une panne physique du disque. Les verrous protègent les outils coopérants, pas un administrateur hostile remplaçant des chemins entre deux appels. Pas de modification d’ACL ni de garantie d’immutabilité matérielle : les altérations sont détectées par hash.

## Tests sans réseau

```powershell
# Si TEMP est trop long sous Windows, créer un répertoire local court hors dépôt :
$env:MC_TEST_TMP = '<REPERTOIRE_LOCAL_COURT_EXISTANT>'
python -B -m unittest discover -s scripts/remote -p 'test_*.py' -v
```

Les nouveaux tests utilisent des dépôts Git temporaires réels et un stockage local réel, puis injectent erreurs, interruptions et santé simulées. Les 31 tests MC-INIT-002 restent inchangés. Aucun test ne lance d’application réelle ou ne contacte le mini-PC. Les futures opérations distantes restent à implémenter et à qualifier après autorisation explicite ; voir le protocole dans le rapport MC-INIT-003.
