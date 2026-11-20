# Accès distant et synchronisation — capacité secondaire

## Statut

L'organisation historique utilisait Codex sur `MonOrdinateur` et SSH/SFTP pour
agir sur `mini-pc-backend`. Depuis MC-REPRISE-001, Codex, Git, les tests et
l'exécution résident directement sur mini-pc-backend. Le canal distant n'est
donc plus requis pour le développement courant. Il est en revanche qualifié
comme canal secondaire pour diagnostiquer et piloter les procédures
interactives autorisées sur `MonOrdinateur`.

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

## Canal qualifié vers MonOrdinateur

La forme canonique est :

```powershell
ssh.exe -F $HOME\.ssh\monordinateur-pv-mig.conf MonOrdinateur "whoami"
```

Le fichier dédié impose déjà authentification par clé, `IdentitiesOnly`, mode
batch, vérification stricte de la clé d'hôte et magasin `known_hosts` dédié.
Les adresses, identités de clé et empreintes ne sont pas recopiées ici.

Exécuter d'abord exactement ce contrôle dans la sandbox. Si elle répond par un
refus réseau, relancer la même commande via l'approbation hors sandbox de Codex.
La règle persistante acceptable est strictement limitée à :

```text
ssh.exe -F <fichier dédié> MonOrdinateur
```

Une règle couvrant tout PowerShell, tout SSH, tout hôte ou tout accès réseau est
interdite. Il est également interdit de contourner la vérification d'hôte, de
modifier le pare-feu, les ACL, les comptes ou les protections Windows.

### Distinguer les refus

- connexion refusée uniquement dans la sandbox : filtrage réseau Codex ;
- `whoami` réussi puis opération Windows refusée : droits effectifs, ACL ou
  séparation de session Windows ;
- clé d'hôte refusée : arrêter et faire vérifier l'identité par un canal fiable,
  sans supprimer ni remplacer automatiquement l'entrée connue ;
- processus SSH en session 0 : jamais une preuve qu'une fenêtre est visible.

Pour une interface visible, contrôler le compte/principal et l'action de la
tâche autorisée, son ACL, l'identifiant de la session console et l'identifiant
de session du processus. Une tâche temporaire doit être limitée, porter un nom
fixe, refuser toute tâche homonyme non conforme, puis être supprimée.

### Reprise après interruption

1. refaire le contrôle `whoami` hors sandbox ;
2. relever la session console active et la session du processus attendu ;
3. vérifier nom, principal, action et état des seules tâches gérées ;
4. revérifier les SHA-256 du staging placé dans le profil du compte interactif ;
5. contrôler transport abonné et boutons à zéro avant toute émission ;
6. annoncer toute prise de souris et attendre l'accord explicite ;
7. après l'essai, fermer le témoin, supprimer sa tâche et les fichiers
   temporaires, puis annoncer que la souris est libre.

Un staging sous `C:\Windows\Temp` créé par un autre compte peut être lisible
depuis SSH mais inexécutable par un jeton interactif limité. Ne pas modifier ses
ACL : transférer les artefacts vérifiés dans le répertoire temporaire du profil
interactif.

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

Aucun service, port, règle de pare-feu, compte, ACL, protection Windows ou
paramètre général de Codex n'est créé, élargi ou modifié pour rétablir ce canal.

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
