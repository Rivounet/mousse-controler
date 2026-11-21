# Risques et réserves

| Risque | Niveau | Preuve | Réduction ultérieure |
|---|---|---|---|
| clone opérationnel en retard sur GitHub | `MAJOR` | `34b2612…` contre `fe4def1…` | synchronisation contrôlée et réversible |
| transport configuré différent du transport officiel installé | `MAJOR` | chemin C++ dans `controller.json`, MSIX PowerShell/WinRT présent | migration de configuration sous mandat |
| sûreté de reprise moderne non démontrée | `MAJOR` | journal, `.ids`, index et captures absents | initialisation et qualification après sauvegarde |
| état de déploiement historique interprétable à tort comme runtime actif | `MAJOR` | `active.json` historique, registre vide, aucun processus visible | séparer état modèle et état Windows réel |
| tâches planifiées inconnues | `INFORMATIONAL` | quatre méthodes passives bloquées | lecture autorisée sans démarrage |
| installation cible inconnue | `INFORMATIONAL` | SSH sandbox refusé | mandat d'accès distinct |
| artefacts locaux multiples | `MINOR` | C++, MSIX et deux builds PositionAgent présents | manifeste d'artefacts approuvés |

## Réserves

- La présence et la concordance du MSIX ne prouvent pas son exécution.
- L'absence de processus visible ne prouve pas l'absence d'une tâche arrêtée ou
  inaccessible.
- L'absence de fichiers persistants dans les chemins ciblés ne prouve pas qu'il
  n'en existe aucun ailleurs ; aucun parcours arbitraire du disque n'a été fait.
- La configuration réseau, les secrets, les identifiants personnels et les
  empreintes d'hôte ont été exclus des preuves publiées.
- Aucune proposition du plan n'est autorisée par le présent mandat.


