# MC-HID-EXEC-001 — Rapport d'exécution

**Date :** 20 novembre 2026  
**Branche :** `feat/mc-hid-exec-001`  
**Verdict provisoire :** `INCOMPLETE`

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
