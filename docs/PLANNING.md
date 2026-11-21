# Planning opérationnel

## État courant

Le programme correctif R0–R5 est fusionné dans `main` au SHA `0817823…`.
R6 consolide uniquement la documentation. La source unique pour les statuts des
constats et les preuves est [ROBUSTESSE.md](ROBUSTESSE.md).

| Travail | État | Sortie attendue |
|---|---|---|
| R6 — cohérence documentaire | En revue | PR Draft documentaire, liens et statuts vérifiés |
| PR #11 — audit indépendant | Ouverte, Draft, non fusionnée | décision séparée ; aucune fusion implicite |
| Synchronisation mini-PC / processus | Non planifiée dans R6 | mandat opérationnel distinct et vérification des SHA |
| Qualification matérielle post-R1–R5 | Non planifiée | autorisation explicite, protocole sûr et preuves séparées |

## Travaux différés sans priorité automatique

- C-09 : sources C++ HOGP historiques conservées.
- C-11 : deux séquenceurs maintenus.
- C-12 : responsabilités concentrées dans `actions.py` et `PositionAgent.cs`.
- C-17 : persistances et répétitions techniques non mutualisées.

Ces sujets ne sont ni résolus ni automatiquement ouverts. Une reprise exige un
bénéfice mesurable, un mandat spécifique et des tests protégeant R1–R5.

## Règles de livraison

- Codex réalise, qualifie et publie les preuves.
- ChatGPT vérifie la cohérence documentaire et effectue les revues indépendantes
  convenues ; une revue statique n'est pas une réexécution des tests Codex.
- L'utilisateur autorise fusion, déploiement, accès cible et essais matériels.
- GitHub Actions et toute CI externe restent exclus.
- Aucun changement de production ou de machine n'est implicite dans une fusion.
