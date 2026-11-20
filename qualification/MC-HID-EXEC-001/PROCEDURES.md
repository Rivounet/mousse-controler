# Installation, exécution, arrêt et restauration

## Construire

```powershell
powershell.exe -NoProfile -File .\scripts\build\Build-PositionAgent.ps1
powershell.exe -NoProfile -File .\scripts\build\Build-HogpPackage.ps1 `
  -CertificateThumbprint <EMPREINTE_VERIFIEE>
python -m unittest discover -v
```

Le MSIX requiert une signature vérifiée. Pour la qualification conditionnelle,
le certificat public exact est importé temporairement dans
`LocalMachine\TrustedPeople`, jamais dans un magasin `Root`. Smart App Control
n'accordant pas son niveau d'exécution au binaire C++ auto-signé, le paquet
héberge le script WinRT par le `powershell.exe` Microsoft-signé dont la signature
est contrôlée à la construction. Ne désactiver ni politique d'exécution, ni mode
développeur, ni protection Windows.

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
