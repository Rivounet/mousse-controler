# MC-POST-MERGE-002 — Synchronisation et qualification post-fusion

**Date :** 20 novembre 2026

**Branche de rapport :** `docs/mc-post-merge-002`

**Référence `main` :** `09fa2fe475cc70c9bdaf375fffc684195207161b`

**Merge PR #8 :** `e0658142a65d8b494f109efa3318c6ea21feac3d`

**Verdict :** `PASS_WITH_RESERVATIONS`

## Synthèse

Le clone de `mini-pc-backend` a été avancé par fast-forward de l'ancien merge
de la PR #6 vers le `main` GitHub attendu. Aucun changement local n'était
présent et aucune réinitialisation destructive n'a été utilisée. Le commit
applicatif de sûreté `e7e26332e56a39cbd2ca915413c313da07c638d9` et la fusion de
la PR #8 sont dans l'ascendance de `main`.

L'agent de production de `MonOrdinateur` était déjà exactement l'artefact
qualifié. Il n'a donc pas été réinstallé. Le contrôleur Python du mini-PC était
en revanche encore un processus lancé avant le correctif fusionné : il ne
publiait pas la durée de rétention des identifiants et le registre `.ids`
n'existait pas. Le seul contrôleur géré a été mis en sécurité, arrêté puis
relancé depuis le `main` synchronisé. Le journal historique a été migré et le
couple `action-journal.jsonl` / `action-journal.jsonl.ids` est désormais présent.

## Git et composants du mini-PC

- `main` local, `origin/main` et la référence demandée concordent au SHA
  `09fa2fe475cc70c9bdaf375fffc684195207161b` ;
- arbre de travail propre avant intervention ; synchronisation par
  `git fetch --prune` puis fast-forward uniquement ;
- tâche `MousseControler-HOGP` : `Running`, déclencheur `AtLogOn`, jeton limité,
  un seul processus contrôleur ;
- lanceur actif identique au lanceur versionné, SHA-256
  `E2B0A993BB31E2B42433EC73A108B0BDE12C9E857613A2A93B7D408FE0FD4C77` ;
- paquet `Rivounet.MousseControler.Hogp` : version `1.0.0.2`, Publisher
  `CN=MousseControler`, statut `Ok`, signature de développement ; son paquet
  qualifié reste référencé par le SHA-256
  `907AFB9E458C7DA5C2B5555581065A310CD8EBC39BC9BB5EAE2CA508A0B12042` ;
- contrôleur, actions, séquences, WebSocket et broker de captures sont chargés
  depuis le `src` du clone `main` ;
- rétention anti-rejeu exposée : 2 592 000 secondes ; journal et `.ids`
  présents ensemble, respectivement 109 710 et 8 329 octets au relevé final ;
- aucune action `ACCEPTED` ou `RUNNING` après reprise ; un ancien `drag`
  terminal reste `UNKNOWN/DRAG_UNCERTAIN`, conformément au contrat, sans rejeu ;
- GATT annoncé, abonnement actif, boutons à zéro, retour de position frais en
  session 1 ;
- l'index de capture n'est pas encore matérialisé car aucune capture conservée
  ni nouvelle demande n'existe après migration. Le broker est chargé et annonce
  les seuls moments autorisés `before` / `after` ; aucune capture n'a été
  déclenchée pour créer artificiellement cet index.

Le premier arrêt de tâche n'a pas terminé son processus enfant dans le délai de
15 secondes. Après l'arrêt d'urgence applicatif, ce processus unique et vérifié
a été terminé comme le prévoit le gestionnaire versionné, puis la tâche a été
relancée. La santé complète a convergé immédiatement après la reprise.

## MonOrdinateur

Le contrôle SSH a d'abord reproduit le refus réseau de la sandbox, puis a réussi
hors sandbox avec la règle limitée au binaire OpenSSH, au fichier dédié et à
l'alias `MonOrdinateur`. Aucun paramètre SSH, compte, ACL, certificat, pare-feu
ou mécanisme de protection n'a été modifié.

- tâche `MousseControler-PositionAgent` : `Running`, `AtLogOn`, niveau limité ;
- un processus `PositionAgent.exe`, dans la même session interactive 1 que
  l'Explorateur Windows ;
- SHA-256 installé
  `0562CC27694964406311C62E963B5F1BA6913B49EE2A3D6B0605F9088FEDF73F`,
  identique à l'artefact qualifié de la PR #8 ;
- configuration présente et inchangée ; mécanisme de capture inclus dans cet
  artefact, sans déclenchement de capture réelle ;
- rollback présent, SHA-256
  `C19B14127CBE1504C74DC53C653494471D2E6827E79D2557A68541D866DC1071` ;
- périphériques Bluetooth et souris natifs en état `OK` ; le retour de position
  reçu par le mini-PC confirme que l'agent et son canal HTTPS/HMAC fonctionnent.

Le code de dernier résultat de la tâche conserve une ancienne tentative de
démarrage refusée (`0x800710E0`), cohérente avec une demande alors que
l'instance était déjà gérée. L'état courant, le processus unique, la session et
le retour de position sont tous sains ; aucune correction cible n'a été requise.

## Qualification non perturbatrice

- compilation Python : PASS ;
- suite complète : **185/185 PASS en 49,178 s** ; temps compilation + suite :
  50,365 s ;
- builds Roslyn `PositionAgent.exe` et `MouseWitness.exe` sous
  `/warn:4 /warnaserror+` : PASS ;
- API de commande sans bearer valide : `401 Unauthorized` ;
- WebSocket sans bearer valide : `401 Unauthorized` ;
- WebSocket authentifié : `ACCEPTED → RUNNING → EXECUTED` pour une attente de
  200 ms, identifiants d'événements uniques, zéro rapport HID ;
- réémission du même `action_id` : rejet `duplicate action id`, aucune seconde
  exécution ;
- GATT `advertising=True`, `subscribed=True`, `buttons=0` ;
- retour de position frais observé à 15 ms au contrôle final ;
- journal et `.ids` conservés ensemble après redémarrage réel du processus.

## Changements réalisés

1. fast-forward du `main` local vers le SHA GitHub attendu ;
2. redémarrage borné de la seule tâche contrôleur locale pour charger le code
   fusionné et migrer le registre anti-rejeu ;
3. création automatique du `.ids` à partir du journal existant ;
4. aucun déploiement ni redémarrage sur `MonOrdinateur`, déjà conforme ;
5. suppression des répertoires temporaires de tests et de builds.

## Réserves et périmètre non retesté

- conformément au mandat, aucun mouvement, clic, défilement, rapport HID réel
  ou capture d'écran réelle n'a été envoyé ; les fonctions matérielles restent
  couvertes par leur qualification antérieure, pas par cette revalidation ;
- l'ancien `drag` à issue incertaine reste volontairement `UNKNOWN` et bloqué,
  sans tentative de normalisation ou de rejeu ;
- les réserves produit existantes demeurent : roulette horizontale absente du
  descripteur, mesure LAN aller simple non absolue et reprise GATT pouvant être
  transitoire avant convergence ;
- le dossier vide historique de staging de maintenance n'a pas été touché ;
- aucune CI GitHub n'est configurée : les résultats proviennent du mini-PC.

La production est opérationnelle, les deux machines utilisent les composants
attendus, les mécanismes de sécurité sont conservés et le rollback cible reste
disponible.
