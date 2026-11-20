# Procédures MC-MOUSE-ACTIONS-001

## Construire et tester

```powershell
$env:MC_TEST_TMP = 'C:\chemin-court\mc-tests'
python -m unittest discover -v
powershell.exe -NoProfile -File .\scripts\build\Build-PositionAgent.ps1
powershell.exe -NoProfile -File .\scripts\build\Build-MouseWitness.ps1
```

## Contrat d'action

`action_submit` reçoit `action_id` facultatif et `action`. Exemples de `kind` :
`click`, `press`, `release`, `hold`, `drag`, `move_with_buttons`, `scroll`,
`move_relative`, `move_to`, `wait`, `wait_command`, `sequence`. `click.count`
vaut 1–20 ; les boutons sont `left/right/middle/back/forward` ou un masque 1–31.
La roulette continue exige durée ≤ 30 s et au plus 500 rapports. Les commandes
de contrôle sont `action_status/list/cancel/pause/resume/continue/events`.

Une politique `capture` peut contenir `before`, `after`, `retention_seconds` et
`timeout_seconds`; elle est refusée sur une attente et héritée uniquement par
les enfants souris d'une séquence. `error_policy` vaut `stop` (défaut), `retry`
ou `continue`. `retry` n'est effectif que sur une opération explicitement sûre.

WebSocket : `ws://127.0.0.1:<event_port>/v1/events`, en-tête
`Authorization: Bearer <jeton DPAPI déprotégé>`, sous-protocole applicatif
`mousse.actions.v1`. Chaque message contient `event_id`, `event_type`,
`emitted_at_ms` et l'instantané `action`.

## Cible et rollback

Construire les deux EXE puis placer avec les scripts
`Update-InteractivePositionAgent.ps1` et
`Start-InteractiveMouseQualification.ps1` dans un staging vérifié. Le staging
doit appartenir au profil interactif autorisé ; ne pas utiliser un dossier créé
par un autre compte sous `C:\Windows\Temp` ni en modifier les ACL. Depuis SSH
autorisé, le script crée une tâche temporaire interactive limitée, vérifie son
processus et permet un nettoyage explicite :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\Start-InteractiveMouseQualification.ps1 -Action Start

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\Start-InteractiveMouseQualification.ps1 -Action Status

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\Start-InteractiveMouseQualification.ps1 -Action Stop
```

Le script met à jour uniquement l'exécutable de la tâche connue, refuse une
tâche témoin homonyme non conforme et ouvre la fenêtre en session console. Une
session SSH directe reste en session 0 et n'est pas une preuve de visibilité.

Avant toute émission, annoncer la durée de prise de souris et attendre l'accord
explicite. Utiliser ensuite les bornes fraîches retournées par le témoin :

```powershell
$env:PYTHONPATH = "$PWD\src"
python .\scripts\qualification\qualify_mouse_actions_runtime.py `
  --config C:\ProgramData\MousseControler\controller.json `
  --phase captures --bounds <X> <Y> <LARGEUR> <HAUTEUR> `
  --evidence-directory .\qualification\MC-MOUSE-ACTIONS-001\evidence
```

La phase `emergency` doit être exécutée en dernier. Redémarrer ensuite la tâche
contrôleur, vérifier `subscribed=True`, `buttons=0`, aucune action en attente et
aucun rejeu. Pour restaurer l'agent cible :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\Update-InteractivePositionAgent.ps1 -Action Rollback
```

Ne jamais publier `agent.json`, journaux bruts, coordonnées, comptes, chemins
privés ou captures plein écran. Les PNG de preuve conservés sont recadrés sur la
seule surface témoin et placés exclusivement dans le dossier `evidence/` du
mandat dans le dépôt. Supprimer chaque capture source via `capture_delete`,
vérifier son absence, fermer la fenêtre témoin, supprimer la tâche et le
staging, puis annoncer « souris libre ». Vérifier enfin transport abonné,
boutons zéro et position fraîche.
