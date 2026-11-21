# Développement, activation et retour arrière locaux

## Principe

Le développement et l'exécution ont lieu sur la même machine,
`mini-pc-backend`. Il n'existe plus de transfert obligatoire depuis un poste de
développement distinct. La séparation importante est désormais **logique** :
clone Git, artefacts, releases actives, état et journaux.

| Zone | Usage | Règle |
|---|---|---|
| `source/` | clone Git, branches, tests | jamais écrasé par une release |
| `staging/` | vérification d'un artefact | incomplet ou invalide = non activé |
| `releases/` | versions immuables par SHA/hash | aucune modification en place |
| `state/` | actif, précédent, verrous, santé | écritures atomiques et bornées |
| `logs/` | traces d'exécution | secrets et identifiants expurgés |

## Cycle local cible

1. Travailler sur une branche issue de `origin/main`, sans modifier `main`.
2. Exécuter `python -m unittest discover` et les diagnostics applicables.
3. Construire un artefact depuis un SHA complet et un arbre Git propre.
4. Vérifier manifeste, empreintes, chemins et absence de secrets.
5. Préparer une release isolée ; conserver l'active et la précédente.
6. Activer au premier plan ou sous contrôle explicite, puis vérifier la santé.
7. En cas d'échec, arrêter le candidat et rétablir la précédente.
8. Publier code et preuves expurgées dans une PR Draft, sans fusion implicite.

Les scripts consolidés dans `scripts/remote/` implémentent déjà le modèle local
d'artefact/release et ses tests. Leur transport SSH/SFTP n'est pas nécessaire au
cycle courant ; voir le document d'accès distant pour son statut secondaire.

## Bluetooth

Le diagnostic en lecture seule peut être lancé librement :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bluetooth\diagnose.ps1
```

La création d'un service GATT visible, la publicité, l'appairage et l'émission
HID ne font jamais partie d'un déploiement ordinaire. Chaque session suit le
protocole autorisé, au premier plan, avec `StopAdvertising()` et un arrêt local
immédiat. Aucun démarrage automatique avant qualification du MVP.

## Contrôles de sécurité

- révision exacte et arbre propre ;
- idempotence, verrou anti-concurrence et chemins contenus ;
- contrôle de santé borné et rollback explicite ;
- API sur loopback, aucun pare-feu ou port modifié implicitement ;
- aucune installation ou reconfiguration Bluetooth implicite ;
- aucune commande souris sans utilisateur présent et surface de test sûre.

## Preuves attendues

Pour une activation : branche, SHA demandé, SHA actif, commande, résultat des
tests, santé, rollback éventuel et fichiers de logs expurgés. Pour HOGP : ajouter
reconnaissance côté cible, type de pilote chargé, événements minimaux observés et
preuve d'arrêt.

## Composants MC-HID-EXEC-001

```powershell
# Compilation de l'agent cible
powershell.exe -NoProfile -File .\scripts\build\Build-PositionAgent.ps1

# Construction du MSIX HOGP (ne l'installe pas)
powershell.exe -NoProfile -File .\scripts\build\Build-HogpPackage.ps1 `
  -CertificateThumbprint <EMPREINTE_VERIFIEE>

# Tests
python -m unittest discover -v
```

Le paquet HOGP doit être signé par le certificat exact préalablement vérifié.
Toute mise à jour doit aussi porter une version de manifeste strictement
supérieure à celle déjà installée ; réutiliser la même version avec un contenu
différent n'est pas une procédure de mise à jour supportée.
Le moteur WinRT est un script livré dans le catalogue MSIX et hébergé par la
copie intacte et Authenticode-valide du `powershell.exe` Windows. Cette
architecture conserve l'identité MSIX nécessaire au serveur GATT tout en
respectant Smart App Control, qui refuse le binaire C++ auto-signé. Le manifeste
déclare uniquement `runFullTrust` et `bluetooth`; aucun service, mode développeur
ou démarrage automatique.

