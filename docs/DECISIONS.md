# Décisions et hypothèses

Les décisions ne sont pas des preuves de faisabilité. Pour chaque choix structurant, noter **date, statut, motivation et effet**. Ce journal fait foi avec la roadmap.

| ID | Date | Statut | Décision / hypothèse | Conséquence |
|---|---|---|---|---|
| D-001 | 2026-11-19 | Validé | Dépôt officiel : `Rivounet/mousse-controler` | Code et documentation de référence dans ce dépôt |
| D-002 | 2026-11-19 | Validé | Développer avec Codex Desktop sur le PC Windows | Ne pas confondre poste de développement et machine d'exécution |
| D-003 | 2026-11-19 | Validé | Exécuter, déployer et tester sur `mini-pc-backend` | Les résultats locaux seuls sont insuffisants |
| D-004 | 2026-11-19 | Validé | PC cible Windows, réception Bluetooth HID native, sans agent dédié | Appairage Bluetooth autorisé, logiciel récepteur non requis |
| D-005 | 2026-11-19 | Validé | Pilotage par **jalons**, sans échéances calendaires | Validation sur livrables et preuves |
| D-006 | 2026-11-19 | Validé | ChatGPT responsable de la documentation et de la revue du code | Codex propose/implémente ; revue indépendante avant fusion |
| D-007 | 2026-11-19 | Priorité validée, faisabilité ouverte | Tenter d'abord le Bluetooth intégré au mini-PC | J2 décide GO/NO-GO selon tests réels |
| D-008 | 2026-11-19 | À qualifier | OS, pilote et rôle BLE périphérique de mini-pc-backend | Inventaire J1/J2 préalable à tout choix de bibliothèque |
| D-009 | 2026-11-19 | Proposé | Contrat API local, authentifié, commandes relatives et arrêt d'urgence | Design à valider pendant J3 |
| D-010 | 2026-11-19 | Validé | Pas de fusion ni de déploiement durable implicite | Arbitrage explicite après revue |
| D-011 | 2026-11-19 | Validé | Prévoir une procédure et du code robustes pour l'accès distant, la synchronisation Git et le déploiement vers mini-pc-backend | J1 qualifie l'accès ; J4 livre et teste l'automatisation |
| D-012 | 2026-11-19 | Cible à qualifier | GitHub reste la référence officielle ; copie distante et versions exécutées sur mini-PC sont isolées | Pas de deuxième source de vérité, pas de réinitialisation Git destructive ; choix transport soumis à inventaire |

| D-013 | 2026-11-19 | Validé | ChatGPT rédige les mandats Codex et supervise la gestion Git/GitHub | Mandats ciblés ; contrôle du diff, des SHA, des PR et des fusions avant validation |
| D-014 | 2026-11-19 | Validé | Premier mandat = amorçage from scratch et diagnostic non destructif | Pas de prototype HID ou de changement système avant vérification de l'environnement |

| D-015 | 2026-11-19 | Validé | Centraliser la reprise future dans `docs/REPRISE.md` et versionner les mandats Codex | Reprise fondée sur l'état Git, le jalon en cours et des livrables vérifiables |

## En cas de changement

Ajouter une ligne datée avec la décision remplacée et sa justification ; ne pas effacer silencieusement une décision antérieure. Répercuter les modifications sur [ROADMAP.md](ROADMAP.md), [PLANNING.md](PLANNING.md) et [ARCHITECTURE.md](ARCHITECTURE.md) lorsque cela s'applique.

**Inconnues majeures :** contrôleur Bluetooth effectif, compatibilité émission HID sous l'OS réel, canal d'accès distant, pile logicielle et mécanisme de déploiement.
