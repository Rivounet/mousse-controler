# Mousse-controler

Contrôle d'une souris sur un PC Windows cible depuis **mini-pc-backend**, via Bluetooth HID, au moyen de commandes reçues par une API.

> **Statut : cadrage initial.** La compatibilité Bluetooth HID du mini-PC n'est pas encore vérifiée. Aucun fonctionnement effectif n'est revendiqué à ce stade.

## Architecture cible

1. **PC Windows de développement** : Codex Desktop développe le code, gère Git et pilote les opérations distantes.
2. **mini-pc-backend** : reçoit les commandes API, les traduit en événements HID, les émet par Bluetooth ; héberge les exécutables et les essais réels.
3. **PC Windows cible** : reçoit les événements au moyen de sa pile Bluetooth/HID native, **sans application réceptrice dédiée**. Il s'agit aussi du PC utilisé pour développer.

Un appairage Bluetooth initial reste nécessaire. Le protocole exact (BLE HID over GATT ou autre solution HID compatible) dépendra de la qualification matérielle.

## Principes

- Priorité au Bluetooth déjà présent, sans matériel additionnel si faisable.
- Aucun logiciel spécifique installé sur le PC cible pour recevoir les commandes.
- API non exposée publiquement, accès authentifié et contrôles de sécurité.
- Tests réels exécutés sur **mini-pc-backend**, pas seulement sur le poste de développement.
- Simplicité : jalons plutôt que dates fixes, GitHub Issues pour les tâches, changements de code examinés avant fusion.
- Aucun pilote constructeur particulier n'est requis par principe : viser l'interface HID native de Windows.

## Documentation

- [Roadmap par jalons](docs/ROADMAP.md)
- [Planning opérationnel](docs/PLANNING.md)
- [Architecture et choix à valider](docs/ARCHITECTURE.md)
- [Déploiement et séparation des environnements](docs/DEPLOIEMENT.md)
- [Accès distant, synchronisation et déploiement robuste](docs/ACCES-DISTANT-ET-SYNCHRONISATION.md)
- [Tests et critères de validation](docs/TESTS.md)
- [Registre des décisions](docs/DECISIONS.md)
- [Consignes Codex](AGENTS.md)

## État de réalisation

- [x] Objectif et responsabilités cadrés.
- [ ] Accès distant au mini-PC qualifié et système de synchronisation/déploiement distant reproductible.
- [ ] Capacité d'émulation Bluetooth HID vérifiée.
- [ ] Prototype contrôlant le PC Windows par Bluetooth.
- [ ] API de commandes intégrée et protégée.
- [ ] Déploiement reproductible et tests validés.

Voir [PLANNING.md](docs/PLANNING.md) pour les prochaines tâches et leurs dépendances.

## Gouvernance légère

**Codex Desktop** : implémentation, tests et déploiements techniques, avec preuves. **ChatGPT** : responsabilité de la documentation de référence, de la revue de code et des critères de validation. **Utilisateur** : arbitrages de périmètre et autorisations d'opérations sensibles. Aucune fusion ou mise en production n'est implicite.
