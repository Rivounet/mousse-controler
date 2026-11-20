# Preuves d'exécution — MC-ROBUSTNESS-R3-001

Date : 21 novembre 2026, Europe/Paris.

## Baseline

- base exacte : `a938b7455638c71846a20f7c4dc6c6c1f887e6e6` ;
- branche : `fix/mc-robustness-r3-001` ;
- runner logiciel avant modification : **242/242 PASS** ;
- cœur/R0 : 168 en 15,410 s ; remote : 69 en 37,186 s ; contrats de
  sécurité non matériels : 5 en 0,007 s ;
- diagnostics matériels exclus : 7.

## Qualification intermédiaire

- nouveaux tests R3 initiaux : **14/14 PASS**, 19,751 s ;
- contrats capture/R0/PositionAgent adaptés : **23/23 PASS**, 3,066 s ;
- R3 enrichi du timeout de join et contrats startup : **20/20 PASS**,
  18,708 s.

## Qualification finale

- ciblés R3, captures, startup, contrat cible et non-régressions R1/R2 :
  **76/76 PASS**, 30,385 s, avertissements Python traités comme erreurs ;
- stabilité R3 dédiée : **2 x 15/15 PASS**, 18,105 s et 17,450 s ;
- cœur applicatif, R0, R1, R2 et R3 : **183/183 PASS**, 37,180 s ;
- simulations remote/déploiement : **69/69 PASS**, 34,087 s ;
- contrats de sécurité non matériels : **5/5 PASS**, 0,008 s ;
- runner logiciel agrégé : **257/257 PASS**, zéro échec attendu ;
- diagnostics matériels exclus : **7** ;
- compilation Python : **PASS** ;
- analyse syntaxique de tous les scripts PowerShell : **PASS** ;
- référence API générée : **PASS** ;
- `git diff --check` : **PASS** ;
- durée cumulée des commandes de qualification finale mesurées : environ
  **2 min 21 s**.

## Sécurité de l'exécution

- stockage : répertoires temporaires privés aux tests ;
- PositionAgent : vrai script, faux cmdlets de tâche/processus, binaires factices ;
- cycle de vie : serveurs et threads doubles, aucun port de production ;
- Bluetooth/HID, capture d'écran, SSH, `MonOrdinateur`, tâches réelles et
  production : non sollicités.
