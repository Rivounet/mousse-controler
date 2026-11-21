# Roadmap — décisions futures

## Programme achevé

R0 à R5 sont fusionnés dans `main`. La PR Draft R6 prépare la clôture de la
consolidation documentaire, qui reste soumise à revue et fusion explicite. Les
références exactes figurent dans [ROBUSTESSE.md](ROBUSTESSE.md).

Le résultat est un durcissement logiciel qualifié localement, pas une nouvelle
qualification matérielle ni un déploiement. Les preuves matérielles historiques
de MC-HID-EXEC-001 et MC-MOUSE-ACTIONS-001 restent valides dans leur périmètre
et ne sont pas étendues aux correctifs R1–R5.

## Portes futures

1. **Exploitation :** avant toute activation, relever le SHA du clone, du
   contrôleur, du MSIX HOGP et de PositionAgent ; préparer rollback et santé.
2. **Matériel :** requalifier seulement sur mandat explicite, avec arrêt
   d'urgence et consentement pour toute prise de souris ou capture.
3. **Dette différée :** rouvrir C-09/C-11/C-12/C-17 uniquement si un bénéfice
   net et indépendant est démontré.
4. **Fonctionnalités :** toute extension doit préserver les garanties R1–R5 et
   séparer code, qualification locale, fusion, synchronisation et déploiement.

## Gouvernance

Le dépôt GitHub est la source officielle. Les profils locaux Windows remplacent
durablement toute attente de GitHub Actions ou de CI externe pour ce programme.
Les rapports historiques restent immuables ; les changements d'état sont ajoutés
au registre [DECISIONS.md](DECISIONS.md).
