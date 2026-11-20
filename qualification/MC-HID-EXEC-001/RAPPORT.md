# MC-HID-EXEC-001 — Rapport d'exécution

**Date :** 20 novembre 2026  
**Branche :** `feat/mc-hid-exec-001`  
**Verdict provisoire :** `INCOMPLETE`

## Reprise révisée — alternative de confirmation et Smart App Control

Le défaut de « fenêtre invisible » a été séparé de l'appairage : la confirmation
est désormais prise en charge explicitement par `PairingTool` avec la cérémonie
WinRT `ConfirmOnly`, et son résultat est écrit dans un JSON expurgé. La sélection
ne repose plus sur un endpoint mis en cache : un `DeviceWatcher` actif exige le
nom exact, `IsPresent=true`, `IsConnectable=true` et `CanPair=true` avant
`PairAsync(ConfirmOnly, Encryption)`. Une fenêtre graphique n'est donc plus une
dépendance de qualification.

Un second blocage a été prouvé avant l'appairage : Smart App Control, politique
`VerifiedAndReputableDesktop`, a refusé le nouveau moteur C++ pourtant signé et
installé. Les événements Code Integrity indiquent niveau demandé 2, niveau
validé 1 et `VerificationError=18`. Aucune protection n'a été désactivée et aucun
certificat n'a été ajouté à un magasin `Root`.

Une alternative conforme a été réalisée : le script PowerShell/WinRT catalogué
dans le MSIX s'exécute sous la copie intacte de `powershell.exe` signée Microsoft
et conserve l'identité `Rivounet.MousseControler.Hogp`. Les preuves locales sont
positives : `CreateAsync=Success`, services HID et Battery créés, publicité
`Started`, puis cycle du transport Python `start → advertise → stop` réussi. Le
MSIX final signé et vérifié a le SHA-256
`1A358251E8F267361D9F5A9319022C625C70F4C70307F66937A43DB6002A75E7`.

La qualification matérielle n'a pas pu reprendre : le nom DNS de la cible ne se
résout plus et aucun voisin SSH déjà connu ne correspond à sa clé hôte. Une
recherche élargie du réseau a été refusée afin de ne pas sonder des machines hors
périmètre. La dernière observation autorisée de la radio cible était `On`; son
état final n'est donc pas encore vérifié. Aucune nouvelle tentative d'appairage,
aucun abonnement et aucun rapport HID n'ont eu lieu dans ce cycle. Le paquet et
le certificat temporaire restent installés sur le mini-PC, sans processus ni
publicité actifs, uniquement pour reprendre dès que la cible redevient joignable.

## Résultat

Le logiciel complet a été réalisé : moteur HOGP natif, contrôleur Python,
retour de position HTTPS/HMAC, agent cible visible, API locale protégée, zones,
trajectoires et séquences. L'accès aux deux machines, la compilation et le
retour de position réel sont opérationnels. RustDesk n'a jamais été utilisé.

La qualification HID réelle reste incomplète. Le certificat public de
développement `CN=MousseControler` a été vérifié par empreinte
`F4D17F09181DE18154C429C0ED762AD66A762C54`, EKU signature de code, validité du
20 novembre au 20 décembre 2026 et absence de clé privée dans le `.cer`. Cette
empreinte correspond au signataire du MSIX, au Publisher du manifeste et à la
signature validée par SignTool. SHA-256 du MSIX installé :
`55644240E5D93155A21B0868FBDEC1DC2C1E3CA80D59FBBEBBF1348312490A21`.

Le certificat public a été importé temporairement dans
`LocalMachine\TrustedPeople` après confirmation UAC, sans ajout dans un magasin
Root par cette procédure. Le paquet signé a été installé pour l'utilisateur,
avec identité `Rivounet.MousseControler.Hogp`, signature `Developer`, capacité
`bluetooth` et `runFullTrust`. Le processus observé provenait bien de son
répertoire `WindowsApps`.

