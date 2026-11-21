# Tests R5

## Baseline

Commande :

```powershell
python -B scripts/qualification/qualify.py --profile software
```

Résultat : **PASS**, 269/269 tests, 127,843 s, base
`c5d8ef6bdb06b0fb6295b946d0be578956e35d93`.

## Tests ciblés

```powershell
python -B -m unittest tests.test_trajectory.GeometryTests tests.test_api_catalog -v
```

Résultat : **15/15 PASS**, 9,277 s.

Couverture ajoutée : polygones très fins, concaves, coordonnées négatives,
grandes coordonnées, sommets colinéaires, quasi-dégénérescence, 50 graines par
famille, double exécution reproductible ; doublons de commandes, actions et
événements refusés avant mutation. Les tests existants couvrent génération de
référence, recherche/découverte, authentification et tolérance des paramètres
inconnus.

## Qualification finale

Le résultat final `full-local`, ses builds, versions, durée, exclusions et SHA
qualifié sont ajoutés après exécution sur le commit de code/documentation.

