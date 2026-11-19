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

**Cycle :** mandat ChatGPT **fourni dans le chat, non archivé dans GitHub** → travaux Codex → rapport, SHA, diff/PR et preuves sur GitHub → revue ChatGPT (PASS / PASS_WITH_RESERVATIONS / NO-GO) → décision utilisateur si nécessaire → mise à jour documentaire. Ne jamais présenter une validation de ChatGPT comme une exécution ou une supervision continue automatique : elle intervient à la demande, sur preuves consultables.

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

**Qualifié selon le rapport et les preuves expurgées de la [PR #1](https://github.com/Rivounet/mousse-controler/pull/1) (examinés par ChatGPT) :** Windows 11 Famille sur le poste de développement, Windows 11 Pro sur mini-pc-backend ; accès SSH par clé et listing SFTP réussis ; adaptateur Realtek sur les deux PC et indicateur WinRT de rôle périphérique BLE positif. Le mini-PC dispose d'un compte SSH administrateur : privilégier les droits minimaux pour les opérations courantes.

**MC-INIT-002 (preuves examinées en [PR #2](https://github.com/Rivounet/mousse-controler/pull/2)) :** 31 tests locaux déclarés PASS et code lu ; 13 empreintes SHA-256 publiées revérifiées ; SSH, UTF-8, délais, transfert SFTP aller-retour d'un témoin de 63 octets, nettoyage borné et arrêt d'un processus témoin au cours d'une session SSH démontrés sur pièces. Le compte distant reste administrateur.

**Non démontré :** livraison d'une release Git par SHA, démarrage persistant après déconnexion SSH, gestion applicative des processus, santé, verrou de déploiement et rollback, émission GATT/HID, appairage et mouvement de souris. La compatibilité HID reste ouverte. Ne pas confondre une spécification publiée avec un logiciel déjà fonctionnel.

**Git pendant MC-INIT-001 :** `main` local conservé à `84dbade9fe74ed8c38f4aa1b089a44c194dfa288` ; `origin/main` observé à `1527797a555b97ae2bced2b1864f1a010422cb9a` après fetch. Avant la suite, vérifier de nouveau les SHA et effectuer un fast-forward seulement si l'état local le permet et si le mandat l'autorise. Aucun push ou commit Codex déclaré. Ces références sont un instantané du rapport, pas une affirmation de l'état Git actuel.

**Jalons :** J0 validé ; **J1 validé avec réserves** (SSH et transfert réversible qualifiés, automatisation applicative reportée à J4) ; J2 HID non qualifié ; J3 API à faire ; J4 déploiement robuste à faire ; J5 qualification MVP à faire.

## 6. Prochaine action

**MC-INIT-001** : exécuté selon le rapport du 19 novembre 2026 ; [revue ChatGPT](REVUES/MC-INIT-001.md) = **PASS_WITH_RESERVATIONS** après lecture des preuves publiées. **Publication MC-INIT-001 : PASS**, PR #1 Draft au SHA `8886cab1230039add8e2712a5114c4e312c0f49b`, sans fusion. **J1 reste ouvert.**

**MC-INIT-002** : terminé avec réserves, [revue](REVUES/MC-INIT-002.md) publiée après examen des 14 fichiers de la PR #2 au SHA `cf3c37200541d3291f6b506731e14ce020bcf630`. **PR #1 et PR #2 sont en Draft, non fusionnées.**

**Prochaine étape :** décider de l'intégration séparée des PR #1 et #2 avant la réalisation de la chaîne de release. Mandat MC-INIT-003 à fournir intégralement dans le chat, sans fichier GitHub : sync par SHA, staging, version active, arrêt et rollback sous tests contrôlés, sans HID et sans modification système implicite.

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

## Règle des mandats et publication des preuves

**Mandats Codex :** uniquement dans le chat, en version intégrale et directement copiable. Le dépôt ne contient aucun fichier de mandat ; la reprise s'appuie sur les décisions, jalons, revues et livrables, sans copier les consignes opérationnelles de mandat dans GitHub.

## Publication des preuves et revues

**Règle permanente :** Codex publie les rapports et preuves nécessaires aux revues dans GitHub, sur une branche dédiée et une PR Draft, sous `qualification/<MANDAT>/`. Les données brutes sensibles restent hors dépôt public. ChatGPT lit directement la PR et les preuves, sans demander un transfert manuel à l'utilisateur. Le rapport MC-INIT-001 a été transmis séparément avant cette règle ; les preuves de MC-INIT-001 et MC-INIT-002 ont été publiées et relues dans les PR #1 et #2 ; toute nouvelle preuve suit le même processus.
