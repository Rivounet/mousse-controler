# Rapport d'audit MC-HID-AUDIT-001

**Date :** 19 novembre 2026
**Périmètre :** audit non intrusif, sans publicité, appairage, émission HID,
déploiement cible ni modification système.
**Verdict :** architecture réalisable, HOGP encore
`GO_WITH_RESERVATIONS`, retour de position réalisable sous réserve du diagnostic
de `MonOrdinateur`.

## Réponse synthétique

La solution doit séparer strictement deux flux :

1. `mini-pc-backend` émet des rapports de souris **relatifs** au moyen d'un
   serveur HOGP WinRT au premier plan ;
2. un agent visible et limité à la session interactive de `MonOrdinateur` lit
   `GetCursorPos` et publie uniquement la position sur un endpoint HTTPS privé.

Le mini-PC ferme la boucle : il n'émet un nouveau déplacement que sur une
mesure fraîche, recalcule l'erreur, borne le rapport, et abandonne dès que le
retour devient obsolète. Ce mécanisme absorbe l'accélération Windows et les
écarts réels sans prétendre convertir directement des pixels en unités HID.

## Faits vérifiés sur mini-pc-backend

- Windows 11 Professionnel 26H2 x64, build `26300.9974` ;
- adaptateur Realtek, pilote `1.1061.2312.2501` daté du 20 mai 2024 ;
- BLE, rôles central et périphérique annoncés par `BluetoothAdapter` ;
- surface WinRT présente : `GattServiceProvider`, caractéristiques locales,
  notifications, publicité et appairage ;
- Python 3.12 et Node 26 présents ; aucun SDK .NET, MSVC, Windows SDK, CMake,
  Ninja, Rust ou Go accessible dans le `PATH` ;
- compilateur C# .NET Framework 4.8 présent, mais métadonnées `Windows.winmd`
  du Windows SDK absentes : il suffit pour l'agent Win32, pas pour compiler
  proprement le moteur WinRT HOGP ;
- `hidbth.sys` est présent ;
- le probe non diffusé a observé la radio Bluetooth **Off** et
  `GattServiceProvider.CreateAsync` a retourné `RadioNotAvailable`. Aucun
  objet GATT n'a donc été créé et la forme HID n'a pas été qualifiée.

Les indicateurs WinRT confirment les préconditions, pas le fonctionnement HID.
Le moteur HOGP requiert encore une chaîne MSVC/Windows SDK et une session de test
autorisée avec radio active, création réelle, publicité, bonding et pilote HID.

Les probes WinRT et `GetCursorPos` ont fonctionné dans un processus utilisateur
non élevé ; aucun droit administrateur n'est donc requis pour ces diagnostics.
Le futur agent doit toutefois appartenir à la station de fenêtres et à l'input
desktop de la session interactive (`WINSTA_READATTRIBUTES`). Un service en
Session 0 ne convient pas. L'installation d'outils, une règle de pare-feu ou
certaines opérations de provisionnement pourront demander une élévation
ponctuelle ; le moteur HOGP lui-même doit rester exécutable en utilisateur, à
confirmer lorsque la radio sera active.

## MonOrdinateur

Aucun accès authentifié à la cible n'était disponible. Aucune version de
Windows, topologie écran, capacité Bluetooth, règle de pare-feu ou permission
de session n'est donc affirmée.

[`Inspect-MonOrdinateur.ps1`](../../scripts/diagnostics/Inspect-MonOrdinateur.ps1)
collecte en lecture seule les prérequis sans adresse IP/MAC, compte, nom de
machine ni règle détaillée. Il vérifie notamment `GetCursorPos`, coordonnées
virtuelles signées, écrans, DPI système, paramètres d'accélération, session
interactive/console, .NET Framework, compilateur C#, Bluetooth, profils réseau
et politiques globales du pare-feu. Son exécution locale sur le mini-PC a validé
le fonctionnement du script, **pas les caractéristiques de MonOrdinateur**.

## Canal Bluetooth HOGP

### Table GATT minimale recommandée

- HID Service `0x1812` ;
- HID Information `0x2A4A`, lecture chiffrée ;
- Report Map `0x2A4B`, lecture chiffrée ;
- HID Control Point `0x2A4C`, écriture sans réponse chiffrée ;
- Report `0x2A4D`, lecture + notification chiffrées, descripteur Report
  Reference `0x2908` ; le CCCD est généré par Windows ;
- Battery Service `0x180F` et Battery Level `0x2A19` ;
- Device Information Service `0x180A`, obligatoire dans HOGP mais réservé par
  Windows. Il faut vérifier que la pile système expose l'information attendue ;
- Protocol Mode et Boot Mouse Input Report sont omis en mode Report Protocol
  uniquement, sauf incompatibilité constatée sur la cible.

Le rapport recommandé n'utilise pas de Report ID et contient six octets : bits
de boutons, `X int16 little-endian`, `Y int16 little-endian`, molette `int8`.
Le Report Reference vaut alors `[0x00, 0x01]` (ID 0, Input Report). Point de
départ du Report Map, à figer par test de parsing :

```text
05 01 09 02 A1 01 09 01 A1 00 05 09 19 01 29 05
15 00 25 01 95 05 75 01 81 02 95 01 75 03 81 03
05 01 09 30 09 31 16 00 80 26 FF 7F 75 10 95 02
81 06 09 38 15 81 25 7F 75 08 95 01 81 06 C0 C0
```

La conformité exacte du descripteur et son interprétation Windows doivent être
validées par parsing unitaire puis sur la cible ; cet audit ne l'a pas exposé
par GATT.

