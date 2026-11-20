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
`Start-InteractiveMouseQualification.ps1` dans un staging vérifié. Depuis la
session visible de MonOrdinateur :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\Start-InteractiveMouseQualification.ps1
```

Le script met à jour uniquement l'exécutable de la tâche connue et ouvre la
fenêtre témoin. Pour restaurer :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  .\Update-InteractivePositionAgent.ps1 -Action Rollback
```

Ne jamais publier `agent.json`, journaux bruts ou PNG. Fermer la fenêtre témoin
à la fin. Vérifier ensuite transport abonné, boutons zéro, position fraîche et
absence de fichier image dans l'arbre Git.
