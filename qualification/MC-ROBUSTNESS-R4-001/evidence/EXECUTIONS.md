# MC-ROBUSTNESS-R4-001 — Exécutions expurgées

Date locale : 21 novembre 2026. Machine : Windows 11 x64. Aucun chemin de clé,
secret, certificat privé ou donnée de production n'est publié.

## Baseline

```text
base: 54c24aa197e2075709b71311fa7e5c1b621077a0
commande: python -B scripts/qualification/run_r0_software_tests.py
résultat: PASS — 263/263, expected failures 0, matériel exclu 7
durée mesurée des suites: 109,985 s + 44,745 s + 0,007 s
```

## Contrôles ciblés R4

```text
tests de sûreté orchestrateur: 6/6 PASS — 3,330 s
tests R2 après séparation des budgets: 18/18 PASS — 8,799 s
build PositionAgent préliminaire: PASS
build PairingTool: PASS
build MouseWitness: PASS
création paquet HOGP non signé: PASS — aucune installation
```

Deux exécutions `full-local` antérieures ont rendu `FAIL` sur le démarrage du
processus simulé du test
`test_button_timeout_is_unknown_quarantined_and_not_replayed`. Le test isolé a
passé deux fois en 0,323/0,324 s. L'analyse a montré que le budget de démarrage
de 300 ms, pertinent pour le test dédié au startup, était réutilisé dans ce cas
de timeout de commande. Les échecs n'ont pas été convertis en succès ; ils ont
conduit à séparer les budgets de test, sans modification applicative.

## Qualification finale

```text
SHA qualifié: 72546bdd22ccbd269cacf112ffb3a82d30d38b64
commande: python -B scripts/qualification/qualify.py --profile full-local
verdict: PASS
tests: 269/269 PASS
software-tests: 125,219 s
python-compilation: 0,922 s
api-reference-check: 0,547 s
powershell-syntax: 0,890 s — 22 scripts, aucun exécuté
position-agent-build: 2,235 s
total: 131,750 s
diagnostics matériels exclus: 7
```

Artefact principal :

```text
nom: artifacts/PositionAgent/PositionAgent.exe
taille: 28672 octets
SHA-256: 072437c98910b0f0736c961d75689623e0c724ac61d000609d422a896aacffa4
Roslyn: 4.14.0-3.26424.7 (a528c90a)
Windows SDK: 10.0.26100.0
installé: false
```

Les logs bruts restent dans le dossier `out/` ignoré par Git. Cette preuve ne
publie que les résultats nécessaires et expurgés.
