# MC-ROBUSTNESS-R6-001 — Rapport de consolidation documentaire

## Verdict documentaire

**PASS sous réserve de revue et fusion explicite de la PR R6.**

La branche part de `main`
`0817823eb2e7a5e8d477ed3e382ef128611fd5b9`. Aucun fichier applicatif, test,
script ou référence API générée n'est modifié. Aucun test matériel, accès cible,
installation, synchronisation ou déploiement n'est exécuté.

## Inventaire GitHub vérifié

- PR #10 et #12–#18 : fusionnées ; commits R0–R5 conformes aux références du
  mandat.
- PR #11 : ouverte, Draft, non fusionnée.
- qualifications finales R4 et R5 : commentaires publiés sur les SHA finaux de
  branche ; 269/269 et 271/271 tests déclarés PASS par Codex.
- revues ChatGPT : examens indépendants des diffs et preuves, distincts des
  exécutions locales Codex et explicitement décrits comme non réexécutés.

## Consolidation

- `docs/ROBUSTESSE.md` devient l'unique matrice C-01 à C-17.
- README expose seulement l'état courant synthétique.
- roadmap et planning ne conservent que les décisions et travaux réellement
  ouverts.
- reprise sépare GitHub des machines et processus non vérifiés.
- tests formalise les profils locaux et la portée des preuves.
- architecture et décisions sont alignées sur le moteur HOGP actif et la clôture
  R0–R6.
- les critères R0 historiques sont clarifiés sans modifier les rapports R0–R5.

## Contradictions corrigées

- R0–R5 ne sont plus présentés comme Draft, à publier ou non commencés.
- les quatre P1 initiaux ne sont plus présentés comme ouverts après leurs
  correctifs fusionnés.
- R5 est présenté comme C-13/C-14 ciblé, pas comme refonte complète.
- l'état des machines n'est plus déduit de l'état GitHub.
- GitHub Actions/CI externe sont exclus de manière cohérente.
- les tests Codex et les revues ChatGPT sont distingués.

## Réserves

Les réserves de code, qualification et exploitation sont conservées dans
[`docs/ROBUSTESSE.md`](../../docs/ROBUSTESSE.md), notamment la non-requalification
matérielle, les sept diagnostics exclus, les limites WinRT/récupération/quota,
la roulette horizontale et les réserves LAN/GATT historiques.

## Vérifications

Les contrôles de liens Markdown, références PR/SHA, statuts contradictoires,
cohérence documentaire, `git diff --check` et liste de fichiers sont consignés
dans la description de la PR. `full-local` n'est pas relancé car le diff est
strictement documentaire.
