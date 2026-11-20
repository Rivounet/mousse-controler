# MC-ROBUSTNESS-R3-001 — tests

## Suite ciblée

```powershell
python -B -m unittest tests.test_r3_robustness -v
```

Couverture C-03 :

- quota presque atteint et dépassement refusé avant écriture ;
- espace disque libre insuffisant ;
- deux téléversements concurrents, un seul admis sous le plafond ;
- index absent, JSON invalide et enregistrement incomplet ;
- PNG, fichier temporaire et index orphelins ;
- écriture interrompue, refus de suppression, redémarrage et retry.

Couverture C-07 :

- échec de création de chacun des trois serveurs ;
- échec de démarrage de chacun des trois threads ;
- échecs simultanés de tous les `shutdown`, `server_close`, du moteur d'actions
  et du contrôleur ;
- thread encore vivant après la borne de join ;
- fermeture répétée idempotente.

Couverture C-08 :

- installation et rollback explicite réussis ;
- pannes injectées en préparation, sauvegarde, remplacement, installation,
  démarrage, vérification et confirmation ;
- panne de restauration répétée et bornée ;
- panne de redémarrage après restauration ;
- blocage d'une nouvelle installation après `RECOVERY_REQUIRED`.

## Non-régression

```powershell
python -B scripts/qualification/run_r0_software_tests.py
```

Le runner inclut R0, R1, R2, R3, les tests applicatifs et les simulations de
déploiement, mais exclut explicitement les sept diagnostics matériels.

## Contrôles statiques

```powershell
python -B -m compileall -q src tests scripts
python -B scripts/generate_api_reference.py --check
git diff --check
```

La syntaxe des scripts PowerShell est analysée par le parseur PowerShell sans
les exécuter contre une tâche réelle. Les résultats finaux figurent dans
`evidence/EXECUTIONS.md`.