L'exécution contrôlée utilise `python -m mousse_controler.app serve --config
<runtime-config>`. Le fichier de configuration reste hors Git, ACL utilisateur +
SYSTEM, et ne contient que des blobs DPAPI. L'arrêt est `Ctrl+C` ou la commande
locale authentifiée `stop`, qui libère les boutons, arrête la publicité et ferme
les serveurs.

MC-MOUSE-ACTIONS-001 ajoute des valeurs optionnelles sans casser les anciennes
configurations : `event_port` (8767, loopback uniquement), `capture_directory`
(par défaut à côté de la configuration), quotas `capture_max_*`,
`action_queue_size`, `action_max_records`, `event_max_subscribers` et
`action_journal`. `action_id_retention_seconds` vaut 2 592 000 (30 jours) par
défaut et doit rester strictement positif. Le jeton WebSocket est le bearer de
commande déjà protégé par DPAPI. Le journal, son registre anti-rejeu compagnon
`<action_journal>.ids`, l'index `<capture_directory>/.capture-index.json` et les
PNG restent hors Git ; le serveur ne fournit aucun endpoint de téléchargement
d'image.

Le journal et son fichier `.ids` forment un même état persistant : sauvegarde,
restauration, déplacement ou suppression doivent les traiter ensemble. La
garantie anti-rejeu s'applique pendant la rétention configurée à compter de la
première acceptation et au-delà tant que l'action demeure dans le registre. Un
fichier manquant après acceptation réduit cette garantie ; un fichier présent
mais invalide bloque le démarrage plutôt que d'autoriser un rejeu.

De même, ne pas effacer manuellement `.capture-index.json`. Une suppression
refusée apparaît en `DELETE_FAILED`; le fichier reste compté dans le quota et
identifiable par `capture_status`/`capture_list`, puis `capture_delete` permet
une nouvelle tentative contrôlée. Au redémarrage, les PNG non indexés sont
récupérés au lieu d'être considérés supprimés.

La cible est mise à jour dans sa session interactive avec
`scripts/target/Update-InteractivePositionAgent.ps1`. `Plan` ne mute rien ;
`Install` vérifie la tâche exacte, les SHA-256, arrête l'agent avec délai borné,
conserve un seul binaire `.mc-mouse-actions.previous`, remplace atomiquement et
redémarre ; `Rollback` restaure ce binaire. Le script refuse toute tâche dont
l'action n'est pas `PositionAgent.exe` et ne touche ni au fichier `agent.json`,
ni à DPAPI, au pare-feu, aux certificats ou à l'appairage.

Restauration : arrêter le contrôleur, désenregistrer les tâches temporaires
cible, retirer la règle pare-feu privée dédiée, restaurer chaque radio à son état
initial, supprimer le paquet `Rivounet.MousseControler.Hogp` et retirer uniquement
les certificats `CN=MousseControler` dont l'empreinte correspond à l'installation.

## Mise en service contrôlée autorisée — 21 novembre 2026

L'utilisateur a autorisé la transition opérationnelle sur `mini-pc-backend` et `MonOrdinateur` : certificat public MSIX v2 vérifié dans le magasin approprié, installation du MSIX 1.0.0.3 signé, mise à jour transactionnelle de PositionAgent, synchronisation du contrôleur, migration des seules configurations/tâches Mousse-controler, activation et contrôles de santé/communication. Cette autorisation **ne couvre pas** les commandes HID réelles, mouvements de souris ni captures. Ne pas désactiver Defender ou Smart App Control, ni étendre les permissions système générales.

Exécuter la séquence documentée dans `scripts/operations/README.md` et `qualification/MC-OPERATIONAL-FINALIZATION-001/PROCEDURE-MISE-EN-SERVICE.md`. Vérifier les sauvegardes, les persistances par ensembles (journal + `.ids`, index + PNG), les états de tâche/processus, les SHA, le verrou d'installation et la disponibilité du rollback. L'installation du **certificat public** dans un magasin de confiance doit rester distincte du stockage de la **clé privée** de signature. Vérifier la chaîne et le signataire exact du MSIX réellement installé, pas seulement du package de staging.

Le résultat final doit prouver les versions actives, tâches, processus, sessions, API/WebSocket, authentification, communication et récupération sans HID ni capture. `OPERATIONAL_PASS` désigne uniquement ce périmètre non matériel ; l'acceptation HID/captures exige un accord ultérieur au moment des essais. Une opération ambiguë impose arrêt contrôlé et restauration ou `RECOVERY_REQUIRED`.
