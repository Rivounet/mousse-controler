# MC-OPERATIONAL-BASELINE-002 — Rapport

## Verdict

**PARTIAL.** L'inventaire passif du mini-PC a permis d'identifier précisément
le MSIX HOGP installé et les chemins de persistance attendus. La lecture des
tâches planifiées reste bloquée dans le contexte de sécurité disponible et
`MonOrdinateur` reste inaccessible depuis la sandbox.

Aucun composant opérationnel n'a été synchronisé, démarré, arrêté, installé,
activé, modifié ou qualifié matériellement.

## Références vérifiées

- GitHub `main` : `fe4def1dd6f5a895a81ec60e52b480bb5fbc9421`.
- Clone opérationnel : branche `feat/mc-api-catalog-001`, SHA
  `34b2612bef260db382251601c103886dd76dd12a`, arbre propre.
- Référence locale `origin/main` :
  `0817823eb2e7a5e8d477ed3e382ef128611fd5b9`, non actualisée pendant l'audit.

## Résultats complémentaires

- package installé : `Rivounet.MousseControler.Hogp` version `1.0.0.2`,
  éditeur `CN=MousseControler` ;
- manifeste installé lisible et alias `mousse-hogp-packaged.exe` présent ;
- binaire déclaré : `powershell.exe`, avec script WinRT `hogp.ps1` ;
- manifeste, script et hôte installés identiques aux entrées du MSIX local
  accessible, SHA-256 du MSIX `907AFB9E…B12042` ;
- quatre méthodes passives de lecture des tâches refusées ; leur présence,
  état et historique restent `BLOCKED` ;
- aucun processus applicatif correspondant visible dans la session inspectée ;
- chemins par défaut des persistances déterminés, mais journal d'actions,
  registre `.ids`, index et images de capture absents des emplacements ciblés ;
- configuration contrôleur toujours dirigée vers le moteur C++ historique ;
- état cible PositionAgent entièrement `BLOCKED`.

## Conclusion

Le package PowerShell/WinRT est installé et son contenu est vérifiable, mais il
n'est pas le transport référencé par la configuration contrôleur observée.
L'absence de processus visible ne prouve ni l'absence ni l'état des tâches
inaccessibles. Les huit écarts initiaux sont actualisés dans
[MATRICE-ECARTS.md](MATRICE-ECARTS.md). Un plan réversible, strictement non
exécuté, figure dans [PLAN-SYNCHRONISATION.md](PLAN-SYNCHRONISATION.md).


