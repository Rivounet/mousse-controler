# Synchronisation Git non destructive

## Réalisation

- `git fetch --prune origin` a actualisé `origin/main` vers `a2c2542…` ;
- un worktree distinct a été créé sous
  `worktrees/mc-operational-recovery-001` ;
- branche : `prep/mc-operational-recovery-001` ;
- base : `a2c25423faebecee4fa882d36e982d1d93c7e425` ;
- commit de correctif : `6f2f5c16974711e0af59d8a86251eefdd8721b3f`.

Le clone `source` est resté sur sa branche et son SHA initiaux, avec un arbre
propre. Ses fichiers ignorés ont été sauvegardés avant le `fetch`.

## Diff logiciel

- `scripts/qualification/qualify.py` : cache Python temporaire court et nettoyé ;
- `tests/qualification/test_r4_qualification.py` : test de régression du chemin et nettoyage.

Aucun code applicatif, contrat de sécurité, descripteur HID ou comportement
fonctionnel n'a été modifié.

## Retour arrière Git

Le worktree et sa branche peuvent être retirés après clôture, sans toucher au
clone opérationnel. La référence de sauvegarde conserve le SHA initial. Aucun
`reset --hard`, rebase, fusion ou mise à jour de `main` n'a été effectué.
