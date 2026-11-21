# MC-CODEX-ENVIRONMENT-001 — Rapport

## Verdict

**ENVIRONMENT_READY**

L'environnement Codex Windows est reproductible pour les travaux locaux, la
lecture de la tâche Mousse-controler, l'inspection passive de `MonOrdinateur`,
les qualifications logicielles et la préparation MSIX. Les contextes exigeant
une sortie de sandbox sont limités à des commandes ou scripts exacts; aucune
permission générale SSH, PowerShell ou administrateur n'a été ajoutée.

Référence de départ : `44c1350e304559a1bb1d477936d9705404c2dedf`.
Branche de livraison : `tools/mc-codex-environment-001`.

## Résultats

- La sandbox convient à Git, Python, builds, tests, lecture de fichiers et
  écriture dans le worktree. Son réseau et certains fournisseurs Windows sont
  effectivement restreints, même si une préférence utilisateur est plus large.
- Le canal SSH exact a exécuté une commande passive hors sandbox, puis a été
  réutilisé sans nouvelle décision. L'identité d'hôte reste stricte.
- La tâche locale a été lue deux fois dans son contexte propriétaire : activée,
  interactive, privilèges limités, état `Ready`, dernier résultat `1`, aucun
  processus ni port de commande actif au moment de la preuve.
- La tâche distante est activée et `Running`; son processus est en session
  interactive et son binaire correspond au hash attendu.
- Une nouvelle clé RSA 3072 bits a été créée hors dépôt. Le PFX est chiffré,
  son secret est protégé par DPAPI CurrentUser et le dossier n'accorde l'accès
  qu'à l'utilisateur courant et SYSTEM. Création idempotente et restauration
  ont réussi.
- Le MSIX isolé 1.0.0.3 a été signé; signataire, publisher et identité
  concordent. La racine nouvelle n'est volontairement pas approuvée.
- La suite `full-local` a réussi sur le HEAD publié, sans diagnostic matériel,
  accès distant, installation ou déploiement.

## Effets opérationnels

Aucune tâche, ACL opérationnelle, configuration, confiance Windows, version
MSIX installée, processus d'application ou cible distante n'a été modifiée.
Seuls la clé de signature utilisateur protégée et les artefacts isolés de
qualification ont été créés.

Les preuves expurgées sont dans `evidence/procedure-results.json`. Les contrats
exécutables sont documentés dans `scripts/operations/README.md`.

## Finalisation de la PR #24

Les deux réserves de revue sont closes par des preuves comportementales :

- un refus du fournisseur de processus produit `BLOCKED`, code `2`, avec nombre
  et liste de processus à `null`; une inspection réussie sans processus produit
  distinctement `PASS`, `0` et une liste vide;
- `prepare-deployment` ouvre un instantané verrouillé du MSIX, relit son manifeste
  et exige la concordance exacte du SHA-256, de la taille, du nom d'identité, du
  publisher et de la version avec la preuve de signature;
- les divergences de hash, d'identité et de version retournent toutes `PARTIAL`,
  code `2`, avec `signing_qualified=false`;
- l'inspecteur local corrigé a également été rejoué dans son contexte Windows
  réel en lecture seule.

La suite `full-local` est rejouée sur le HEAD final. Son SHA, son nombre de tests,
sa durée et le verdict sont publiés dans le commentaire final de la PR.
