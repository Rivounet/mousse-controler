# État Git/GitHub observé le 19 novembre 2026

- `origin/main` : `2b42ea12aaeaeb9dad7512a621e66257f7f8a37a`.
- PR #1 : Draft ouverte, tête `8886cab1230039add8e2712a5114c4e312c0f49b`, base `main`.
- PR #2 : Draft ouverte, tête `cf3c37200541d3291f6b506731e14ce020bcf630`, base `main`.
- PR #3 : Draft ouverte, tête `150e6ad6db9b34669e41bfd422c3d804443af6cb`, base PR #2.
- PR #1 indépendante de PR #2 ; PR #2 est ancêtre de PR #3.
- Les trois PR étaient signalées fusionnables par GitHub au diagnostic.
- Aucun clone Git ne préexistait dans la racine d'exécution. Le clone officiel a
  été créé dans son sous-dossier `source/`, sans modifier les artefacts locaux.
- La branche `feat/mc-reprise-001-consolidation` part de `origin/main` et
  conserve les cinq commits utiles des trois PR par cherry-pick non destructif.
- PR #4 : Draft créée depuis cette branche vers `main`, sans fusion automatique.

Commandes de lecture utilisées : `git ls-remote`, `git merge-base`,
`git rev-list`, API publique GitHub des PR. Aucune branche ou PR existante n'a
été supprimée, fusionnée, rebasée ou réécrite.
