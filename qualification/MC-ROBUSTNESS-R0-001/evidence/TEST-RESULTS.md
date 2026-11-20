# Preuves de qualification logicielle

Date : 2026-11-20, fuseau Europe/Paris.

## Avant ajout des caractérisations

- cœur : 114 tests, 4,096 s, PASS ;
- remote/déploiement simulé : 69 tests, 34,172 s, PASS ;
- contrats non matériels : 5 tests, 0,008 s, PASS ;
- total : 188/188 PASS ;
- diagnostics matériels exclus : 7.

## Caractérisations ciblées R0

- commande : `python -B -m unittest tests.test_r0_characterization -v` ;
- 18 tests, 1,929 s, PASS ;
- 9 noms `current_defect` reproduisent explicitement une réserve connue ;
- 0 test attendu/ignoré dans cette suite dédiée ;
- aucun accès externe ni matériel.

## Résultat agrégé final

- cœur + caractérisations R0 : 132/132 PASS, 6,077 s ;
- remote/déploiement simulé : 69/69 PASS, 34,360 s ;
- contrats non matériels : 5/5 PASS, 0,008 s ;
- **total : 206/206 PASS**, 0 échec attendu, 7 diagnostics matériels exclus ;
- temps des trois runners : 40,445 s, hors inventaire/build/documentation.

## Build et syntaxe

- 21 fichiers PowerShell analysés, 0 erreur ;
- 3 exécutables C# compilés avec avertissements traités comme erreurs ;
- 3 builds réussis ; répertoire temporaire supprimé (`TempRemoved=True`).

## Lecture du résultat

Le succès des tests `current_defect` atteste la stabilité de la reproduction, pas
la résolution. Les portes futures sont détaillées dans `DEFECT-MATRIX.md` et
`R1-R5-CRITERIA.md`. Le résultat ci-dessus provient de
`scripts/qualification/run_r0_software_tests.py` après correction du chemin
temporaire du runner.

## Incident d'outillage R0 résolu

La première invocation du runner agrégé utilisait le répertoire temporaire du
bac à sable, dont le chemin dépassait le budget Windows testé par
`ReleaseStore`. Résultat : 23 erreurs `WINDOWS_PATH_BUDGET_EXCEEDED` dans la
suite remote, alors que celle-ci avait réussi à 69/69 avec un chemin court.
Le runner utilise désormais un sous-répertoire temporaire aléatoire sous
`<racine-workspace>/t`, supprimé automatiquement. Aucun code applicatif ni test
de production n'a été modifié pour masquer la garde de longueur.
