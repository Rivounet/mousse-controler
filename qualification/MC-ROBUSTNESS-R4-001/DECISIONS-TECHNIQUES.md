# MC-ROBUSTNESS-R4-001 — Décisions techniques

## D-R4-01 — Qualification locale uniquement

La qualification de Mousse-controler est exécutée localement sous Windows.
GitHub sert au versionnement, aux PR et à la conservation des preuves. GitHub
Actions et les services CI externes sont exclus.

Conséquence : aucun fichier `.github/workflows/`, runner hébergé ou dépendance à
un état CI distant n'est introduit.

## D-R4-02 — Profils fermés

L'orchestrateur utilise une liste de phases définie dans le code. Il ne découvre
pas et n'exécute pas automatiquement les scripts de diagnostic. Le profil
`full-local` est exactement la concaténation des profils `software` et `build`.

Les diagnostics matériels ne sont pas une option de l'orchestrateur. Ils
restent accessibles uniquement par leurs commandes dédiées et doivent faire
l'objet d'une autorisation explicite distincte.

## D-R4-03 — Découverte contrôlée des outils Windows

Roslyn est recherché dans `VSINSTALLDIR`, puis dans les installations retournées
par `vswhere` avec la composante MSBuild. Le SDK Windows provient de
`KitsRoot10`; la version la plus haute n'est retenue que si elle possède
`windows.winmd` et les contrats Foundation requis. Les références .NET
Framework restent celles de `v4.0.30319`, en privilégiant Framework64. Les
outils MSIX viennent du même SDK validé.

Cette découverte remplace les chemins Visual Studio/SDK versionnés en dur, sans
migration de framework, changement de manifeste, d'options, de ressources ou
de contrat de sortie.

## D-R4-04 — Logs en flux continu

Les sous-processus écrivent directement dans le log de phase. Une capture en
pipe non drainée peut bloquer une suite verbeuse et perturber les tests de
temps ; l'écriture continue évite ce couplage tout en conservant la preuve.

## D-R4-05 — Délais de test séparés

Le test dédié au délai de démarrage HOGP garde 300 ms. Les cas qui testent une
commande, une récupération ou une quarantaine utilisent 1,5 s uniquement pour
la création du processus Python simulé. Les délais du produit et les assertions
sur les opérations restent inchangés.

## D-R4-06 — Reproductibilité mesurée, pas supposée

Chaque artefact reçoit chemin relatif, taille et SHA-256, avec version de
compilateur et SDK. Ces données permettent de comparer des exécutions mais ne
constituent pas une promesse de binaire bit-à-bit reproductible.
