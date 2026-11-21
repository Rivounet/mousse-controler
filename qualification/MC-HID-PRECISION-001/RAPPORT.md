# MC-HID-PRECISION-001 — Rapport de correction logicielle

## Verdict attendu et périmètre

Le verdict de ce mandat est `SOFTWARE_FIX_QUALIFIED`. Il ne constitue pas un
`MATERIAL_PASS`, n'autorise aucun déploiement et ne remplace pas l'échec matériel
historique. Le SHA exact, le décompte et la durée de la qualification finale sont
publiés avec le résultat `full-local` dans la PR #26, à partir du
`summary.json` produit par l'orchestrateur.

## Défaut et cause retenue

L'essai matériel autorisé a émis une seule fois `-10`, puis `+10` unités HID et
a observé un résidu final de +1 pixel. Un essai correctif séparément autorisé a
ensuite observé 9 pixels pour 10 unités, tandis que `move_to` a retrouvé la cible
exacte par six corrections. La configuration constatée avait l'accélération
Windows active.

La cause produit est l'assimilation erronée d'une unité HID relative à un pixel
écran. La transformation Windows est un contributeur directement observé ; les
preuves disponibles ne permettent pas de l'isoler comme cause mécanique unique,
et aucune nouvelle expérience matérielle n'est réalisée pour le faire.

## Correction

- `move_relative` reste compatible et documenté comme action brute en unités HID.
- `move_relative_confirmed` ancre sa cible sur une position fraîche et exprime
  le delta en pixels écran.
- La correction est fermée et bornée : durée, amplitude, mouvement cumulé,
  itérations, stagnation, oscillation et absence de progrès.
- Une mesure initiale absente/périmée n'émet rien ; une issue incertaine après
  émission devient `UNKNOWN` et n'est jamais rejouée.
- L'arrêt d'urgence interrompt aussi l'attente d'un nouveau retour de position.

Le MSIX HOGP, PositionAgent, le descripteur HID, la configuration Windows et les
composants installés ne sont pas modifiés.

## Preuves logicielles

La batterie ciblée exécute réellement la boucle et le transport simulé ; elle ne
se limite pas à rechercher des chaînes dans les scripts. Elle couvre notamment
un aller/retour exact malgré un résidu simulé d'un pixel, l'absence de retour,
la mesure périmée, la correction inefficace, la stagnation, l'oscillation, les
limites cumulées et d'itérations, l'arrêt d'urgence et l'émission incertaine sans
rejeu.

Commande ciblée :

```powershell
python -B -m unittest tests.test_controller tests.test_actions tests.test_api_catalog -v
```

La porte finale est :

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

Les diagnostics matériels restent explicitement exclus de cette porte.

## Réserves

La correction n'est pas encore démontrée sur la chaîne matérielle réelle tant
que le scénario minimal de [PROCEDURE-MATERIELLE.md](PROCEDURE-MATERIELLE.md)
n'a pas reçu une autorisation distincte et produit son propre verdict. Les
preuves et le `MATERIAL_FAIL` antérieurs restent conservés sans réécriture.
