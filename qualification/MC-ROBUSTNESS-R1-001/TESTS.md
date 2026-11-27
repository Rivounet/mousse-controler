# MC-ROBUSTNESS-R1-001 — tests

## Suite ciblée

Commande :

```powershell
$env:PYTHONPATH = 'src'
python -B -m unittest tests.integration.test_r1_safety tests.unit.test_trajectory -v
```

Couverture ajoutée :

- 18 combinaisons de six actions bouton et trois politiques d'erreur ;
- séquence multi-action avec `continue` après effet ambigu ;
- arrêt durant attente et pause du séquenceur historique ;
- arrêt global répété, concurrent et partiellement défaillant ;
- fermeture avec action suspendue, `hold` déjà émis, file pleine et erreur
  d'arrêt contrôleur ;
- course soumission/fermeture ;
- persistance des états et anti-rejeu après redémarrage.

Correctif de revue :

- interleaving déterministe `hold` : attente terminée, arrêt contrôleur,
  tentative de relâchement refusée ;
- résultat `UNKNOWN` et quarantaine pour `stop`, `continue` et `retry` ;
- même garantie pour un `hold` enfant d'une séquence `continue` ;
- identifiant persistant non rejouable après reconstruction du registre ;
- chemins nominaux `drag` et `move_with_buttons` inchangés.

## Suite logicielle complète R0

Commande :

```powershell
python -B scripts/qualification/run_r0_software_tests.py
```

Le runner exclut par construction :

- 3 diagnostics Windows susceptibles de toucher la radio ;
- 4 diagnostics de session/cible ;
- tout HID, capture réelle, SSH ou accès à `MonOrdinateur`.

Les résultats finaux sont consignés dans
[`evidence/EXECUTIONS.md`](evidence/EXECUTIONS.md).

## Interprétation

`UNKNOWN` est un résultat de sûreté attendu lorsqu'un effet bouton a pu être
émis. `release_confirmed=false` signifie que `release_all` a été tenté sans
revendiquer une observation physique indépendante. `CANCELLED` est réservé aux
actions non commencées ou interrompues sans effet ambigu.
