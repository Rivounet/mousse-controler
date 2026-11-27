# MC-ARCHITECTURE-CONVERGENCE-001 — rapport de livraison

## Objectif

Rétablir une architecture en couches et un runtime reproductible sans changer
les contrats HID, les protections réseau ni le rôle de PositionAgent.

## Constat d'entrée

- tâche contrôleur active depuis un worktree comportant quatre fichiers suivis
  modifiés avant le démarrage ;
- voies historique et moderne sérialisées seulement au niveau des primitives ;
- position et topologie publiées sous deux verrous ;
- modèle de releases documenté mais non utilisé par la tâche réelle.

## Livraison

- `application.py` : façade des cas d'usage et cycle des séquences ;
- `orchestration.py` : bail exclusif commun aux actions, séquences et commandes
  historiques ;
- `feedback.py` : publication atomique position/topologie ;
- `CommandGateway` limité au protocole, à l'authentification, à l'idempotence et
  au routage de contrats ;
- release contrôleur extraite des objets Git d'un SHA propre, manifeste et
  empreintes vérifiés avant inscription de tâche et avant lancement ;
- portage des correctifs non commités observés sur le runtime : attente de
  feedback initial, reprise HOGP bornée et publication terminale sûre.

## Preuves logicielles

Les tests dédiés couvrent l'ancien scénario d'interférence
`hold(left) + legacy move`, l'annulation avant acquisition, l'atomicité du
feedback et les altérations de release. Le profil officiel `software` a réussi
sur l'arbre de développement le 27 novembre 2026 en 239,14 s ; ce passage ne
vaut pas qualification du SHA publié, car il précédait le commit de livraison.

La preuve de livraison est le profil `full-local` exécuté après commit sur le
SHA exact publié. Son verdict, son répertoire local et ses exclusions doivent
être portés dans la PR Draft sans publier de chemins privés ou secrets.

## Exclusions et activation

Aucun Bluetooth, HID, capture réelle, accès distant, installation, arrêt du
runtime actif ou modification de tâche n'est exécuté par ce chantier. La
fusion et l'activation d'une release sont deux décisions séparées. Avant
activation : sauvegarde des persistances, vérification du rollback et contrôle
de santé non matériel obligatoires.
