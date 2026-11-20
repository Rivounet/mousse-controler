# MC-MOUSE-ACTIONS-001 — Rapport de qualification

**Date :** 20 novembre 2026

**Branche :** `feat/mc-mouse-actions-001`

**Base :** `4b5e80450931a19adb88312d6f6a3b0ff8e4fd81`

**Commit applicatif initial :** `597f7401d8bc743aebf9fa018422188460dd0767`

**Verdict courant :** `PASS_WITH_RESERVATIONS` — logiciel, canal SSH, session
interactive et matrice matérielle réelle qualifiés

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

Suite complète finale après intégration cible : **177/177 PASS en 44,286 s**.
Compilation Python réussie.
`PositionAgent.exe` et `MouseWitness.exe` compilent sous Roslyn avec
`/warn:4 /warnaserror+`. Les tests simulés couvrent actions, séquences, états,
WebSocket, HMAC, capture, rétention, annulation, arrêt, inconnue et non-rejeu.

Runtime mini-PC activé sur le contenu du commit applicatif : tâche `Running`,
annonce GATT `Started`, abonnement `True`, boutons `0`, position cible fraîche
(47 ms au contrôle), API commande 8766 et WebSocket 8767 sur loopback. Une
attente de 200 ms a produit via le WebSocket réel trois événements uniques
`ACCEPTED`, `RUNNING`, `EXECUTED`, avec état final corrélé et zéro rapport HID.

## Qualification SSH et Windows

La définition `MonOrdinateur` a été trouvée dans le fichier SSH dédié, avec clé
exclusive, mode batch, vérification stricte et magasin d'hôte dédié. La même
commande `whoami` est refusée par la sandbox au niveau réseau puis réussit hors
sandbox. Une règle d'approbation persistante a été limitée au binaire SSH, au
fichier dédié et à cet alias.

Le compte distant effectif correspond au principal de la tâche interactive et
dispose d'un droit explicite sur celle-ci ; l'identité exacte est expurgée du
dépôt. La session SSH est 0, la console active est 1 et l'agent/témoin ont été
observés en session 1. Le lancement direct par SSH n'est donc pas retenu.

Un premier staging créé par le compte de maintenance sous `C:\Windows\Temp` a
produit `0x80070005` avec le jeton interactif limité. Aucune ACL n'a été changée :
les mêmes artefacts, vérifiés par SHA-256, ont été transférés dans le profil du
compte interactif. L'agent a été mis à jour avec sauvegarde de rollback et sa
tâche persistante est restée limitée et `Running`.

## Qualification matérielle réelle

Après accord explicite de disponibilité de la souris, 17 actions ont été
exécutées dans la surface sûre : position absolue confirmée, clics gauche
simple/double/triple, droit, milieu, précédent, suivant, combinaison
appui/relâchement, maintien, glisser confirmé, retour confirmé, roulettes
discrète/continue et séquence composée. Tous les identifiants d'événements
WebSocket sont uniques ; les actions positionnelles terminent `CONFIRMED`, les
autres `EXECUTED`.

Le témoin corrigé a observé 37 messages : clics gauche/droit/milieu, doubles,
boutons X, glisser et roulette. Tous les événements d'action sont restés dans
la surface sûre. Deux PNG réels avant/après, 1920×1080, ont été reçus. Les
sources plein écran ont été supprimées et vérifiées absentes ; seules leurs
versions recadrées 884×611 sur la surface témoin sont publiées dans `evidence/`
après contrôle visuel d'absence de contenu extérieur.

L'arrêt d'urgence a annulé la séquence en attente avant son clic. Le témoin a
reçu zéro événement après l'acceptation de l'arrêt. Après redémarrage, le
transport est revenu `Started`, `subscribed=True`, boutons `0`; le journal
durable contient zéro action `ACCEPTED/RUNNING` et conserve l'action d'urgence
en `CANCELLED`, sans rejeu.

La tâche témoin, son processus, le staging du profil interactif et tous les PNG
sources ont été supprimés. Les deux PNG recadrés de preuve restent uniquement
dans le dossier du mandat. La tâche de production et le rollback de l'agent
sont préservés. L'ancien staging de maintenance ne contient plus aucun fichier ;
son dossier vide subsiste car Windows refuse sa suppression au compte
propriétaire, et ses ACL n'ont pas été modifiées.

## Réserves

- la roulette horizontale reste indisponible par conception du descripteur HID ;
- toute nouvelle qualification visible doit être annoncée et recevoir un accord
  explicite pour ne pas interrompre l'usage humain de la souris ;
- le dossier vide de staging de maintenance reste à supprimer par une opération
  Windows disposant déjà du droit approprié, sans changement d'ACL.
