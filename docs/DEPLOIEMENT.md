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

# Compilation moteur + lanceur + MSIX (ne l'installe pas)
powershell.exe -NoProfile -File .\scripts\build\Build-HogpPackage.ps1

# Tests
python -m unittest discover -v
```

Le paquet HOGP doit être signé par un certificat approuvé et installé pour
l'utilisateur avant usage. Ne pas utiliser l'option non signée tous utilisateurs
et ne pas activer le mode développeur. Le manifeste déclare uniquement
`runFullTrust` et `bluetooth`; aucun service ou démarrage automatique.

L'exécution contrôlée utilise `python -m mousse_controler.app serve --config
<runtime-config>`. Le fichier de configuration reste hors Git, ACL utilisateur +
SYSTEM, et ne contient que des blobs DPAPI. L'arrêt est `Ctrl+C` ou la commande
locale authentifiée `stop`, qui libère les boutons, arrête la publicité et ferme
les serveurs.

Restauration : arrêter le contrôleur, désenregistrer les tâches temporaires
cible, retirer la règle pare-feu privée dédiée, restaurer chaque radio à son état
initial, supprimer le paquet `Rivounet.MousseControler.Hogp` et retirer uniquement
les certificats `CN=MousseControler` dont l'empreinte correspond à l'installation.
