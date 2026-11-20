# Tentatives d'appairage expurgées

| Tentative | Contexte | Résultat |
|---|---|---|
| 1 | session interactive 1, API standard, minimum MITM | `Failed`, aucune paire |
| 2 | session interactive 1, minimum chiffrement | `Failed`, aucune paire |
| 3 | outil C# Custom Pairing, `ConfirmOnly` reçu et accepté | `Failed`, protection utilisée `None`, aucune paire |
| 4 | identité MSIX vérifiée, publicité stabilisée `status=2`, session interactive 1 | `ConfirmOnly` reçu et accepté, `Failed`, protection utilisée `None`, aucune paire |

La publicité packagée est passée transitoirement par `Aborted` avant de se
stabiliser en `StartedWithoutAllAdvertisementData`. Le moteur a signalé trop tôt
un échec de commande, alors que son état ultérieur confirmait la publicité
active. Aucune nouvelle tentative ne doit précéder l'instrumentation de l'échec
de bonding/chiffrement. Les adresses, identifiants AEP et IP privées sont omis.
