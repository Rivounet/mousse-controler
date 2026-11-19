# Roadmap — jalons sans échéances fixes

Pilotage par **preuves fonctionnelles**, non par simple disponibilité d'API. **MC-HID-EXEC-001** est le mandat exécutoire global cadré ; son exécution/achèvement n'est pas attesté ici.

| Jalon | Finalité | Critère de sortie | État |
|---|---|---|---|
| J0 — Cadrage | Architecture, exigences, décisions, documentation | Référentiel cohérent | Validé, actualisation en cours |
| J1 — Environnement | Développement local sur mini-pc-backend, Git et tests | Environnement reproductible | Validé |
| J2 — HID natif | Faire reconnaître le mini-PC comme souris BLE HOGP | Publicité, appairage, pilote HID et mouvement réel | En cours — GATT local qualifié, HOGP réel non démontré |
| J3 — Commandes, trajectoires et position | API protégée, agent LAN, séquences de zones et correction | A→B→C, zones rectangle/cercle/polygone, modes temporisé/commandé, trajectoires configurables, mesure réelle et précision testées sur les deux PC | À faire |
| J4 — Exploitation robuste | Installation, état, arrêt, reprise, rollback | Procédures réversibles et sûres sur les deux machines | Partiel — fondations locales historiques |
| J5 — Qualification MVP | Tests matériels, sécurité, robustesse et performances | Rapport avec résultats mesurés et limites | À faire |

## Dépendances et priorités

- PR #4 fusionnée ; PR #1–#3 clôturées. PR #5 Draft sur main : audits et outils à intégrer de manière contrôlée, sans fusion implicite.
- HOGP Windows/Realtek : créations GATT locales réussies radio On, mais service Device Information réservé, publicité, bonding, reconnexion et mouvement non qualifiés.
- MonOrdinateur : agent `GetCursorPos` et retour HTTPS/HMAC à réaliser ; accès distant sécurisé et session interactive à qualifier.
- Les trajectoires courbes, vitesses variables et micro-variations sont des fonctions de mouvement configurables, **sans objectif d'évasion de détection**. La reconnaissance HID standard ne garantit pas qu'une application considère l'usage comme humain.
- Récepteur Logitech Nano exclu du transport de commande ; alternative matérielle HID seulement après décision.

Les jalons restent indépendants des fusions. ChatGPT maintient le référentiel et supervise GitHub ; Codex implémente et publie une PR Draft ; fusion sur autorisation explicite.
