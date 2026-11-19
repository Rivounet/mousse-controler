# Stratégie de tests et revue technique

## Niveaux de vérification

| Niveau | But | Environnement | Preuve minimale |
|---|---|---|---|
| T0 — Contrôles statiques | Typage, lint, analyse des dépendances quand définis | PC Windows / CI éventuelle | Commandes, versions, statut |
| T1 — Unitaires | Parseur API, limites de valeurs, commandes, arrêt, adaptateur simulé | PC Windows / mini-PC | Rapport automatisé |
| T2 — Intégration technique | Service sur mini-PC, pilote/adaptateur Bluetooth, appairage ; synchronisation et transfert distants | mini-pc-backend + PC cible | Inventaire, SHA, contrôles d'accès et journaux datés |
| T3 — Bout en bout | API → souris : déplacements, clics, scroll | mini-PC + PC cible | Cas testés, résultats observés |
| T4 — Robustesse/sûreté | Coupure Bluetooth, reconnexion, commandes invalides, saturation et arrêt d'urgence | mini-PC + PC cible | Anomalies, repro, correction ou réserve |

## Tests d'acceptation MVP

- Le PC cible reconnaît une souris Bluetooth HID native après appairage.
- Aucun logiciel récepteur propre au projet n'est installé sur le PC cible.
- Un client API autorisé peut commander mouvement relatif, clic gauche/droit et défilement.
- Une commande non autorisée ou malformée n'entraîne aucun événement HID.
- Une déconnexion Bluetooth est détectée ; aucune séquence obsolète ne s'exécute après reconnexion.
- Un arrêt d'urgence stoppe rapidement l'émission ; une souris physique reste fonctionnelle.
- Un cycle de synchronisation/déploiement/retour arrière depuis Codex Desktop est reproductible, avec SHA demandé et SHA observé.
- La synchronisation refuse un clone distant présentant des modifications imprévues, sans les écraser.
- Les actions de déploiement sont idempotentes et exclusives ; une interruption réseau ou un échec de contrôle post-déploiement ne détruit pas la version précédente.
- Une procédure de récupération manuelle documentée existe en cas de perte de connectivité distante.
- Les limites matérielles, versions et conditions de test sont documentées.

## Précautions

Les commandes de souris peuvent déplacer le curseur et cliquer sur une application en cours. Exiger une fenêtre de test volontaire, une procédure d'arrêt et des mouvements de faible amplitude. Les tests ne doivent ni modifier des données non liées, ni installer d'agent sur le PC cible.

## Compte rendu standard d'un lot

- Identifiant du lot, branche et SHA.
- Inventaire des fichiers modifiés, objectif et limites.
- Environnement réellement testé (poste local / mini-PC / cible).
- Commandes lancées et résultats **PASS / FAIL / NON_EXÉCUTÉ**.
- Logs utiles expurgés de secrets.
- Régressions, réserves, retour arrière possible.
- Lien PR ou diff à relire.

## Revue de code — responsabilité ChatGPT

Pour chaque PR avant fusion : vérifier adéquation au besoin, séparation API/HID, compatibilité et gestion d'erreurs, sécurité des commandes, tests réels attestés, impact sur mini-PC et PC cible, qualité de la synchronisation et du rollback, absence d'écrasement Git distant, dette ajoutée, actualisation des documents. Rendre un verdict **PASS**, **PASS_WITH_RESERVATIONS** ou **NO-GO**, justifié par éléments contrôlables.

**Un rapport Codex n'est pas à lui seul une revue indépendante.** ChatGPT examine le diff et les preuves disponibles ; indique explicitement ce qu'il n'a pas pu contrôler. La fusion ou le déploiement durable n'est jamais implicite.
