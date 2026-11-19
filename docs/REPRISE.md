# Reprise du projet Mousse-controler

**Dernière consolidation : 19 novembre 2026.** Ce document est le point d'entrée pour reprendre le projet dans une nouvelle conversation ChatGPT ou une nouvelle session Codex Desktop. Ne pas le confondre avec une preuve d'exécution.

## 1. Objectif produit

Le mini-PC nommé **mini-pc-backend** doit recevoir des commandes d'une API et se présenter par Bluetooth comme une **souris HID** auprès d'un **PC Windows cible**. Windows doit utiliser sa pile et son pilote HID natifs, **sans application réceptrice dédiée** sur le PC cible ; l'appairage Bluetooth est permis. Les actions visées incluent déplacement relatif, clic et défilement. La compatibilité du contrôleur Bluetooth existant et de la pile logicielle **reste à démontrer**.

## 2. Machines et dépôt

| Élément | Rôle |
|---|---|
| PC Windows | Poste local de développement avec **Codex Desktop** ; également ordinateur cible recevant la souris Bluetooth |
| `mini-pc-backend` | Machine distante où le code est déployé, exécuté et testé ; émetteur Bluetooth HID et hôte de l'API |
| [GitHub Rivounet/mousse-controler](https://github.com/Rivounet/mousse-controler) | **Seule source de vérité officielle** pour le code et la documentation |

Le développement et les tests unitaires préliminaires sont effectués depuis Windows ; les essais d'intégration et de comportement Bluetooth doivent être attestés sur **mini-pc-backend** et le PC cible.

## 3. Responsabilités permanentes

| Acteur | Responsabilités |
|---|---|
| **Utilisateur** | Définit les objectifs, tranche les choix engageants, autorise modifications système, fusions et opérations sensibles |
| **ChatGPT** | Définit les mandats Codex, tient la documentation et les décisions à jour dans GitHub, pilote la roadmap et le planning, supervise Git/GitHub, effectue les revues indépendantes de code et de preuves |
| **Codex Desktop** | Exécute les mandats, développe localement, prépare les branches et PR, effectue diagnostics, transferts/déploiements autorisés, tests distants et comptes rendus |

**Cycle :** mandat ChatGPT → travaux Codex → rapport, SHA, diff/PR et preuves → revue ChatGPT (PASS / PASS_WITH_RESERVATIONS / NO-GO) → décision utilisateur si nécessaire → mise à jour documentaire. Ne jamais présenter une validation de ChatGPT comme une exécution ou une supervision continue automatique : elle intervient à la demande, sur preuves consultables.

## 4. Principes de gestion

- **Planning par jalons, sans dates imposées**. L'état opérationnel des tâches est dans [PLANNING.md](PLANNING.md) ; les critères de jalon sont dans [ROADMAP.md](ROADMAP.md).
- Développement ciblé, branches de travail et PR **Draft** pour les modifications applicatives. **Pas de fusion implicite**, ni modification directe de `main` par Codex.
- Conserver les modifications préexistantes, contrôler SHA et état Git avant toute manipulation ; pas de force-push ni de nettoyage destructif.
- Séparer source Git distante et versions déployées sur mini-PC. Toute synchronisation vise une **révision SHA exacte**.
- Accès distant sécurisé, vérification de l'hôte, scripts reproductibles, journaux rapatriés, déploiement idempotent, verrou contre la concurrence, contrôles de santé et rollback.
- Pas d'installation/configuration réseau/Bluetooth non autorisée ; pas d'API exposée publiquement. Préserver la souris physique du PC et éviter les clics de test intempestifs.
- Favoriser la simplicité : documents utiles, décisions courtes, pas de gouvernance supplémentaire sans nécessité.

## 5. État connu et inconnues

**Acquis :** dépôt GitHub initialisé avec README, consignes Codex, roadmap, planning, architecture, procédure de déploiement, spécification d'accès distant, stratégie de tests, registre des décisions et ce document de reprise.

**Non démontré :** connexion distante vers mini-pc-backend, version de son OS et matériel Bluetooth exact, capacité du mode périphérique HID, méthode de synchronisation, scripts effectifs, prototype HID, API et tests réels. Ne pas confondre une spécification publiée avec un logiciel déjà fonctionnel.

**Jalons :** J0 cadrage documentaire validé ; **J1 environnement et accès distant à démarrer** ; J2 faisabilité Bluetooth HID ; J3 API ; J4 déploiement robuste ; J5 qualification MVP.

## 6. Prochaine action

**Premier mandat : [MC-INIT-001 — démarrage from scratch](MANDATS/MC-INIT-001.md)**, à exécuter avec Codex Desktop sur le PC Windows. Objectif : vérifier le dépôt local et GitHub, inventorier Windows et mini-pc-backend **en lecture seule**, identifier les moyens d'accès distant, proposer la solution de synchronisation et les pistes HID. **Ne pas encore installer, reconfigurer ou développer le prototype Bluetooth.**

Après le rapport Codex : ChatGPT vérifie les faits, écarts Git et risques, consigne la revue et prépare un second mandat ciblé (accès distant/déploiement), après arbitrages éventuels.

## 7. Où retrouver les détails ?

- [README.md](../README.md) : présentation et navigation.
- [ROADMAP.md](ROADMAP.md) / [PLANNING.md](PLANNING.md) : jalons et tâches.
- [ARCHITECTURE.md](ARCHITECTURE.md) : architecture et inconnues Bluetooth.
- [ACCES-DISTANT-ET-SYNCHRONISATION.md](ACCES-DISTANT-ET-SYNCHRONISATION.md) / [DEPLOIEMENT.md](DEPLOIEMENT.md) : contrat de gestion distante et déploiement.
- [TESTS.md](TESTS.md) : validations et revue de code.
- [DECISIONS.md](DECISIONS.md) : décisions datées.
- [AGENTS.md](../AGENTS.md) : instructions opérationnelles Codex.

## 8. Règle de mise à jour

À chaque jalon ou décision structurante, **ChatGPT met à jour** les documents concernés et résume ici : état réellement vérifié, prochaine action, blocages et références PR/SHA utiles. Ne pas dupliquer l'intégralité des rapports, pointer vers leurs preuves.
