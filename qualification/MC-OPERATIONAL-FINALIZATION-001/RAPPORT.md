# MC-OPERATIONAL-FINALIZATION-001 — Rapport consolidé

## Verdict

**PARTIAL.** Tous les travaux indépendants d'une ressource externe ou d'une
autorisation opérationnelle sont terminés. Le code officiel est qualifié dans
un worktree distinct, la version MSIX a été rendue installable comme mise à
jour, les artefacts sont construits, la véritable tâche mini-PC et ses
persistances sont caractérisées, sauvegardées et intégrées au plan de reprise.

Le passage à `READY_FOR_ACTIVATION_DECISION` exige encore la clé privée du
certificat de signature existant. L'état dynamique de la tâche et
`MonOrdinateur` restent inaccessibles dans la sandbox.

## Résultats

- base officielle : `995916c094b9559a307c3f0ac856e9e2dc88d3e4` ;
- commit logiciel qualifié : `0706aa9a86a2a5c2777a099ead1d0cec4b50ebb3` ;
- `full-local` : **PASS**, 274 tests, 136,0 s ;
- version MSIX portée de `1.0.0.2` à `1.0.0.3`, identité et alias inchangés ;
- PositionAgent et MSIX 1.0.0.3 construits et manifestés ;
- tâche `MousseControler-HOGP` statiquement inspectée ;
- configuration réellement utilisée localisée sous `ProgramData` ;
- journal, `.ids` et index capture présents et sauvegardés ensemble ;
- configuration proposée validée sans promotion ;
- aucune installation, activation, tâche, capture, action HID ou fusion.

## Correction apportée

Le package construit depuis le code courant diffère du package installé, mais
le manifeste réutilisait sa version `1.0.0.2`. Une mise à jour MSIX ne doit pas
réutiliser une version avec un contenu différent. Le manifeste passe à
`1.0.0.3`; deux tests protègent l'incrément, l'identité, l'hôte PowerShell et
l'alias d'exécution.

## Décision

La procédure technique est prête. Les décisions humaines résiduelles sont
regroupées dans [DECISIONS-REQUISES.md](DECISIONS-REQUISES.md). Le verdict
`PARTIAL` n'autorise ni installation ni activation.
