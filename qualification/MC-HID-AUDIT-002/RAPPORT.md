# Rapport MC-HID-AUDIT-002

**Date :** 19 novembre 2026
**Portée :** radio Bluetooth du mini-PC, accès et prérequis de MonOrdinateur,
sans activation, publicité, appairage, événement HID, installation ni changement
système.

## Verdicts

| Machine | Verdict | Motif |
|---|---|---|
| `mini-pc-backend` | `READY_WITH_RESERVATIONS` | contrôleur, pilote, services, PnP, BLE et rôle périphérique sains ; radio volontairement `Off`, donc création GATT impossible jusqu'à activation autorisée |
| `MonOrdinateur` | `INCOMPLETE` | aucun canal natif existant utilisable depuis le mini-PC ; inventaire historique favorable, mais diagnostic courant de session/écrans/DPI/radio/réseau non exécuté |

Ces verdicts portent sur les prérequis, pas sur une qualification HOGP
fonctionnelle.

## A — mini-pc-backend

### Cause de `RadioNotAvailable`

Le résultat est reproductible :

- WinRT énumère Wi-Fi `On` et Bluetooth `Off` ;
- l'état Bluetooth est `Off`, et non `Disabled` ;
- Realtek Bluetooth Adapter : PnP `OK`, code problème `0`, `ConfigFlags=0` ;
- pilote `1.1061.2312.2501`, daté du 20 mai 2024 ;
- BLE et rôle périphérique annoncés `true` ;
- `bthserv` et `RmSvc` actifs ; `BTAGService` manuel et arrêté, état normal
  hors Audio Gateway ;
- aucun périphérique Bluetooth présent en erreur ;
- aucune stratégie Bluetooth configurée détectée ;
- aucun événement d'erreur/avertissement des 30 derniers jours corrélé à
  l'identifiant de l'adaptateur.

Le probe non diffusé reproduit `GattServiceProvider.CreateAsync =
RadioNotAvailable` pour HID, Battery et Device Information. La cause immédiate
est donc l'alimentation logicielle Bluetooth coupée. Il n'existe actuellement
aucun indice d'une désactivation PnP, d'un kill-switch firmware, d'une stratégie
administrative ou d'un défaut pilote. Seul un essai radio `On` permettra de
prouver que cette cause est suffisante.

Microsoft distingue `Off` (état opérationnel éteint) de `Disabled` (firmware ou
commutateur matériel). La lecture de l'état ne demande pas d'autorisation ; le
changement par `SetStateAsync` exige un consentement et reste soumis au matériel
et aux stratégies.

### Activation proposée — non exécutée

Procédure recommandée après autorisation complémentaire :

1. ouvrir **Paramètres > Bluetooth et appareils** (`ms-settings:bluetooth`) ;
2. relever l'état initial `Off`, puis basculer Bluetooth sur `On` ;
3. attendre l'état WinRT `On` sans lancer de recherche d'appareil ;
4. exécuter `Inspect-BluetoothRadio.ps1`, puis le probe GATT non diffusé ;
5. ne jamais appeler `StartAdvertising` ;
6. pour restaurer, replacer le bouton sur `Off` et confirmer WinRT `Off`.

Effets attendus : alimentation et réénumération des enfants Bluetooth, service
GATT créable en mémoire. Risques : émission RF normale et reconnexion automatique
possible à un appareil déjà appairé. Aucune nouvelle association n'est créée par
le simple bouton. Pour cette raison, l'activation n'a pas été faite dans l'audit.

Résultat discriminant :

- `Success` radio `On` : `RadioNotAvailable` provenait uniquement de l'état Off ;
- autre erreur : conserver son enum, vérifier permission/contexte puis table
  GATT, sans publicité ;
- radio impossible à activer ou `Disabled` : investiguer stratégie, firmware ou
  pilote avant MC-HID-EXEC-001.

## B — accès à MonOrdinateur

Les canaux natifs ont été recherchés sans scan réseau :

- aucun alias SSH `MonOrdinateur` ;
- aucune clé d'hôte approuvée correspondante ;
- aucun enregistrement DNS sous ce nom ;
- aucun accès SSH par clé existant identifié ;
- aucun nouveau compte, port, règle ou mécanisme d'authentification créé ;
- RustDesk est explicitement exclu et n'a pas été utilisé.

Un nom d'hôte/adresse et un canal natif existant sont nécessaires pour une
exécution distante. À défaut, le diagnostic local ci-dessous est la voie sûre.

### Données historiques, non requalifiées

L'inventaire MC-INIT-001 du même jour indiquait Windows 11 Famille x64 build
26300, Realtek Bluetooth Adapter `1.1072.2312.2502`, rôles BLE central et
périphérique, PowerShell 7.6.9 et réseau Wi-Fi actif. Il ne décrit pas la session,
les écrans, le DPI, la radio ni le pare-feu actuels et ne suffit pas à remplacer
MC-HID-AUDIT-002.

