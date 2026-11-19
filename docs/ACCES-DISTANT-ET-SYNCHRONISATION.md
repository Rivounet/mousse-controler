# Accès distant et synchronisation — capacité secondaire

## Statut

L'organisation historique utilisait Codex sur `MonOrdinateur` et SSH/SFTP pour
agir sur `mini-pc-backend`. Depuis MC-REPRISE-001, Codex, Git, les tests et
l'exécution résident directement sur mini-pc-backend. Le canal distant n'est
donc plus requis pour le développement courant.

Les travaux des PR #2 et #3 sont conservés : ils ont de la valeur pour une
future maintenance à distance, la livraison d'artefacts immuables et le rollback.
Ils ne doivent pas être supprimés ni présentés comme une dépendance du MVP HID.

## Capacités conservées

- diagnostic d'hôte et de chemins en lecture seule ;
- plan de synchronisation sans contact réseau ;
- client SSH/SFTP strict et borné ;
- manifeste et empreintes d'artefact issus d'un SHA exact ;
- staging, verrou, activation, santé, arrêt et rollback locaux simulés/testés ;
- erreurs explicites, refus des chemins dangereux et protection des états sales.

Les rapports MC-INIT-002 et MC-INIT-003 distinguent ce qui a été exécuté,
simulé ou seulement conçu. MC-REPRISE-001 n'a relancé aucun accès distant.

## Usage autorisé à l'avenir

Une maintenance distante peut être retenue si l'utilisateur souhaite administrer
mini-pc-backend depuis une autre machine. Avant toute écriture :

1. vérifier l'identité de l'hôte et l'empreinte connue par un canal fiable ;
2. utiliser un compte aux droits minimaux et une clé hors dépôt ;
3. contrôler l'état Git, le chemin autorisé, l'espace et les points de reprise ;
4. commencer par `doctor`, `status` et `--dry-run` ;
5. cibler un SHA immuable, jamais une branche mouvante ;
6. refuser un clone sale ou une release existante incohérente ;
7. rapatrier uniquement des preuves expurgées.

Aucun service, port, règle de pare-feu, compte ou ACL n'est créé ou modifié sans
autorisation spécifique.

## Interface historique

| Action | Statut / rôle secondaire |
|---|---|
| `doctor` | diagnostic en lecture seule |
| `sync --ref <SHA> --dry-run` | plan sans mutation |
| `sync --ref <SHA>` | à requalifier avant usage réseau réel |
| `deploy --ref <SHA>` | modèle de release locale, usage distant à requalifier |
| `status`, `logs` | inspection et collecte expurgée |
| `stop`, `rollback` | arrêt/retour arrière contrôlés |

## Source de vérité

GitHub reste la référence versionnée. Le clone `source/` de mini-pc-backend est
le clone de développement courant ; les dossiers `releases/` ne sont pas des
dépôts concurrents. Aucun `git reset --hard`, `git clean -fdx`, `git pull`
aveugle, force-push ou écrasement d'un état inconnu.

## Critère de remise en priorité

Ce composant redevient prioritaire uniquement si une exigence de maintenance à
distance est décidée. Il faudra alors requalifier le canal réel, l'idempotence,
les erreurs réseau et un rollback observable. Cela ne bloque ni le diagnostic
HOGP ni le développement local actuel.
