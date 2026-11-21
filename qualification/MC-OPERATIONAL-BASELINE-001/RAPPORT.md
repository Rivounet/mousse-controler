# MC-OPERATIONAL-BASELINE-001 — Rapport

## Verdict

**PARTIAL.** GitHub et `mini-pc-backend` ont été inspectés passivement.
`MonOrdinateur` est `BLOCKED` : le canal SSH documenté existe, mais la connexion
depuis la sandbox est refusée et poursuivre exigerait une nouvelle approbation.

Aucune synchronisation Git, installation, activation, tâche, opération
Bluetooth, commande HID, capture, déploiement ou rollback n'a été réalisé.

## Références

- GitHub `main` : `440ab39a042ddd5254cc93a75e2d91123b362b4a`.
- Fusion correspondante : PR #19, MC-ROBUSTNESS-R6-001.
- Clone `source` du mini-PC : branche `feat/mc-api-catalog-001`, SHA
  `34b2612bef260db382251601c103886dd76dd12a`, arbre propre.
- Référence locale `origin/main` non actualisée : `0817823…`.

## Résultat synthétique

- aucun processus Mousse/Python/HOGP/PositionAgent correspondant n'est visible ;
- registre local de processus vide et état d'activation historique sans
  processus associé ;
- configuration contrôleur encore dirigée vers le moteur C++ historique ;
- alias `mousse-hogp-packaged.exe` présent, mais métadonnées AppX inaccessibles ;
- tâches planifiées inaccessibles dans ce contexte ;
- aucun fichier persistant d'actions/captures trouvé dans `state/` ou `runtime/` ;
- périphérique Bluetooth `MONORDINATEUR` exposé passivement par PnP, sans test
  de connexion, radio ou fonction HID ;
- état PositionAgent sur la cible entièrement `BLOCKED`.

## Écarts

Huit écarts ou inconnues sont suivis : **0 CRITICAL, 4 MAJOR, 1 MINOR et
3 INFORMATIONAL**. Les détails et autorisations nécessaires figurent dans
[RISQUES.md](RISQUES.md).

## Conclusion

La présence d'anciens artefacts et d'un alias MSIX ne prouve pas qu'un runtime
récent soit installé ou chargé. L'état observé ne concorde pas avec GitHub et ne
permet pas d'affirmer que Mousse-controler est opérationnel. Une phase ultérieure
pourra autoriser séparément l'inspection cible hors sandbox, puis décider d'une
synchronisation ou d'un redéploiement ; aucune de ces actions n'est incluse ici.