### Diagnostic local exact

Dans la session interactive de MonOrdinateur, depuis le dépôt ou une copie
contrôlée du script :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnostics\Inspect-MonOrdinateur.ps1
```

Le schéma 2 relève en lecture seule : OS/build, .NET Framework et compilateur
C#, session console/input desktop, `GetCursorPos` et `GetPhysicalCursorPos`,
écrans/coordonnées virtuelles/DPI, accélération, Bluetooth/PnP/radio/services,
pilote HID hôte, souris présentes, profil réseau et politiques globales du
pare-feu. Il exclut comptes, nom d'hôte, IP/MAC, identifiants PnP et règles
détaillées.

Quand le serveur HTTPS du mini-PC existera, le même script pourra tester
uniquement l'ouverture TCP sortante :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnostics\Inspect-MonOrdinateur.ps1 -MiniPcHost <hote> -MiniPcPort <port>
```

Ce test ne crée aucun listener et ne modifie pas le pare-feu.

## Retour de position

Le script enrichi a été validé sur le mini-PC : .NET Framework 4.8, compilation
C# inbox, session interactive, input desktop lisible, `GetCursorPos` et
`GetPhysicalCursorPos` réussissent, coordonnées cohérentes, DPI par moniteur et
paramètres pointeur lisibles. Cela valide la méthode, pas la cible.

Sur MonOrdinateur, l'agent sera `READY` si le diagnostic courant confirme :

- .NET Framework 4.8 et processus x64 ;
- session utilisateur interactive et input desktop lisible ;
- appels curseur réussis et référentiel physique cohérent ;
- topologie et DPI complets, y compris coordonnées négatives éventuelles ;
- profil LAN privé et sortie TCP vers le futur endpoint ;
- pare-feu sortant non bloquant ;
- `hidbth.sys`, adaptateur Bluetooth `OK` et aucune erreur souris/HID.

Le verrouillage ou changement de session invalidera le feedback. L'agent reste
manuel pendant la qualification et n'accepte aucun ordre entrant.

## Dépendances minimales pour MC-HID-EXEC-001

### Déjà présentes

- Windows 11 x64, Python 3.12, Git et PowerShell ;
- .NET Framework 4.8 et compilateur C# inbox sur le mini-PC ;
- pile WinRT Bluetooth, Realtek, `hidbth.sys` ;
- aucune bibliothèque Python additionnelle nécessaire au contrôleur initial.

### À installer sur le mini-PC après autorisation

- Visual Studio Build Tools, workload
  `Microsoft.VisualStudio.Workload.VCTools` ;
- MSVC x64/x86 `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` ;
- Windows 11 SDK 10.0.26100,
  `Microsoft.VisualStudio.Component.Windows11SDK.26100` ;
- dépendance projet verrouillée `Microsoft.Windows.CppWinRT` si le build MSBuild
  retenu l'exige.

Le SDK .NET moderne, CMake, Rust, Go, WinUI et un IDE complet ne sont pas requis.
L'installation Build Tools demandera vraisemblablement une élévation ponctuelle
et un téléchargement ; le runtime HOGP doit ensuite fonctionner en utilisateur
standard. Rien n'a été installé pendant l'audit.

Sur MonOrdinateur, aucune installation n'est prévue si le diagnostic confirme
.NET Framework 4.8. Le binaire agent et sa configuration utilisateur suffiront
pendant la qualification.

## Autorisations encore nécessaires

1. activer temporairement la radio Bluetooth du mini-PC et accepter le risque de
   reconnexion à des appareils déjà bondés ;
2. installer Build Tools/MSVC/Windows SDK sur le mini-PC ;
3. fournir un canal natif existant vers MonOrdinateur ou exécuter localement le
   diagnostic et transmettre sa sortie hors Git ;
4. plus tard seulement : publicité, appairage et rapports HID bornés ;
5. règle de pare-feu privée mini-PC uniquement si le test du serveur HTTPS la
   rend nécessaire.

## Préparation de MC-HID-EXEC-001

Le mandat peut démarrer après deux portes :

- **Porte radio :** état `On` autorisé et `CreateAsync` non diffusé réussi ;
- **Porte cible :** diagnostic schéma 2 courant reçu avec verdict au moins
  `READY_WITH_RESERVATIONS`.

Le reste de l'architecture de MC-HID-AUDIT-001 est maintenu : C++20/C++/WinRT,
Python 3.12, agent C# Framework 4.8, HTTPS épinglé/HMAC/anti-rejeu, démarrage
manuel et boucle sur mesures fraîches.
