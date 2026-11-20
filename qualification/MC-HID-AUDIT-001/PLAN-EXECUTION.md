# Plan du mandat exécutoire unique

Ce plan forme un seul mandat avec portes de sécurité. Un échec ordinaire est
corrigé dans le même mandat ; une porte intrusive attend l'autorisation prévue.

## 0 — Préconditions et gel des contrats

- créer branche de réalisation et état de rollback ;
- exécuter `Inspect-MonOrdinateur.ps1` sur la cible et archiver une preuve
  expurgée ;
- vérifier Windows, .NET, Bluetooth HID Host, session, réseau, écrans et DPI ;
- faire arbitrer R1 à R5 et les six autorisations listées dans `DECISIONS.md` ;
- figer schéma position, interfaces internes, rapport HID et critères.

**Porte :** arrêt si cible incompatible, absence de canal privé ou décision
manquante ayant un impact système.

## 1 — Socle testable sans matériel

- implémenter modèles de commande, TTL, idempotence, limites et état boutons ;
- implémenter `SimulatedHogpTransport` et snapshots position simulés ;
- implémenter boucle de correction déterministe, stale/topology/session guards ;
- implémenter serveur HTTPS/HMAC et tests anti-rejeu ;
- construire l'agent : mesure latest-only, séquence, WTS lock/session, backoff,
  indicateur visible, DPAPI ; aucune route de réception de commande ;
- tests unitaires et d'intégration loopback avec pertes/latence simulées.

**Sortie :** zéro dépendance Bluetooth, tests de sécurité/état exhaustifs, agent
inspectable et désinstallable par suppression de ses fichiers/configuration.

## 2 — Moteur HOGP hors émission

- installer/valider la chaîne autorisée ; verrouiller versions et script build ;
- créer table HID/Battery, valeurs statiques, Report Reference et handlers ;
- parser le Report Map dans un test et tester sérialisation/désérialisation ;
- coder machine d'état, événements d'abonnement/session et `release_all` ;
- vérifier que l'arrêt libère toutes ressources sans appeler la publicité dans
  les tests par défaut.

**Sortie :** binaire signé par hash, tests locaux et inspection de la table. Si
Device Information réservé bloque la conformité, documenter le comportement
système avant toute publicité.

## 3 — Porte Bluetooth matérielle bornée

Après autorisation : radio active, moteur au premier plan, publicité
découvrable temporaire, appairage Windows volontaire, inspection de la table et
chargement du pilote souris. Envoyer successivement : rapport nul, mouvement
minimal dans une zone sûre, clic seulement après validation séparée, puis
libération. Tester arrêt, déconnexion et reconnexion.

**Preuves :** horodatages, transitions anonymisées, erreurs WinRT, abonnement,
pilote HID chargé et observation cible ; aucune adresse Bluetooth publiée.

**Repli :** corriger table/permissions une fois ; si la pile Windows/Realtek ne
peut pas exposer un HOGP conforme, qualifier un module externe derrière la même
interface, sans achat automatique.

## 4 — Canal position réel

- installer manuellement l'agent dans la session cible ; afficher état et arrêt ;
- provisionner certificat épinglé et clé DPAPI ;
- ouvrir uniquement la règle mini-PC autorisée si les tests l'exigent ;
- mesurer cadence, RTT, gigue, pertes, verrouillage, changement de session,
  multi-écrans, coordonnées négatives et DPI ;
- valider refus certificat/signature/replay et absence de commandes vers agent.

**Sortie :** 20 Hz soutenus ou cadence ajustée par mesure, âge 95e percentile
documenté, arrêt du contrôle lors de toute invalidité.

## 5 — Boucle complète et calibration

- calibrer gains et saturations sur grille d'écrans, vitesses/accélérations ;
- exécuter positions proches/lointaines/bords/coordonnées négatives ;
- introduire latence/pertes et mouvement physique concurrent ;
- vérifier tolérance sur trois mesures, timeout, stale 150 ms, max itérations ;
- tester clics/scroll seulement une fois le déplacement stable ;
- exécuter watchdog boutons et arrêt d'urgence à chaque état.

**Critères initiaux :**

- 99 % de commandes atteignent la cible dans 2 s sur la matrice convenue ;
- erreur finale <= 2 px sur trois mesures, P95 <= 4 px ;
- aucun mouvement avec mesure > 150 ms ou mauvaise topologie/session ;
- aucune pression maintenue après arrêt, exception, déconnexion ou reconnexion ;
- arrêt observé <= 250 ms ;
- aucun replay réseau/commande expirée accepté ;
- aucun endpoint agent ne permet d'exécuter une commande.

Les seuils peuvent être ajustés uniquement à partir des mesures publiées.

## 6 — Robustesse, packaging et livraison

- tests longue durée, reconnexions, redémarrages et ressources ;
- packaging par SHA, configuration d'exemple, journaux bornés, install/uninstall
  réversibles ; démarrage au logon seulement si décidé ;
- documenter santé, arrêt, rotation clés/certificat et rollback ;
- suite complète, secret scan, preuves expurgées et PR Draft ; aucune fusion.

## Matrice de traçabilité

| Hypothèse | Test de levée |
|---|---|
| Windows peut créer la table HOGP | CreateAsync radio active + inspection GATT |
| DIS réservé satisfait HOGP | découverte Host/analyse table et PnP ID |
| cible charge souris native | appairage + pilote HID + mouvement borné |
| chiffrement/bonding effectifs | propriétés session et reconnexion après redémarrage |
| agent lit le bon curseur | session active, lock/unlock, RDP/console si applicable |
| coordonnées cohérentes | grille multi-écrans/DPI avec points négatifs |
| LAN assez frais | RTT/gigue/âge P50/P95/P99 et coupures |
| boucle précise | matrice statistique, pas un exemple isolé |
| souris physique sûre | trajectoires concurrentes + arrêt ; Raw Input si échec |
| arrêt libère les boutons | injection de fautes à chaque transition |
