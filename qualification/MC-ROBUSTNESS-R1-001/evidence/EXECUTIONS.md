# Preuves d'exécution — MC-ROBUSTNESS-R1-001

Date : 20 novembre 2026, Europe/Paris.

## Référence avant modification

- base : `d8b412f8620ba85de1b9e864af2f11ed31271006` ;
- worktree propre sur `fix/mc-robustness-r1-001` ;
- runner R0 initial : **206/206 PASS** ;
- détail : 132 cœur/R0 en 5,960 s, 69 remote en 33,878 s, 5 contrats en
  0,008 s ;
- 7 diagnostics matériels exclus explicitement.

## Qualification ciblée intermédiaire

- `tests.test_r1_safety` : **11/11 PASS**, 0,195 s ;
- `tests.test_r1_safety tests.test_trajectory` : **24/24 PASS**, 0,613 s
  avant ajout du dernier cas `hold` actif ;
- suite cœur intermédiaire : **141/141 PASS**, 6,155 s.

## Qualification finale

- suite ciblée `tests.test_r1_safety tests.test_trajectory` : **25/25 PASS**,
  0,633 s ;
- stress déterministe R1 : **10 x 11/11 PASS** sur
  `tests.test_r1_safety` ;
- suite cœur avec `PYTHONPATH=src` : **145/145 PASS**, 6,282 s ;
- suite `test_remote` : **69/69 PASS**, 33,183 s ;
- contrats de sécurité non matériels : **5/5 PASS**, 0,004 s ;
- runner R0 agrégé : **219/219 PASS**, aucun échec attendu ;
- génération de référence API : `--check` **PASS** ;
- `git diff --check` : **PASS** ;
- diagnostics matériels exclus : **7**.

## Sécurité de l'exécution

- transport utilisé : `SimulatedHidTransport` et doubles déterministes ;
- réseau : aucun accès distant ;
- Bluetooth/HID : non sollicités ;
- capture : non sollicitée ;
- production : aucun processus, fichier de configuration ou journal actif
  modifié.
