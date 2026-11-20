# Tentatives d'appairage expurgées

| Tentative | Contexte | Résultat |
|---|---|---|
| 1 | session interactive 1, API standard, minimum MITM | `Failed`, aucune paire |
| 2 | session interactive 1, minimum chiffrement | `Failed`, aucune paire |
| 3 | outil C# Custom Pairing, `ConfirmOnly` reçu et accepté | `Failed`, protection utilisée `None`, aucune paire |
| 4 | identité MSIX vérifiée, publicité stabilisée `status=2`, session interactive 1 | `ConfirmOnly` reçu et accepté, `Failed`, protection utilisée `None`, aucune paire |
| 5 | fenêtre système de pairabilité temporaire et réversible | `ConfirmOnly`, `Paired`, protection utilisée `Encryption` |

La corrélation des événements a montré que la cible attendait la réponse tandis
que le mini-PC rejetait l'authentification entrante. L'ouverture temporaire de
la pairabilité locale a supprimé ce rejet. La paire a ensuite été observée sur
les deux machines. Les adresses, identifiants AEP, comptes et IP privées sont
omis.
