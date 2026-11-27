# Planning opérationnel — 27 novembre 2026

| Chantier | État | Critère de clôture |
|---|---|---|
| Robustesse R0–R5 et R6 | Fusionnés | Qualifications logicielles et rapports historiques conservés |
| PR #22–#24 : préparation et environnement Codex | Fusionnées | `ENVIRONMENT_READY`, `full-local` 286/286 PASS selon Codex |
| Mise en service mini-pc-backend et MonOrdinateur | **QUALIFIÉE** | MSIX et PositionAgent conformes, contrôleur PR #26 actif, sauvegarde et rollback vérifiés |
| Communication/API/WebSocket | **QUALIFIÉE** | 401 sans jeton, événements corrélés, télémétrie fraîche et reconnexion vérifiés |
| Qualification matérielle HID/capture | **EXÉCUTÉE** | Consentement immédiat, actions bornées, capture privée supprimée, arrêt d'urgence et récupération vérifiés |
| PR #11 audit historique | Draft non fusionnée | Décision distincte ; aucune fusion implicite |
| MC-HID-PRECISION-001 — correction logicielle | **QUALIFIÉE** dans la PR #26 | `SOFTWARE_FIX_QUALIFIED`, 301/301 sur `aa53504…` |
| MC-HID-PRECISION-001 — requalification matérielle | **QUALIFIÉE** | aller/retour exact, axes X/Y, amplitudes, absolu, tolérance et bornes observés |
| MC-FINAL-VALIDATION-001 | **TERMINÉE — PR À REVOIR** | rapport consolidé publié ; PR maintenue Draft et non fusionnée |
| Audit architecture/runtime | **TERMINÉ** | dérive de worktree, concurrence des voies et feedback non atomique démontrés |
| Couche application et coordination | **IMPLÉMENTÉE, À QUALIFIER AU SHA PUBLIÉ** | aucun entrelacement inter-voie ; arrêt toujours prioritaire |
| Feedback position/topologie | **IMPLÉMENTÉ, À QUALIFIER AU SHA PUBLIÉ** | une génération atomique ou refus fail-closed |
| Release contrôleur immuable | **IMPLÉMENTÉE, NON ACTIVÉE** | extraction Git propre, manifeste, empreintes et refus des fichiers inattendus |
| Runtime actif historique | **NON REPRODUCTIBLE — À REMPLACER APRÈS PORTE** | aucune mutation avant qualification, PR et rollback vérifié |

## Exécution

Codex réalise les étapes déjà autorisées de bout en bout, réutilise les procédures `scripts/operations/` dans leurs contextes exacts et corrige les anomalies ordinaires sans arrêter le mandat à chaque étape. Rapporter les jalons significatifs avec temps écoulé. Une PR ou un build ne constituent pas une preuve de mise en service. ChatGPT maintient la documentation de référence et suit GitHub ; les nouvelles fusions restent soumises à accord explicite. Aucun GitHub Actions ni CI externe.

## Différés

C-11 est rouvert et traité par la convergence ; C-12 est réduit de façon
ciblée. C-09/C-17 restent différés. Toute nouvelle
prise de souris reste soumise à un nouveau consentement immédiat malgré la
clôture de cette validation.