La création GATT packagée a réussi. WinRT a d'abord signalé un `Aborted`
transitoire, puis `StartedWithoutAllAdvertisementData` (`status=2`) ; le moteur
a donc un défaut de course dans le compte rendu synchrone de démarrage. La cible
a retrouvé l'endpoint exact, puis une tentative d'appairage volontaire a reçu
et accepté `ConfirmOnly`, mais Windows a retourné `Failed` avec niveau de
protection effectivement utilisé `None`. Aucune paire, aucun abonnement GATT et
aucun rapport HID n'ont été produits.

## Jalons

| Jalon | Résultat |
|---|---|
| Accès aux deux machines | PASS — OpenSSH existant, clé + host key stricte |
| Environnement de compilation | PASS — Build Tools, MSVC et SDK officiels |
| Agent de position | PASS — visible, session console 1, deux écrans, HTTPS signé accepté |
| MSIX et identité packagée | PASS — signature, Publisher, intégrité, installation et chemin processus vérifiés |
| Publicité packagée | PARTIAL — état stabilisé `StartedWithoutAllAdvertisementData`, course `Aborted` transitoire |
| Premier appairage HID | FAIL contrôlé — `ConfirmOnly`, résultat `Failed`, aucune paire résiduelle |
| Premiers mouvements réels | Non exécutés |
| Positionnement précis | Non qualifié matériellement |
| Livraison finale | En cours — PR Draft, aucune fusion |

## Tests

`python -m unittest discover -v` : **103/103 PASS**, durée initiale 60,365 s ;
revalidation après intégration de `main` : **103/103 PASS en 54,453 s** avec le
répertoire temporaire court prévu ; après correction de la course publicitaire :
**103/103 PASS en 45,994 s**.

Après intégration de l'alternative Smart App Control et des tests de commande de
l'alias packagé : **105/105 PASS en 52,869 s**, puis revalidation complète
**105/105 PASS en 80,412 s**.

Les tests simulés ne sont pas utilisés comme preuve de fonctionnement HID.
Sont encore requis : reconnaissance souris native, mouvement, clic, scroll,
reconnexion, précision, P95, multi-écrans matériel, perte réseau et arrêt
mesuré.

## État final observé

- agent cible et tâche d'appairage : arrêtés et désenregistrés ;
- radio mini-PC : `On`, état initial préservé ;
- radio cible : restaurée de `On` à son état initial `Off`, confirmation WinRT ;
- aucune paire Bluetooth créée ;
- aucune notification ou commande HID émise ;
- aucun pilote, firmware, service caché ou démarrage automatique ajouté ;
- paquet HOGP désinstallé, processus absent, publicité arrêtée et boutons
  libérés ; règle pare-feu temporaire et répertoire cible supprimés ;
- certificat temporaire `LocalMachine\TrustedPeople` retiré par empreinte ;
- une copie de la même empreinte a été détectée dans `CurrentUser\Root`, hors de
  l'import conditionnel courant. La confirmation graphique lancée depuis la
  session Codex RDP 7 n'était pas visible sur la console 6 ; le retrait exact a
  été effectué avec `certutil -user -delstore Root <empreinte>`. Les magasins
  Root ne contiennent plus cette empreinte. Les copies de construction
  existantes dans `CurrentUser\My` et `CurrentUser\TrustedPeople` sont
  préservées.

## Blocage et prochaine action

Le blocage produit n'est plus la confiance MSIX : l'identité packagée et la
publicité ont été démontrées. Le blocage est l'échec de bonding/chiffrement côté
Windows malgré `ConfirmOnly`. La course du démarrage publicitaire a été corrigée
dans le code et recompilée, sans reconstruire ni réinstaller un nouveau MSIX
après le nettoyage. Avant une nouvelle tentative, instrumenter l'échec de
pairing sans affaiblir `Encryption`, puis établir pourquoi la protection
utilisée reste `None`.
Le verdict ne peut pas devenir PASS sans reconnaissance HID et preuve
matérielle. Le nettoyage de qualification est clos et vérifié.
