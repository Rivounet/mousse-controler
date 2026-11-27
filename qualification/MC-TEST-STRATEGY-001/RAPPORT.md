# MC-TEST-STRATEGY-001 — architecture et portes de qualification

## Objectif

Transformer la suite locale historique en porte de qualification traçable,
structurée et fail-closed, sans ajouter de CI externe ni exécuter d'opération
matérielle.

## Baseline

- `main` d'entrée : `7e21ad2bbd7b9b78948ba2d5da16c74c89bf5565` ;
- 312 tests non matériels avant modification ;
- dernière qualification `full-local` : PASS en 372,625 s sur un arbre ensuite
  fusionné sans différence ;
- défaut confirmé : l'ancien orchestrateur pouvait produire `PASS` avec une
  identité Git indisponible et ne contrôlait pas la propreté de l'arbre ;
- aucune protection de branche ni CI externe, conformément à l'option B choisie
  par le propriétaire.

## Architecture livrée

- niveaux explicites `unit`, `contract`, `qualification`, `integration`,
  `system` et `support` ;
- profils rapides et d'intégration distincts, avec compatibilité
  `software`/`build`/`full-local` ;
- résumé de tests JSON structuré : exécutions, échecs, erreurs, skips, échecs
  attendus, succès inattendus et durées par famille ;
- qualification bloquée avant toute phase si Git est indisponible, l'identité
  commit/arbre est invalide ou le dépôt est sale ;
- compteurs de tests et provenance Git inclus dans le résumé v2 ;
- skips et `expectedFailure` interdits dans une qualification favorable.

## Vérifications de développement

- profil `fast` : 138/138 avant ajout des quatre tests de qualification du
  présent lot, 47 s ;
- profil `integration` final de développement : 176/176, zéro skip et zéro
  erreur ;
- un délai fragile du scénario de saturation `stderr` a été rendu spécifique
  au test de drainage, sans modifier les délais applicatifs ;
- une invocation de diagnostic hors runner a confirmé l'importance du
  répertoire temporaire court sous Windows ; le runner officiel le conserve.

La preuve officielle finale doit être exécutée sur un commit propre et publiée
dans la PR Draft avec le SHA, l'empreinte d'arbre, les compteurs, durées,
artefacts et exclusions. Les chemins locaux et informations sensibles ne sont
jamais publiés.

## Exclusions

Aucun HID, Bluetooth réel, capture, SSH, installation, déploiement, mutation de
tâche Windows ou accès à `MonOrdinateur`. La qualification matérielle conserve
sa porte et son consentement séparés.
