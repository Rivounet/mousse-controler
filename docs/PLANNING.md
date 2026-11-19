# Planning opérationnel — progression par jalons

Il n'y a **aucune date cible obligatoire**. Les tâches passent par : **À faire → En cours → En revue → Validé** ; **Bloqué** indique un obstacle documenté. Un passage à *Validé* nécessite une preuve ou une revue adaptée.

## Prochaines tâches (ordre recommandé)

| ID | Jalon | Travail | Responsable d'exécution | Livrable/preuve | État |
|---|---|---|---|---|---|
| MC-001 | J0 | Publier la documentation de référence | ChatGPT | Documents du dépôt | Validé |
| MC-002 | J1 | Inventorier mini-pc-backend (OS, Bluetooth, versions, accès) **sans modification** | Codex Desktop | Rapport de diagnostic reproductible | À faire |
| MC-003 | J1 | Qualifier le canal de déploiement PC → mini-PC | Codex Desktop | Test de connexion/transfert et collecte de logs | À faire |
| MC-004 | J2 | Mesurer le rôle périphérique BLE/HID disponible sur le mini-PC | Codex Desktop | Matrice matériel/OS, résultats et limites | À faire |
| MC-005 | J2 | Tester l'appairage et un mouvement HID minimal | Codex Desktop | Démonstration + traces côté émetteur/cible | À faire |
| MC-006 | J3 | Définir le contrat API et le moteur de commandes | Codex Desktop | Contrat versionné, tests automatisés | À faire |
| MC-007 | J3 | Intégrer le Bluetooth HID et les sécurités | Codex Desktop | Démo API → souris sur PC Windows | À faire |
| MC-008 | J4 | Automatiser l'installation, démarrage, arrêt et rollback | Codex Desktop | Procédure testée sur mini-PC | À faire |
| MC-009 | J5 | Qualifier robustesse, déconnexions, sécurité, non-régression | Codex Desktop | Rapport et preuves | À faire |
| MC-010 | J5 | Effectuer la revue finale du code et de la documentation | ChatGPT | Verdict motivé + réserves | À faire |

## Définition de « terminé »

Une tâche technique est terminée quand ses changements sont localisés, ses tests et leurs résultats sont rapportés, et son comportement est vérifié sur **mini-pc-backend** quand pertinent. Le code ne passe pas en `main` sans revue de ChatGPT et décision de fusion explicite. Une tâche documentaire n'est terminée qu'après publication GitHub et vérification des liens/cohérences.

## Cadence de travail

1. Choisir **une tâche ciblée**, avec un résultat observable.
2. Codex Desktop annonce périmètre, diagnostic initial et risques, puis implémente localement.
3. Codex transfère sur mini-PC, exécute les tests réels autorisés et fournit logs, commandes et résultats.
4. ChatGPT réalise revue de code / documentation et publie son verdict : **PASS**, **PASS_WITH_RESERVATIONS** ou **NO-GO**, avec motifs.
5. Une intégration ou fusion ne se fait qu'après autorisation applicable.

Pour les tâches longues, Codex doit communiquer des points de progression aux étapes clés avec le temps écoulé et les éventuels blocages.

## Mise à jour

Maintenir ce tableau à jour lors de chaque revue de jalon ; utiliser les GitHub Issues pour le suivi détaillé lorsque les travaux commencent, sans recopier tout leur contenu ici.
