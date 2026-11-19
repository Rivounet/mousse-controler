# Reprise du projet Mousse-controler

**Dernière consolidation : 19 novembre 2026 — MC-REPRISE-001.** Ce document est
le point d'entrée d'une nouvelle session. Les mandats complets restent dans le
chat et ne sont pas archivés dans le dépôt.

## Objectif

`mini-pc-backend` doit se présenter comme souris Bluetooth HID auprès de
`MonOrdinateur`, qui utilise sa pile et ses pilotes natifs. Un agent utilisateur
séparé y publiera uniquement la position réelle du curseur sur LAN privé ; une
API locale protégée commandera mouvement, clic et défilement.

## Organisation actuelle

| Élément | Rôle |
|---|---|
| `mini-pc-backend` | Codex, Git, développement, tests, exécution, future API et émission HOGP |
| `MonOrdinateur` | cible Windows Bluetooth HID + futur agent visible de position sans commande entrante |
| GitHub | source officielle et PR Draft |

Le clone Git est dans le sous-dossier local `source/`, séparé des releases,
staging, états et journaux d'exécution. SSH/SFTP reste une capacité secondaire de
maintenance, non une étape du développement courant.

## État vérifié

### Machine

- Windows 11 Professionnel 26H2 x64, build 26300.9974 ;
- Intel Celeron N5105, Python 3.12.10, Git 2.54.0, Codex CLI 0.169.1 ;
- adaptateur Realtek, pilote 1.1061.2312.2501 ;
- service Bluetooth principal actif.

### Git et tests

`origin/main` a été observé à
`2b42ea12aaeaeb9dad7512a621e66257f7f8a37a`. Les PR #1, #2 et #3 restent
ouvertes en Draft. #1 est indépendante ; #3 est empilée sur #2. Leurs cinq
commits utiles sont conservés dans la branche de consolidation issue de `main`,
sans fusion ni réécriture des branches historiques.

`python -m unittest discover` exécute désormais **78 tests**, tous réussis sur
mini-pc-backend (72 à la consolidation, puis six gardes d'audit). La
découverte racine qui annonçait auparavant zéro test est corrigée.

### Bluetooth HID

Le matériel retourne `true` pour BLE, le rôle périphérique et le rôle central.
Les API WinRT de serveur GATT, création de caractéristiques, notification,
publicité et appairage sont présentes. La documentation Microsoft et la
spécification Bluetooth SIG rendent une implémentation HOGP crédible.

**Verdict : `GO_WITH_RESERVATIONS`.** Aucun service GATT n'a été créé, aucune
publicité démarrée, aucun appairage effectué et aucun événement HID émis. Ces
étapes sont indispensables avant `GO`.

MC-HID-AUDIT-001 a défini l'architecture deux canaux et le plan de réalisation.
Son probe GATT non diffusé a trouvé la radio `Off` et a reçu
`RadioNotAvailable` ; aucune opération sensible n'a été exécutée. MonOrdinateur
n'était pas accessible : son script de diagnostic est prêt, mais ses
caractéristiques restent inconnues.

MC-HID-AUDIT-002 a confirmé que Realtek/PnP/pilote/services sont sains : l'état
Bluetooth est `Off`, non `Disabled`, et explique immédiatement
`RadioNotAvailable`. Une activation autorisée reste nécessaire pour démontrer
`CreateAsync` radio On. Aucun accès natif à MonOrdinateur n'est configuré depuis
le mini-PC ; la cible reste `INCOMPLETE` et le diagnostic schéma 2 est prêt.

## Réalisé, simulé, non qualifié

| Domaine | État |
|---|---|
| Inventaire local et diagnostic Bluetooth | Réalisé en lecture seule |
| Consolidation des trois PR historiques | Réalisée localement, publication à finaliser |
| Tests artefacts/releases/distant hors ligne | 69 PASS |
| Tests diagnostics Bluetooth/cible et garde anti-publicité | 7 PASS |
| Release locale et rollback | Modèle et tests présents ; activation applicative réelle à requalifier |
| SSH/SFTP | Qualifié historiquement, non relancé dans la nouvelle organisation |
| Service HOGP, publicité, bonding, mouvement | Non exécutés — autorisation requise |
| API de commandes | Non développée |

## Prochaine action

Décider l'autorisation du
[`PROTOCOLE-HID.md`](../qualification/MC-REPRISE-001/PROTOCOLE-HID.md). Il
prévoit un prototype au premier plan, arrêt par `Ctrl+C` avec
`StopAdvertising()`, appairage volontaire et mouvement de cinq pixels dans une
surface sûre. Sans autorisation, ne pas passer au développement complexe de
l'API. Exécuter auparavant le diagnostic cible et arbitrer les décisions de
[`MC-HID-AUDIT-001`](../qualification/MC-HID-AUDIT-001/DECISIONS.md).
Les portes complémentaires sont décrites dans
[`MC-HID-AUDIT-002`](../qualification/MC-HID-AUDIT-002/RAPPORT.md).

## Sources de vérité

- [Rapport MC-REPRISE-001](../qualification/MC-REPRISE-001/RAPPORT.md)
- [Audit MC-HID-AUDIT-001](../qualification/MC-HID-AUDIT-001/RAPPORT.md)
- [Complément MC-HID-AUDIT-002](../qualification/MC-HID-AUDIT-002/RAPPORT.md)
- [Roadmap](ROADMAP.md) et [planning](PLANNING.md)
- [Architecture](ARCHITECTURE.md)
- [Déploiement local](DEPLOIEMENT.md)
- [Accès distant secondaire](ACCES-DISTANT-ET-SYNCHRONISATION.md)
- [Tests](TESTS.md), [décisions](DECISIONS.md) et [consignes Codex](../AGENTS.md)

## Gouvernance

D-021 : mandats exclusivement dans le chat. D-022 : pas de revue automatique à
chaque livraison. D-023 : autonomie technique de Codex dans les limites
explicites. Aucune fusion, publicité Bluetooth, modification système ou émission
HID n'est implicite.
