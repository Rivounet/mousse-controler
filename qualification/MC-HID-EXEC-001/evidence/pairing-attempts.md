# Tentatives d'appairage expurgées

| Tentative | Contexte | Résultat |
|---|---|---|
| 1 | session interactive 1, API standard, minimum MITM | `Failed`, aucune paire |
| 2 | session interactive 1, minimum chiffrement | `Failed`, aucune paire |
| 3 | outil C# Custom Pairing, `ConfirmOnly` reçu et accepté | `Failed`, protection utilisée `None`, aucune paire |
| 4 | identité MSIX vérifiée, publicité stabilisée `status=2`, session interactive 1 | `ConfirmOnly` reçu et accepté, `Failed`, protection utilisée `None`, aucune paire |
| 5 | fenêtre système de pairabilité temporaire et réversible | `ConfirmOnly`, `Paired`, protection utilisée `Encryption` |
| 6 | requalification `DESKTOP-NPIHO8K`, SHA `399ac53`, fenêtre ouverte mais notification backend non validée | scan/Inspect uniques, `ConfirmOnly`, `Failed`, protection `None`, aucune paire ; backend `BTHUSB 37`, deux hôtes `BTHUSB 29` |

La corrélation des événements a montré que la cible attendait la réponse tandis
que le mini-PC rejetait l'authentification entrante. L'ouverture temporaire de
la pairabilité locale a supprimé ce rejet. La paire a ensuite été observée sur
les deux machines. Les adresses, identifiants AEP, comptes et IP privées sont
omis.

La tentative 6 corrige l'interprétation historique : ouvrir la pairabilité rend
la demande recevable mais ne vaut pas acceptation automatique sur Windows
Desktop. Le consentement système backend est requis une fois pour créer le bond.
La qualification courante doit ensuite prouver que ce bond persiste et se
reconnecte sans intervention.
