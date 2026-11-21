# Procédures livrées

La source normative courte est `scripts/operations/README.md`.

| Besoin | Entrée |
|---|---|
| Inventaire/préconditions | `Check-CodexEnvironment.ps1` |
| Tâche et runtime du mini-PC | `Inspect-LocalRuntime.ps1` |
| Cible distante passive | `Inspect-RemoteTarget.ps1` |
| Builds et tests | `Invoke-BuildAndQualify.ps1 -Profile full-local` |
| Clé, restauration et signature | `Prepare-MsixSigning.ps1` |
| Dossier de déploiement sans activation | `Prepare-Deployment.ps1` |

Toutes les entrées produisent du JSON et partagent les codes `0` (objectif
atteint), `1` (défaut), `2` (précondition/autorisation) et `130` (interruption).
Les inspecteurs sont idempotents et en lecture seule. Les effets de build sont
bornés à `out/`. Les tests de non-régression vérifient la présence des six
contrats, les canaux exacts et l'absence d'opération matérielle dans les
inspecteurs ou la préparation de signature.

Les contrats critiques possèdent en plus des tests d'exécution : fournisseur de
processus disponible, vide ou refusé, et MSIX temporaires dont la preuve est
concordante ou altérée sur le hash, l'identité ou la version. Ces tests appellent
les fonctions et scripts réels; ils ne reposent pas sur la recherche de chaînes.
