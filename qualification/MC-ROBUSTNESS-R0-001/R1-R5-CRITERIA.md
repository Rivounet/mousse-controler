# Critères de sortie R1 à R5 — état actuel

Ce document définissait les portes proposées par R0. Elles ont ensuite guidé
les lots R1–R5. Les rapports de chaque lot et
[`docs/ROBUSTESSE.md`](../../docs/ROBUSTESSE.md) font foi pour les résultats.

| Lot | Décision actuelle | Portée |
|---|---|---|
| R1 | Critères logiciels atteints, PR #14 fusionnée | matériel non requalifié |
| R2 | Critères logiciels atteints, PR #15 fusionnée | WinRT et matériel non requalifiés |
| R3 | Critères logiciels atteints, PR #16 fusionnée | opérations réelles de récupération non requalifiées |
| R4 | `full-local` final PASS, PR #17 fusionnée | 7 diagnostics matériels exclus ; aucune CI externe |
| R5 | C-13/C-14 qualifiés localement, PR #18 fusionnée | C-09/C-11/C-12/C-17 différés |

## Critères conservés

- R1 : états ambigus `UNKNOWN`, quarantaine/arrêt, coordination des séquenceurs,
  drainage de file et absence de rejeu.
- R2 : deadlines HOGP, arrêt indépendant, drainage stderr, handshake/lectures et
  connexions LAN bornés, TLS/HMAC inchangés.
- R3 : quota au pic, temporaires/index/orphelins comptés, nettoyage best-effort,
  rollback borné et `RECOVERY_REQUIRED` durable.
- R4 : profils locaux `software`, `build`, `full-local`, découverte contrôlée
  des outils, résultats et artefacts mesurés. GitHub Actions et toute CI externe
  sont définitivement exclus du programme actuel.
- R5 : aucun changement de contrat ; C-13/C-14 couverts ; aucune suppression
  HOGP ou convergence structurelle sans bénéfice démontré.

Ces critères n'autorisent ni déploiement, ni essai HID/capture, ni modification
des machines. Un résultat logiciel fusionné n'est pas une preuve matérielle.
