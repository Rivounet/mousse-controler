# Matrice de concordance

| Composant | GitHub | Mini-PC | MonOrdinateur | Concordance |
|---|---|---|---|---|
| Code Python | `main` `440ab39…` | clone propre `34b2612…` sur branche fonctionnelle ancienne | sans objet | `MISMATCH` |
| Transport HOGP | PowerShell/WinRT dans MSIX ; manifeste 1.0.0.2 | configuration vers `mousse-hogp.exe` C++ ; alias MSIX présent, installation non lisible | hôte PnP seulement, fonction non testée | `MISMATCH` |
| PositionAgent | source C# au SHA GitHub | deux builds locaux non prouvés installés | inspection impossible | `BLOCKED` |
| Scripts de maintenance | version GitHub `440ab39…` | version du clone `34b2612…` | inspection impossible | `MISMATCH` |
| Configuration runtime | contrat actuel R1–R6 | configuration MC-HID-EXEC historique ; persistance actions/captures absente des répertoires inspectés | inspection impossible | `MISMATCH` |
| Processus actifs | contrôleur/HOGP attendus seulement si activation voulue | aucun processus correspondant visible | inspection impossible | `UNKNOWN` |
| Package MSIX installé | identité `Rivounet.MousseControler.Hogp` | alias présent ; métadonnées AppX inaccessibles | sans objet | `UNKNOWN` |
| Tâches planifiées | contrats documentés | requêtes refusées dans ce contexte | inspection impossible | `BLOCKED` |

## Règles d'interprétation

- Une concordance de SHA compare uniquement les fichiers observés.
- Aucun processus n'étant visible, aucun fichier n'est déclaré chargé en mémoire.
- L'alias MSIX ne prouve ni la version ni la santé du package installé.
- La présence PnP de `MONORDINATEUR` ne constitue pas un test HID ou GATT.
- `BLOCKED` n'est pas converti en `MATCH` par les qualifications historiques.

