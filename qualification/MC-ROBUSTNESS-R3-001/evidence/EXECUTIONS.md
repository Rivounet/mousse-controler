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

## Correctif de revue B1/B2/B3

- SHA revu : `3d5a9397abda829df88b367b0dd096cbb83a0b3c` ;
- trois commentaires inline et revue globale lus avant modification ;
- stockage R3 + captures existantes : **20/20 PASS**, 3,521 s ;
- transactions PositionAgent ciblées : **9/9 PASS**, 70,633 s ;
- ciblés B1/B2/B3, R3, caractérisations R0 et non-régressions R1/R2 :
  **95/95 PASS**, 97,608 s, avertissements Python traités comme erreurs ;
- cœur applicatif, R0, R1, R2 et R3 : **189/189 PASS**, 107,081 s ;
- simulations remote/déploiement : **69/69 PASS**, 47,376 s ;
- contrats de sécurité non matériels : **5/5 PASS**, 0,017 s ;
- runner logiciel agrégé : **263/263 PASS**, zéro échec attendu ;
- diagnostics matériels exclus : **7** ;
- compilation Python, analyse syntaxique PowerShell, référence API et
  `git diff --check` : **PASS** ;
- durée cumulée des commandes de qualification finale : environ **4 min 16 s**.

Instrumentation B1 : le pic maximal observé atteint exactement le quota au
stade `index_temporary_written`, avec coexistence du PNG final, de l'ancien
index et du nouvel index temporaire. Toutes les observations satisfont
`used_bytes <= max_total_bytes`, y compris avec orphelin et temporaire
préexistants. Aucun fichier non géré n'est supprimé.

Le harness B2/B3 enregistre après chaque invocation l'état de tâche, le nombre
de processus, le SHA-256 du binaire et les compteurs start/stop. Il exécute le
script réel sur des binaires factices et remplace uniquement les cmdlets de
tâche/processus ; aucune tâche Windows réelle n'est touchée.
