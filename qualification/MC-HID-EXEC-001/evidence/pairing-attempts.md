# Tentatives d'appairage expurgées

| Tentative | Contexte | Résultat |
|---|---|---|
| 1 | session interactive 1, API standard, minimum MITM | `Failed`, aucune paire |
| 2 | session interactive 1, minimum chiffrement | `Failed`, aucune paire |
| 3 | outil C# Custom Pairing, `ConfirmOnly` reçu et accepté | `Failed`, protection utilisée `None`, aucune paire |

La publicité non packagée est ensuite passée à `Aborted`; aucune nouvelle
tentative ne doit être faite avant installation du paquet avec capacité
`bluetooth`. Les adresses, identifiants AEP et IP privées sont omis.
