# MC-HID-EXEC-001 — Rapport d'exécution

**Date :** 20 novembre 2026  
**Branche :** `feat/mc-hid-exec-001`  
**Verdict provisoire :** `INCOMPLETE`

## Résultat

Le logiciel complet a été réalisé : moteur HOGP natif, contrôleur Python,
retour de position HTTPS/HMAC, agent cible visible, API locale protégée, zones,
trajectoires et séquences. L'accès aux deux machines, la compilation et le
retour de position réel sont opérationnels. RustDesk n'a jamais été utilisé.

La qualification HID réelle n'est pas terminée. Le serveur GATT non packagé
crée tous ses attributs mais Windows passe la publicité à `Aborted`. La
documentation Microsoft exige la capacité manifeste `bluetooth`; un MSIX signé
de développement a donc été construit. Son installation attend l'approbation
humaine de l'ancre de confiance limitée à l'utilisateur courant. Aucune
installation globale non signée, désactivation de protection ou contournement
n'a été effectué.

## Jalons

| Jalon | Résultat |
|---|---|
| Accès aux deux machines | PASS — OpenSSH existant, clé + host key stricte |
| Environnement de compilation | PASS — Build Tools, MSVC et SDK officiels |
| Agent de position | PASS — visible, session console 1, deux écrans, HTTPS signé accepté |
| Premier appairage HID | FAIL contrôlé — aucune paire résiduelle |
| Premiers mouvements réels | Non exécutés |
| Positionnement précis | Non qualifié matériellement |
| Livraison finale | En cours — PR Draft, aucune fusion |

## Tests

`python -m unittest discover -v` : **103/103 PASS**, durée 60,365 s.

Les tests simulés ne sont pas utilisés comme preuve de fonctionnement HID.
Sont encore requis : reconnaissance souris native, mouvement, clic, scroll,
reconnexion, précision, P95, multi-écrans matériel, perte réseau et arrêt
mesuré.

## État final observé

- agent cible : encore lancé par tâche interactive temporaire pour la poursuite
  de la qualification ;
- radio mini-PC : `On` au début de la phase d'exécution ;
- radio cible : passée de `Off` à `On` pour l'essai, à restaurer si le mandat est
  abandonné ;
- aucune paire Bluetooth créée ;
- aucune notification ou commande HID émise ;
- aucun pilote, firmware, service caché ou démarrage automatique ajouté ;
- paquet HOGP non installé ; certificat de développement présent dans les
  magasins utilisateur `My` et `TrustedPeople`, pas approuvé dans `Root`.

## Blocage et prochaine action

Une validation humaine est nécessaire avant d'approuver le certificat exact
`CN=MousseControler` dans `CurrentUser\Root`. Après installation du MSIX :
vérifier `AdvertisementStatus=Started`, appairer, exécuter un mouvement minimal
sur surface sûre, puis la batterie matérielle. Sans ces résultats, le verdict
ne peut pas devenir PASS.
