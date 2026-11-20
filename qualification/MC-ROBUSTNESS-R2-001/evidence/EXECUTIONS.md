# Preuves d'exécution — MC-ROBUSTNESS-R2-001

Date : 21 novembre 2026, Europe/Paris.

## Baseline

- base : `5b158a68325154be0621fd8764fb3d09b6d2e398` ;
- runner logiciel R0 avant modification : **222/222 PASS** ;
- tests remote : 69 en 34,439 s ;
- contrats non matériels : 5 en 0,004 s ;
- diagnostics matériels exclus : 7.

## Qualification intermédiaire

- nouveaux tests R2 et contrats transport : **18/18 PASS**, 5,049 s ;
- suite cœur complète : **161/161 PASS**, 11,455 s ;
- syntaxe PowerShell : **PASS** ;
- référence API générée : **PASS** ;
- compilation Python : **PASS** ;
- `git diff --check` : **PASS**.

## Qualification finale

- ciblés R2, caractérisations R0 et non-régression R1 :
  **42/42 PASS**, 7,624 s ;
- stress final R2 : **3 x 14/14 PASS**, entre 5,547 s et 5,567 s par passe ;
- suite cœur/R0 : **164/164 PASS**, 12,115 s ;
- tests remote : **69/69 PASS**, 35,039 s ;
- contrats de sécurité non matériels : **5/5 PASS**, 0,003 s ;
- runner logiciel R0 agrégé : **238/238 PASS**, aucun échec attendu ;
- diagnostics matériels exclus : **7** ;
- syntaxe PowerShell, compilation Python, référence API et
  `git diff --check` : **PASS**.

## Sécurité de l'exécution

- moteurs HOGP : sous-processus Python factices ou doubles en mémoire ;
- serveur : HTTP/TLS loopback éphémère, certificat auto-signé de test ;
- Bluetooth/HID, capture, SSH, cible et production : non sollicités ;
- aucune preuve ne revendique un relâchement physique de bouton.

## Correctif de revue B1/B2

- commentaires GitHub B1/B2 lus avant modification, SHA examiné
  `ff1cc898a9fe4f4f4f06ecf9206e6684d0bf61c2` ;
- ciblés R2 et transport finaux : **25/25 PASS**, 8,796 s, avec
  `ResourceWarning` traités comme erreurs ;
- stabilité finale B1/B2 : **3 x 25/25 PASS**, entre 8,807 s et 9,149 s
  par passe (`unittest`), sans avertissement de ressource ;
- non-régression R1 : **14/14 PASS**, 0,288 s ;
- cœur et caractérisations : **168/168 PASS**, 17,072 s ;
- simulations remote/déploiement : **69/69 PASS**, 37,561 s ;
- contrats non matériels : **5/5 PASS**, 0,008 s ;
- runner logiciel R0 agrégé : **242/242 PASS**, zéro échec attendu ;
- diagnostics matériels exclus : **7** ;
- B1 : vrai TLS loopback, client muet puis client valide servi en moins de
  0,4 s avant la borne de 0,6 s du premier, slots revenus à zéro ;
- B2 : en-têtes et corps `trickle` expirés sans appel métier, reprise saine ;
- capture de **24 Mio** acceptée sur loopback dans son budget total.