Tous les attributs sensibles exigent `EncryptionRequired`. La cible autorisée
est appairée volontairement dans l'interface Windows ; aucune notification ne
part avant abonnement au Report characteristic. Après bonding, la publicité
redevient connectable mais non découvrable si WinRT et le Host le permettent.

Le moteur conserve un masque de boutons. Sur arrêt, expiration, erreur ou perte
de session, il tente un rapport nul si le Host est encore abonné, remet toujours
l'état interne à zéro, vide les commandes et arrête la publicité. Aucune
commande ou pression n'est rejouée après reconnexion.

## Retour de position LAN

L'agent recommandé est une petite application C# .NET Framework 4.8 exécutée
dans la session utilisateur, avec icône/état et arrêt explicite. Elle n'est ni
service ni récepteur de commandes. Elle utilise `GetCursorPos` et un manifeste
Per-Monitor-V2, puis envoie la dernière mesure seulement :

```json
{
  "v": 1,
  "agent_id": "logical-id",
  "session": "random-per-start",
  "seq": 42,
  "observed_utc": "2026-11-19T12:34:56.789Z",
  "monotonic_ms": 123456,
  "x": -120,
  "y": 740,
  "virtual_screen": {"left": -1920, "top": 0, "width": 3840, "height": 1080},
  "topology_generation": "opaque-hash"
}
```

Transport : HTTPS sur LAN privé, certificat serveur épinglé, clé HMAC-SHA-256
par agent protégée par DPAPI côté cible et ACL côté mini-PC. La signature couvre
méthode, chemin, session, séquence et corps canonique. Le serveur rejette ancien
timestamp, séquence rejouée, session inconnue et taille excessive. La réponse
est un simple acquittement de séquence : aucun ordre souris ni script n'est
accepté par l'agent. Le flux sortant évite toute ouverture entrante sur la cible.

Cadence initiale proposée : 20 Hz, à mesurer. En déconnexion, pas de file ; la
mesure la plus récente remplace l'ancienne et l'agent retente avec backoff. Le
verrouillage, changement de session, échec `GetCursorPos`, changement de
topologie ou absence de mesure fraîche rendent le contrôle indisponible.

## Boucle de position précise

Le référentiel est celui de l'écran virtuel Windows, en pixels physiques signés.
Les coordonnées peuvent être négatives. Une cible est liée à une génération de
topologie et rejetée si les écrans changent.

Pour chaque mesure fraîche :

1. calculer `erreur = cible - position_mesurée` ;
2. si l'erreur est dans la tolérance pendant plusieurs mesures, terminer ;
3. produire un pas relatif proportionnel borné, plus grand loin de la cible et
   plus fin à proximité ;
4. envoyer un seul rapport, puis attendre une mesure de séquence supérieure ;
5. abandonner sur timeout, retour trop ancien, changement de session/topologie,
   déconnexion, bouton incohérent ou arrêt utilisateur.

Seuils de qualification proposés, à confirmer par mesure : erreur finale
`<= 2 px` sur trois échantillons successifs, 95e percentile `<= 4 px`, aucun
dépassement hors écran, retour d'arrêt `<= 250 ms`, réussite `>= 99 %` sur une
matrice de positions. Le timeout d'une commande est initialement 2 s et une
mesure âgée de plus de 150 ms est rejetée. Ces valeurs sont des **critères de
test**, pas des performances observées.

Une souris physique concurrente ne peut pas être identifiée par `GetCursorPos`
seul. Le contrôleur peut détecter une trajectoire incompatible et s'arrêter,
mais Raw Input est nécessaire pour attribuer un mouvement à un périphérique.
L'arbitrage minimal recommandé est : pause immédiate après écarts répétés et
contrôle seulement sous supervision ; ajouter Raw Input uniquement si les tests
montrent que cette protection est insuffisante.

## Technologie recommandée

| Composant | Choix | Motif |
|---|---|---|
| HOGP | C++20 + C++/WinRT, MSVC/Windows SDK | API WinRT native, contrôle du cycle de vie, binaire autonome |
| Agent position | C# .NET Framework 4.8 WinForms/console | runtime et compilateur intégrés à Windows observé ; P/Invoke simple |
| Contrôleur/API mini-PC | Python 3.12, bibliothèque standard en priorité | déjà disponible, tests rapides, orchestration et HTTPS suffisants |
| Tests | Python + doubles HID/LAN ; tests Windows ciblés | sépare logique déterministe et matériel |

C# WinRT serait une alternative valide après installation d'un SDK .NET et des
Windows SDK Contracts, mais n'apporte pas ici un avantage suffisant. Python et
PowerShell sont écartés pour le serveur HOGP de production : projection WinRT,
cycle de vie et typage des buffers seraient plus fragiles.

## Blocages et risques

1. radio actuellement Off et création GATT non démontrée ;
2. conformité de la table HOGP, notamment Device Information réservé par
   Windows, non observée ;
3. reconnaissance/bonding/reconnexion réels avec MonOrdinateur inconnus ;
4. cible non diagnostiquée : Windows, Bluetooth, écrans, DPI et réseau inconnus ;
5. chaîne C++/WinRT absente ; son installation sera une opération autorisée
   séparément dans le mandat exécutoire ;
6. ouverture HTTPS entrante sur le mini-PC susceptible d'exiger une règle de
   pare-feu privée explicite ;
7. latence et précision non mesurées ;
8. mouvement concurrent attribuable seulement avec Raw Input.

## Conclusion

Il n'existe pas d'obstacle architectural identifié. La voie Windows native est
crédible mais ne passe pas encore à `GO` : le prochain mandat doit d'abord
diagnostiquer la cible, installer/valider la chaîne choisie avec autorisation,
puis franchir des portes matérielles réversibles. Le plan détaillé est dans
[`PLAN-EXECUTION.md`](PLAN-EXECUTION.md).
