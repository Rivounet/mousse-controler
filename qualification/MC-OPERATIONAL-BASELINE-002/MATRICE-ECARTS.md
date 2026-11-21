# Matrice actualisée des écarts E-01 à E-08

| ID | État initial | Nouvelle preuve | État actualisé | Risque / cause démontrée | Correction envisageable et préconditions |
|---|---|---|---|---|---|
| E-01 | `MAJOR`, clone `34b2612…` contre GitHub `440ab39…` | GitHub est désormais `fe4def1…`; clone toujours propre à `34b2612…` | `OUVERT`, écart accru | code opérationnel antérieur à la baseline documentaire ; cause de non-synchronisation confirmée | synchronisation Git contrôlée vers `fe4def1…`, mandat distinct et sauvegardes préalables |
| E-02 | `MAJOR`, état historique `c23dab3…`, aucun processus | `active.json` toujours `stable`, registre processus vide, aucun processus visible | `OUVERT` | état de déploiement modèle ne démontrant aucun runtime chargé | qualifier la fonction de cet état avant toute activation ; mandat d'exploitation |
| E-03 | `MAJOR`, configuration vers C++ historique | MSIX PowerShell/WinRT 1.0.0.2 installé et vérifié, mais configuration inchangée | `OUVERT`, mieux caractérisé | prochain lancement configuré vers un moteur historique malgré le package officiel disponible | migration proposée dans le plan ; nécessite sauvegarde, build vérifié et mandat de configuration |
| E-04 | `MAJOR`, persistances modernes non trouvées | chemins par défaut déterminés ; journal, `.ids`, captures et index absents | `OUVERT`, preuve renforcée | reprise/anti-rejeu non initialisés ou jamais utilisés ; cause exacte non démontrée | préserver toute découverte ultérieure ; initialisation seulement par runtime qualifié et mandat d'activation |
| E-05 | `MINOR`, builds anciens dans `source/out` | MSIX local identifié et deux builds PositionAgent/C++ restent présents sans manifeste d'approbation | `OUVERT` | confusion entre présent, installé et actif | produire un manifeste d'artefacts après reconstruction contrôlée |
| E-06 | `INFORMATIONAL`, MSIX et tâches illisibles | MSIX entièrement identifié ; quatre méthodes de lecture des tâches bloquées | `PARTIELLEMENT LEVÉ` | package connu, activation planifiée inconnue | inspection des tâches dans un contexte de lecture autorisé, sans démarrage |
| E-07 | `INFORMATIONAL`, cible inaccessible | nouvelle tentative passive refusée par la sandbox, sans élévation | `BLOCKED` | état PositionAgent inconnu | audit cible sous autorisation distincte et canal approuvé |
| E-08 | `INFORMATIONAL`, journal ancien | aucun nouveau journal opérationnel ; dernière preuve reste historique | `OUVERT` | aucune preuve récente de fonctionnement | collecte passive explicitement autorisée après synchronisation/activation |

## Lecture

- Aucun écart n'est corrigé par ce mandat.
- E-06 est le seul écart réduit par une observation supplémentaire.
- E-07 est un blocage d'accès, pas un succès implicite.
- E-01 à E-05 nécessitent une décision ou une modification ultérieure ; elles ne
  sont pas résolues par la seule présence du MSIX.


