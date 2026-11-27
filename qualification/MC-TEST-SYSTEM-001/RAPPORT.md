# MC-TEST-SYSTEM-001 — assemblage et déterminisme

## Objectif

Ajouter une preuve hermétique au niveau application et réduire les attentes
temporelles fragiles, sans solliciter de HID, Bluetooth, capture, DPAPI, SSH,
installation ou déploiement.

## Architecture livrée

- `build_runtime` compose explicitement services, contrôleurs, registre,
  exécuteur et passerelles ;
- `register_runtime_servers` porte la responsabilité unique de créer les trois
  serveurs du processus ;
- `RuntimeFactories` rend injectables les seules frontières de processus et de
  matériel, tandis que le chemin de production conserve ses adaptateurs réels ;
- le profil `integration` découvre désormais `tests/system` comme famille
  distincte ;
- les boucles de polling modifiées utilisent une attente commune bornée avec un
  diagnostic de dépassement.

## Preuve système

Le scénario système exécute le graphe applicatif réel avec serveurs HTTP et
WebSocket réels sur loopback et ports éphémères. Il vérifie une position HMAC,
le contrôle d'accès de la commande, la lecture de position, la soumission d'une
attente, ses états `ACCEPTED`, `RUNNING`, `EXECUTED`, puis le nettoyage. Le
double HOGP enregistre les appels et la preuve refuse tout mouvement, bouton ou
défilement.

## Vérifications de développement

- 5 tests ciblés assemblage/convergence : PASS ;
- 123 tests touchés unitaires, intégration et système : PASS en 113,299 s ;
- compilation Python des modules modifiés : PASS.

La preuve officielle `full-local` est publiée sur la PR Draft après commit, avec
SHA, empreinte d'arbre, compteurs, durées et empreintes d'artefacts.

## Exclusions

Aucune opération matérielle, aucune capture, aucun secret réel, aucun accès
réseau externe et aucune mutation de tâche Windows. Le serveur de position du
scénario système est en HTTP loopback ; la terminaison TLS réelle reste couverte
par les tests d'intégration dédiés.
