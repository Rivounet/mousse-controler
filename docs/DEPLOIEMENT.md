# Développement, déploiement et exécution

## Séparation stricte

| Environnement | Utilisation | N'y faire pas |
|---|---|---|
| PC Windows / Codex Desktop | Édition, compilation, tests unitaires, Git et lancement des opérations distantes | Ne pas considérer un test local comme preuve du comportement Bluetooth réel |
| mini-pc-backend | Exécutables, API, émission Bluetooth, journaux, tests d'intégration et d'endurance | Ne pas développer directement dans des dossiers système ou écraser des services existants |
| PC Windows cible | Appairage et réception HID native | Aucun service/agent spécifique de contrôle à installer |

Le PC Windows de développement est aussi **le PC cible** : les tests de mouvement/clic doivent être explicitement supervisés, pour éviter toute commande involontaire sur une session de travail active.

## Préparation nécessaire (J1)

Avant tout déploiement, relever et conserver :
1. OS/édition/version du mini-PC, permissions disponibles et services déjà actifs.
2. Adaptateur et pile Bluetooth, état des pilotes, capacité périphérique BLE.
3. Réseau, moyen d'accès distant **déjà autorisé**, emplacement de déploiement dédié et stratégie de sauvegarde.
4. Commandes et résultats d'un diagnostic **en lecture seule**.

**Aucun SSH, WinRM, partage SMB ou autre canal n'est présumé prêt.** Choisir l'outil le plus simple après inventaire. Ne jamais committer mots de passe, clés privées ni jetons.

## Cycle cible (à automatiser une fois qualifié)

1. Codex crée une branche courte à partir de `main` et apporte une modification ciblée.
2. Exécute les vérifications locales pertinentes.
3. Prépare un artefact versionné/reproductible, avec SHA Git identifié.
4. Transfère l'artefact dans un répertoire dédié sur mini-pc-backend.
5. Arrête proprement l'instance de test précédente si nécessaire, effectue un déploiement réversible et lance l'application.
6. Vérifie l'état du service et réalise les tests autorisés avec le PC cible.
7. Récupère sorties, logs, erreurs et SHA effectivement déployé.
8. Rédige le résultat, soumet le code à revue ChatGPT ; la fusion reste distincte du déploiement de test.

## Critères de sécurité

- Démarrer sur commande ; ne pas rendre le service persistant au démarrage avant décision explicite.
- Conserver une méthode d'arrêt d'urgence utilisable depuis le mini-PC et isoler les tests Bluetooth.
- Interdire des modifications non liées aux travaux sur mini-pc-backend.
- Définir un rollback documenté avant tout remplacement d'une version fonctionnelle.
- Ne pas exposer l'API sur Internet ; ne pas exposer de port LAN sans décision et authentification.

## État actuel

La méthode de connexion, les chemins, les outils de compilation et les scripts sont **à définir après qualification J1**. Ce document évite volontairement des commandes de déploiement fictives.
