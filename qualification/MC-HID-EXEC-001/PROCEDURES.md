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

Installer `PositionAgent.exe`, `Manage-InteractivePositionAgent.ps1` et un
`agent.json` contenant uniquement le secret DPAPI cible sous le répertoire
applicatif de l'utilisateur. Enregistrer la tâche
`MousseControler-PositionAgent` en mode interactif limité avec déclencheur
`AtLogOn`. Vérifier `agent_is_interactive=true`. Ne jamais activer l'auto-logon :
après un redémarrage, l'utilisateur ouvre sa session puis la tâche démarre.
Les deux tâches persistantes ont cinq reprises sur échec espacées d'une minute.

## Mini-PC

Le runtime non versionné sous `C:\ProgramData\MousseControler` contient la paire
certificat/clé TLS, les blobs DPAPI et les chemins. Le jeton de commande doit
être généré comme texte ASCII aléatoire avant protection DPAPI ; ne jamais
placer des octets arbitraires directement dans l'en-tête Bearer.

Installer la tâche persistante :

```powershell
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File .\scripts\runtime\Manage-MousseControllerTask.ps1 `
  -Action Start -ConfigPath C:\ProgramData\MousseControler\controller.json `
  -PythonPath <PYTHON_EXACT> -TaskName MousseControler-HOGP
```

Le runtime peut aussi être lancé au premier plan pour diagnostic :

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m mousse_controler.app serve --config <runtime-config>
```

Le mode `serve` prépare GATT puis démarre l'annonce connectable. Les commandes
loopback authentifiées `transport_status`, `position_status` et
`position_metrics` fournissent une
preuve sans mouvement. Après 30 s sans abonnement, le runtime recrée le
transport et recommence l'annonce ; aucun nouvel appairage n'est demandé.
Le lanceur du mini-PC nettoie le transport si l'initialisation échoue et retente
jusqu'à cinq fois, toutes les 30 s. Ce second niveau couvre les indisponibilités
Bluetooth transitoires observées juste après une ouverture de session.

## Mesurer les performances

Ouvrir d'abord une surface de test dédiée ne contenant aucune application
sensible, puis exécuter une série bornée :

```powershell
$env:PYTHONPATH = "$PWD\src"
python .\scripts\qualification\measure_position_performance.py --cycles 20
```

La commande produit un JSON avec taille d'échantillon, réussite, médiane, P95,
maximum, erreur, corrections et temps cumulés transport/feedback. Ne comparer
que des matrices identiques. `position_metrics` expose séparément cadence de
retour, HMAC, traitement récepteur et lecture native du curseur. La différence
entre horodatages de deux machines n'est une latence réseau valable que si leurs
horloges sont synchronisées et l'incertitude documentée.

## Arrêter

Utiliser `Ctrl+C` ou la commande `stop` pour l'arrêt d'urgence. La commande
libère les boutons et arrête le transport ; redémarrer la tâche pour reprendre
le service. Pour retirer les tâches persistantes, utiliser l'action `Stop` de
leurs gestionnaires. Sur la cible :

```powershell
.\Manage-InteractivePositionAgent.ps1 -Action Stop
.\Manage-InteractivePairing.ps1 -Action Stop
```

## Restaurer

1. Arrêter le contrôleur et retirer les tâches temporaires uniquement ; conserver
   les tâches persistantes tant que la qualification de redémarrage est ouverte.
2. Restaurer les radios à leur état initial documenté.
3. Supprimer la règle pare-feu dédiée.
4. Désinstaller `Rivounet.MousseControler.Hogp` si installé.
5. Retirer uniquement le certificat de développement dont sujet et empreinte
   correspondent à l'installation.
6. Supprimer les répertoires temporaires du projet sur la cible.

Ne jamais supprimer une paire, un certificat ou une règle étrangère au projet.
