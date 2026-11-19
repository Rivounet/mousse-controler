# Revue indépendante MC-INIT-003 — 19 novembre 2026

**PR :** [#3 Draft](https://github.com/Rivounet/mousse-controler/pull/3) — `150e6ad6db9b34669e41bfd422c3d804443af6cb`; base : branche de la [PR #2](https://github.com/Rivounet/mousse-controler/pull/2) à `cf3c37200541d3291f6b506731e14ce020bcf630`. **Verdict : PASS_WITH_RESERVATIONS pour les fondations locales. J4 : NON VALIDÉ.**

## Contrôles effectués

- Examen direct de la PR, du diff (16 nouveaux fichiers, +2 commits), des scripts `artifacts.py`, `releases.py`, `deployment.py`, des tests et des preuves.
- **15 empreintes SHA-256 sur 15 conformes** au manifeste (UTF-8/LF), sans inclure le manifeste lui-même.
- Le journal indique **69 tests PASS**, dont 31 hérités ; scripts et tests inspectés, mais tests **non réexécutés indépendamment** et aucune CI sur ce commit observée.
- Préparation d'artefacts Git par SHA complet avec manifeste et ZIP déterministe, refus de chemins/modes risqués et bundles altérés. Une archive de 10 fichiers / 101 481 octets est déclarée reproductible ; l'archive binaire est conservée localement, non accessible à cette revue.
- Gestion de releases locale avec état persistant et verrou exclusif ; `SimulatedRuntime` utilise des identités fictives et ne lance/arrête **aucun processus Windows réel**.
- Aucun SSH, transfert, déploiement ou changement de configuration sur `mini-pc-backend` durant MC-INIT-003.

## Réserves

1. `sync` prépare les artefacts localement : `remote_synced=false` et pas de transport réseau.
2. Le modèle `deploy`/`status`/`stop`/`rollback`/`recover` simule l'application. Aucune version active ou rollback distant démontré.
3. Le verrou protège les outils coopérants ; verrou abandonné et interruption brutale nécessitent une inspection manuelle. `os.replace` et `fsync` ne fournissent pas de transaction multi-fichiers ni une résistance prouvée à la coupure d'alimentation.
4. Vérifications de chemin et d'absence de jonction non atomiques face à des modifications concurrentes. La sélection et recherche de secrets sont ciblées, pas exhaustives.
5. La durée de vie des processus Windows après déconnexion SSH, le contexte de session, les privilèges minimaux, le suivi de santé, le transport de release, la reprise réseau et Bluetooth HID restent **NON QUALIFIÉS**.
6. La PR #3 dépend de la PR #2 non fusionnée ; ne pas changer sa base ou fusionner sans contrôler les écarts de dépendance.

## Décision

**MC-INIT-003 : PASS_WITH_RESERVATIONS. J4 reste en cours, non validé.** La prochaine qualification doit tester la survie d'un **processus témoin inoffensif** après déconnexion SSH et la préparation du transport/versionnement distant, avec nouvelle autorisation explicite pour toute mutation sur le mini-PC. Les PR #1, #2 et #3 demeurent Draft non fusionnées. La revue GitHub est enregistrée comme commentaire, sans approbation de fusion.

**Règle maintenue :** les mandats Codex sont fournis exclusivement dans le chat, jamais archivés dans GitHub.
