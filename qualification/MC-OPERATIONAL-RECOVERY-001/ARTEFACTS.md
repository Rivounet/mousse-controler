# Artefacts préparés

| Artefact | Taille | SHA-256 | État |
|---|---:|---|---|
| `PositionAgent.exe` | 28 672 | `31AD622DDDF1B8A778F977C7BAFC5E24F3DE8EDF873D5D9542124B3E59531FAE` | build PASS, non installé |
| `MousseControler.Hogp.unsigned.msix` | 187 032 | `4BB1C0F0C3C79D60E1164946336279D9A3206D5B1D8CAB56B7D710CB74122F3E` | package construit, **non signé** |
| MSIX précédent de rollback | 190 501 | `907AFB9E458C7DA5C2B5555581065A310CD8EBC39BC9BB5EAE2CA508A0B12042` | signature valide, contenu historique |

Le MSIX nouveau contient le script PowerShell/WinRT courant et une copie du
Windows PowerShell Microsoft-signé de l'hôte. Son manifeste, son script et son
binaire hôte diffèrent du package historique ; celui-ci ne peut donc pas être
présenté comme build du code actuel.

## Blocage de signature

Aucun certificat `CN=MousseControler` valide avec clé privée n'est disponible
dans les magasins personnels utilisateur ou machine inspectés. Seul le
certificat public historique est présent dans les artefacts sauvegardés. Le
nouveau MSIX ne doit ni être installé ni remplacer le package actif tant qu'il
n'est pas signé et vérifié avec l'identité approuvée.

Les builds ne sont pas réputés reproductibles bit-à-bit ; chaque exécution doit
être identifiée par son SHA-256. Le dossier local de staging contient les
artefacts et un manifeste dont le SHA-256 est
`A491197A6D303C543FFBC55C08774EA97A9CF64F53013A47DD22C9B49938545D`, mais
aucun binaire n'est publié dans la PR.
