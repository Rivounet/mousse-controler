# Rapport MC-REPRISE-001

**Date :** 19 novembre 2026  
**Verdict Bluetooth HID :** `GO_WITH_RESERVATIONS`

## 1. État de mini-pc-backend

Le diagnostic a été exécuté localement et sans modification : Windows 11
Professionnel 26H2, build 26300.9974, architecture x64, Intel Celeron N5105,
Python 3.12.10, Git 2.54.0 et Codex CLI 0.169.1. L'adaptateur est un Realtek,
pilote 1.1061.2312.2501 du 20 mai 2024. `bthserv` est actif ; les services
utilisateur et passerelle audio sont manuels et arrêtés, état normal hors usage.

La racine de projet contenait des releases, staging, état et journaux issus des
travaux antérieurs, mais aucun clone Git. Tous ont été préservés. Le dépôt a été
cloné dans le sous-dossier prévu `source/`.

## 2. État Git/GitHub

`main` distant est au SHA `2b42ea12aaeaeb9dad7512a621e66257f7f8a37a`.
Les PR #1, #2 et #3 sont ouvertes en Draft. #1 est indépendante ; #3 dépend de
#2. Les travaux ont été conservés sur une branche neuve issue de `main`, sans
fusion, suppression, force-push ou réécriture des branches historiques.

## 3. Stratégie de consolidation

La branche de reprise réunit les cinq commits utiles des trois PR au-dessus de
`main`, puis ajoute les diagnostics, la documentation et les preuves de ce lot.
Cette méthode produit une base unique à relire sans modifier les PR historiques.

## 4. Modifications effectuées

- conservation des rapports MC-INIT-001 à 003 et du code de releases locales ;
- diagnostic Bluetooth WinRT reproductible et strictement en lecture seule ;
- découverte des tests depuis la racine ;
- protocole HOGP contrôlé, arrêté avant publicité/appairage/émission ;
- documentation officielle réalignée sur l'exécution locale ;
- reclassification de SSH/SFTP comme capacité de maintenance secondaire.

## 5. Résultats des tests

`python -m unittest discover` : **72 tests PASS en 31,876 s**. Les 69 tests
historiques passent et trois contrôlent le diagnostic Bluetooth. Aucun test ne
contacte `MonOrdinateur` ni n'émet en Bluetooth.

## 6. Architecture simplifiée

Codex, Git, compilation, tests et exécution résident maintenant sur
`mini-pc-backend`. Le clone `source/` reste séparé de `releases/`, `staging/`,
`state/` et `logs/`. L'application future conserve trois frontières simples :
API locale protégée, validation/ordonnancement, adaptateur HID remplaçable.
SSH/SFTP et les releases immuables restent utiles pour maintenance ou rollback,
mais ne sont plus le chemin quotidien de développement.

## 7. Verdict Bluetooth HID

Le matériel réel déclare BLE, rôle périphérique, rôle central et Bluetooth
Classic. Windows expose `GattServiceProvider`, la création de caractéristiques,
les notifications, la publicité BLE et les API d'appairage. La pile Windows
prend en charge HOGP côté hôte et Microsoft documente le serveur GATT.

Ces signaux rendent la voie HOGP crédible. Ils ne prouvent pas que le pilote
Realtek acceptera une publicité HID complète, que le bonding/chiffrement sera
correct ni que `MonOrdinateur` chargera une souris native. Le verdict est donc
`GO_WITH_RESERVATIONS`, jamais `GO`, jusqu'au protocole matériel autorisé.

## 8. Opérations réellement exécutées

Inventaires OS/runtime/Bluetooth, lecture des capacités WinRT, inspection des
services et du pilote, clone Git, inspection GitHub, consolidation non
destructive, tests locaux et mise à jour documentaire.

## 9. Opérations non exécutées

Aucune installation, modification de pilote/service/pare-feu/ACL, création de
service GATT, publicité BLE, appairage, émission HID, événement souris,
déploiement permanent, fusion de PR ou suppression de branche.

## 10. Risques et limitations

- capacité périphérique déclarée mais comportement HOGP non démontré ;
- absence actuelle de toolchain C++/.NET SDK pour construire le prototype ;
- comportement de bonding et reconnexion à mesurer ;
- build Windows 26H2 susceptible d'être une version préliminaire ;
- anciens composants de déploiement consolidés mais non requalifiés à distance
  dans la nouvelle organisation.

## 11. Décision nécessaire

Autoriser ou refuser une session contrôlée couvrant publicité GATT/HID,
appairage avec `MonOrdinateur` puis un mouvement relatif minimal. L'opération,
ses effets et son arrêt sont décrits dans `PROTOCOLE-HID.md`.

## 12. Prochain objectif fonctionnel recommandé

Après autorisation : produire un prototype HOGP minimal au premier plan et
exécuter le protocole. Sans autorisation, ne pas développer l'API applicative ;
conserver le verdict actuel.

## 13. Publication

Branche : `feat/mc-reprise-001-consolidation`. PR Draft :
<https://github.com/Rivounet/mousse-controler/pull/4>. Commit principal de
livraison : `f40344d7acaea7ee5fd034c517a7c012bca5341a`. Le commit de métadonnées
qui ajoute cette référence est rapporté dans la conversation de livraison et à
la tête de la PR. Aucune fusion n'est incluse.
