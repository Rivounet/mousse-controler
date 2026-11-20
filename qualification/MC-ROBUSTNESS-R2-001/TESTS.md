# MC-ROBUSTNESS-R2-001 — tests

## Suite ciblée

```powershell
$env:PYTHONPATH = 'src'
python -B -m unittest tests.test_r2_robustness tests.test_native_transport -v
```

Couverture HOGP :

- moteur vivant muet, sortie partielle et processus interrompu ;
- écriture de commande bloquée et réponse partielle ;
- `stderr` saturé ;
- commande active pendant arrêts concurrents ;
- transition bouton expirée, quarantaine et anti-rejeu après redémarrage ;
- échec simulé de `terminate` et `kill` ;
- contrat textuel de deadline WinRT.

Couverture LAN :

- en-têtes et corps lents ;
- en-têtes et corps `trickle` progressant avant chaque timeout d'inactivité,
  mais arrêtés par leur deadline absolue ;
- corps tronqué et déconnexion ;
- plafond de connexions et refus de l'excès ;
- timeout TLS simulé ;
- vrai TLS loopback avec certificat de test : handshake muet concurrent d'un
  handshake valide, sans blocage de l'accept-loop, puis libération des slots ;
- capture loopback de 24 Mio progressant normalement ;
- deux requêtes pipelinées sur une connexion persistante, y compris lorsque
  les octets de la seconde ont été lus avec les premiers en-têtes ;
- reprise par client sain ;
- HMAC et anti-rejeu via le handler HTTP borné.

Le certificat et sa clé privée sont des données de test auto-signées intégrées
au test, utilisables uniquement sur `127.0.0.1`. La vérification du client est
désactivée uniquement dans ce scénario. Cela ne qualifie ni le certificat de
production, ni Schannel, ni un trafic LAN réel.

## Caractérisations R0 adaptées

T01/T04 et N01/N02/N03 vérifient désormais les contrats corrigés. T02/T03
restent des tests fail-closed de réponse invalide et processus interrompu. Les
anciennes reproductions ne sont pas supprimées silencieusement.

## Suite complète

```powershell
python -B scripts/qualification/run_r0_software_tests.py
```

Le runner exclut les sept diagnostics matériels et ne peut appeler ni radio,
HID natif, capture, SSH, session cible ou tâche planifiée.

Les résultats sont consignés dans `evidence/EXECUTIONS.md`.
