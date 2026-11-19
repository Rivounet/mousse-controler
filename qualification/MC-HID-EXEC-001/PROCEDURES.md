# Installation, exécution, arrêt et restauration

## Construire

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build\Build-PositionAgent.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build\Build-HogpPackage.ps1
python -m unittest discover -v
```

Le MSIX requiert une signature de confiance. Pour une qualification locale,
utiliser un certificat de développement à durée courte et limité à l'utilisateur
courant. Faire approuver cette opération par l'utilisateur ; ne pas installer un
paquet exécutable non signé pour tous les utilisateurs et ne pas activer le mode
développeur.

## Cible

Compiler puis copier `PositionAgent.exe` et un `agent.json` contenant seulement
un secret DPAPI cible. Lancer avec
`Manage-InteractivePositionAgent.ps1 -Action Start`. Vérifier
`agent_is_interactive=true`. Aucun service ou déclencheur de connexion n'est
créé ; la tâche est démarrée explicitement et temporairement.

## Mini-PC

Le runtime non versionné contient certificat/clé TLS, blobs DPAPI et chemins.
Lancer au premier plan :

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m mousse_controler.app serve --config <runtime-config>
```

La création GATT ne diffuse rien. `advertise_start` est une commande loopback
authentifiée séparée.

## Arrêter

Utiliser `Ctrl+C` ou la commande `stop`. Vérifier libération des boutons, arrêt
de publicité et fermeture des ports. Sur la cible :

```powershell
.\Manage-InteractivePositionAgent.ps1 -Action Stop
.\Manage-InteractivePairing.ps1 -Action Stop
```

## Restaurer

1. Arrêter contrôleur et tâches temporaires.
2. Restaurer les radios à leur état initial documenté.
3. Supprimer la règle pare-feu dédiée.
4. Désinstaller `Rivounet.MousseControler.Hogp` si installé.
5. Retirer uniquement le certificat de développement dont sujet et empreinte
   correspondent à l'installation.
6. Supprimer les répertoires temporaires du projet sur la cible.

Ne jamais supprimer une paire, un certificat ou une règle étrangère au projet.
