# MC-OPERATIONAL-RECOVERY-001 — Rapport consolidé

## Verdict

**PARTIAL.** Le code officiel a été récupéré dans un worktree séparé, un défaut
de qualification Windows a été corrigé, les données existantes ont été
sauvegardées et la qualification locale complète réussit sur le commit du
correctif. Une configuration cohérente et un dossier de déploiement ont été
préparés sans remplacer la configuration active.

Le passage à `READY_FOR_DEPLOYMENT_DECISION` est bloqué par l'absence d'un
certificat de signature MSIX disposant de sa clé privée. Les tâches planifiées
restent inaccessibles et `MonOrdinateur` reste `BLOCKED` depuis la sandbox.

## Résultats

- base GitHub : `a2c25423faebecee4fa882d36e982d1d93c7e425` ;
- commit logiciel qualifié : `6f2f5c16974711e0af59d8a86251eefdd8721b3f` ;
- clone opérationnel préservé au SHA `34b2612…`, arbre propre ;
- sauvegarde locale vérifiée : 67 fichiers, 915 495 octets, aucune divergence ;
- `full-local` : **PASS**, 272 tests, 137,859 s, sept diagnostics matériels exclus ;
- PositionAgent construit ;
- MSIX PowerShell/WinRT construit mais non signé ;
- configuration de staging validée, secrets DPAPI conservés ;
- aucun déploiement, installation, activation, tâche, Bluetooth, HID ou capture.

## Correctif réalisé

`compileall` reproduisait le chemin source absolu sous `PYTHONPYCACHEPREFIX`.
Dans un worktree profond, le cache placé sous le répertoire de qualification
dépassait la limite de chemin Windows. Le cache est désormais créé dans un
répertoire court, unique et local au worktree, puis supprimé par le même cycle
de vie. Un test de régression vérifie son emplacement et son nettoyage.

## Décision suivante

Avant toute installation, fournir de manière contrôlée le certificat de
signature existant avec sa clé privée, reconstruire et signer le MSIX, vérifier
sa signature, puis refaire `full-local`. L'inspection des tâches et de la cible
doit rester séparée. Le présent verdict n'autorise aucun déploiement.
