# Mesures avant/après

## Corrections réalisées

| Sujet | Avant | Après | Risque et protection |
|---|---|---|---|
| C-13 polygone fin | 7/20 graines lèvent `RuntimeError`; 10 000 rejets puis échec | mêmes 10 000 essais bornés, puis 1 choix RNG parmi des sommets garantis valides; 0 échec couvert | faible : sorties des graines déjà réussies inchangées; tests de 6 familles × 50 graines × 2 exécutions |
| C-14 insertion registre | 2 écritures directes sans garde; événements dans un littéral; doublon écrasable avant validation | 1 primitive d'insertion, 3 points d'entrée protégés avant mutation | faible : mêmes dictionnaires et formats; tests d'identité de l'ancien objet après refus |

Le repli C-13 n'ajoute aucune boucle non bornée et consomme le RNG fourni : une
même graine produit le même point. Les sommets sont inclus par le contrat
`contains`, donc le point de repli appartient toujours à la zone autorisée.

## Mesures structurelles

Mesure AST simple : nombre de fonctions et de nœuds de branchement (`if`,
`for`, `while`, `try`, `with`, expressions booléennes, `match`, compréhensions).

| Fichier | Lignes | Fonctions | Branchements | Fonction la plus longue |
|---|---:|---:|---:|---|
| `actions.py` | 1 062 | 47 | 244 | `_perform`: 221 lignes, 48 branchements |
| `sequence.py` | 303 | 15 | 45 | `_run`: 99 lignes, 20 branchements |
| `api_catalog.py` avant correction | 890 | 18 | 108 | rendu de référence : 135 lignes |
| `PositionAgent.cs` | 600 | n/a (C#) | non comparé | responsabilités inventoriées séparément |

## Extractions évaluées et non réalisées

| Cible | Lignes concernées | Gain démontré | Risque | Décision |
|---|---:|---|---|---|
| fusion des séquenceurs | >300 + chemins `ActionExecutor` | aucun : états/persistance différents | élevé, garanties R1 | différée |
| extraction `_perform` | 221 | taille potentiellement réduite, duplication non isolée | moyen/élevé, transitions et effets HID | PR dédiée requise |
| persistance actions/captures | >100 par système | schéma commun non démontré | élevé, contrats R3 distincts | ne pas fusionner |
| découpage `PositionAgent.cs` | 600 | cohésion de sous-domaines plausible | moyen, build/déploiement cible | PR dédiée avec tests |
| utilitaires PowerShell | plusieurs scripts | répétitions superficielles seulement | moyen, transactions et privilèges différents | différée |

Aucune valeur « après » artificielle n'est annoncée pour les travaux différés.
