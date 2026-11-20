# MC-MOUSE-ACTIONS-001 — Rapport de qualification

**Date :** 20 novembre 2026  
**Branche :** `feat/mc-mouse-actions-001`  
**Base :** `4b5e80450931a19adb88312d6f6a3b0ff8e4fd81`  
**Commit applicatif initial :** `597f7401d8bc743aebf9fa018422188460dd0767`  
**Verdict courant :** `INCOMPLETE` — logiciel et mini-PC qualifiés ; session
interactive cible et matrice matérielle étendue ouvertes

## Réalisation

- moteur souris complet à cinq boutons : clic simple/double/triple/multiple,
  appui/relâchement, maintien, combinaisons, drag/drop, déplacement maintenu ;
- roulette verticale unitaire, grande amplitude découpée, continue, bornée et
  interruptible ; horizontale annoncée indisponible sur le HID actuel ;
- séquences arbitraires avec mouvements, actions, attentes, pause/reprise,
  attente de commande, capture et politiques stop/retry/continue ;
- registre d'actions et journal durable anti-rejeu, états et erreurs corrélés ;
- WebSocket loopback authentifié et borné ;
- capture avant/après seulement, sélection du moniteur sous curseur, indication
  visible, PNG signé, stockage privé, quotas, TTL et suppression ;
- agent cible toujours dépourvu d'API d'injection souris.

## Résultats disponibles

Suite complète finale avant intégration cible : **175/175 PASS en 47,857 s**.
Compilation Python réussie.
`PositionAgent.exe` et `MouseWitness.exe` compilent sous Roslyn avec
`/warn:4 /warnaserror+`. Les tests simulés couvrent actions, séquences, états,
WebSocket, HMAC, capture, rétention, annulation, arrêt, inconnue et non-rejeu.

Runtime mini-PC activé sur le contenu du commit applicatif : tâche `Running`,
annonce GATT `Started`, abonnement `True`, boutons `0`, position cible fraîche
(47 ms au contrôle), API commande 8766 et WebSocket 8767 sur loopback. Une
attente de 200 ms a produit via le WebSocket réel trois événements uniques
`ACCEPTED`, `RUNNING`, `EXECUTED`, avec état final corrélé et zéro rapport HID.

Le paquet cible est transféré dans un staging temporaire borné et ses quatre
SHA-256 concordent avec les artefacts locaux. Le compte SSH `codex-remote` est
séparé du compte propriétaire de la tâche interactive et reçoit `Access denied`
sur Task Scheduler/CIM. Cette séparation est conservée : aucune élévation,
nouveau service ou baisse de protection n'a été tentée.

## Qualification encore ouverte

- exécuter l'installateur réversible dans la session visible propriétaire ;
- confirmer agent visible, retour position et reconnexion HOGP après échange ;
- capturer réellement avant/après, vérifier écran sélectionné et conservation ;
- observer sur la fenêtre témoin les clics multiples/central, maintien, boutons,
  drag/drop et roulette ;
- répéter arrêt d'urgence et vérifier aucun événement post-arrêt ;
- collecter uniquement un résumé expurgé, supprimer PNG et fermer le témoin.

Les preuves historiques du MVP démontrent déjà clics gauche/droit, roulette,
positionnement, reconnexion et arrêt matériel, mais elles ne sont pas présentées
comme une exécution du nouveau moteur. Aucune capture réelle, secret, adresse
privée, identité de compte ou journal brut ne sera publié.
