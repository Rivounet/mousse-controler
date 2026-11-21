# Planning opérationnel — 21 novembre 2026

| Chantier | État | Critère de clôture |
|---|---|---|
| Robustesse R0–R5 et R6 | Fusionnés | Qualifications logicielles et rapports historiques conservés |
| PR #22–#24 : préparation et environnement Codex | Fusionnées | `ENVIRONMENT_READY`, `full-local` 286/286 PASS selon Codex |
| Mise en service mini-pc-backend et MonOrdinateur | **AUTORISÉE — À EXÉCUTER** | MSIX signé et approuvé installé, PositionAgent mis à jour, contrôleur actif, SHA et santé vérifiés, rollback prêt |
| Communication/API/WebSocket sans action HID | À qualifier en exploitation | Authentification, sessions, ports, états et échange LAN vérifiés |
| Qualification matérielle HID/capture | **EN ATTENTE DE CONSENTEMENT SPÉCIFIQUE** | Accord à l'instant des essais, arrêt d'urgence, preuves réelles |
| PR #11 audit historique | Draft non fusionnée | Décision distincte ; aucune fusion implicite |
| MC-HID-PRECISION-001 — correction logicielle | En qualification dans la PR #26 | `SOFTWARE_FIX_QUALIFIED`, sans émission HID réelle |
| MC-HID-PRECISION-001 — requalification matérielle | Bloquée par autorisation distincte après qualification logicielle | deux actions bornées, aucun clic/défilement/capture |

## Exécution

Codex réalise les étapes déjà autorisées de bout en bout, réutilise les procédures `scripts/operations/` dans leurs contextes exacts et corrige les anomalies ordinaires sans arrêter le mandat à chaque étape. Rapporter les jalons significatifs avec temps écoulé. Une PR ou un build ne constituent pas une preuve de mise en service. ChatGPT maintient la documentation de référence et suit GitHub ; les nouvelles fusions restent soumises à accord explicite. Aucun GitHub Actions ni CI externe.

## Différés

C-09/C-11/C-12/C-17 ne sont pas automatiquement rouverts. Les essais matériels restent séparés de l'activation logicielle.
