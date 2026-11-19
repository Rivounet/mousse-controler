# Mousse-controler

Contrôle de la souris de **MonOrdinateur** depuis **mini-pc-backend**, au moyen
d'un périphérique Bluetooth HID natif et, à terme, de commandes reçues par une
API locale protégée.

> **Statut : reprise consolidée, faisabilité HOGP favorable mais non démontrée.**
> Les capacités BLE/GATT locales sont présentes ; aucune publicité, aucun
> appairage et aucun événement souris n'ont encore été exécutés.

## Organisation actuelle

1. **mini-pc-backend** : machine unique de développement et d'exécution.
   Codex, Git, Python, les tests, les diagnostics et la future émission HID y
   résident.
2. **MonOrdinateur** : cible Windows recevant les événements via ses pilotes HID
   natifs ; un agent utilisateur séparé publiera uniquement la position réelle
   du curseur sur un canal LAN privé sécurisé.
3. **GitHub** : source officielle du code et de la documentation. Le clone de
   développement reste séparé des releases et états d'exécution locaux.

L'analyse d'écran et le contrôle intelligent des applications ne font pas partie
du périmètre actuel.

## Architecture simple visée

```text
client autorisé
      │
      ▼
API locale protégée → validation / boucle / arrêt → adaptateur HOGP Windows
                        ▲                           │ Bluetooth LE
                        │ HTTPS + HMAC              ▼
                  agent position ← MonOrdinateur + pilote HID natif
```

L'adaptateur HID restera remplaçable et simulable. Les scripts SSH/SFTP et de
releases issus des travaux précédents sont conservés comme capacités secondaires
de maintenance et de rollback ; ils ne sont plus requis pour développer au
quotidien sur mini-pc-backend.

## Développement et tests

```powershell
python -m unittest discover
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bluetooth\diagnose.ps1
```

La suite locale compte 76 tests. Le diagnostic Bluetooth est strictement en
lecture seule : il ne crée pas de service GATT et ne démarre aucune publicité.

## État vérifié

- [x] Dépôt et travaux des PR #1 à #3 consolidés sans fusion.
- [x] Environnement réel de mini-pc-backend inventorié.
- [x] 76 tests locaux réussis.
- [x] Rôle périphérique BLE et API serveur GATT présents.
- [ ] Service HOGP créé et annoncé sur le matériel réel.
- [ ] Appairage avec MonOrdinateur et reconnaissance comme souris.
- [ ] Mouvement HID minimal observé.
- [ ] API de commandes intégrée et protégée.
- [ ] Agent de position diagnostiqué puis qualifié sur MonOrdinateur.

Le verdict détaillé est `GO_WITH_RESERVATIONS`. Le prochain essai nécessite une
autorisation explicite car il rendrait un service GATT visible, créerait un
appairage et pourrait émettre un événement souris.

## Documentation

- [Reprise et état courant](docs/REPRISE.md)
- [Rapport MC-REPRISE-001](qualification/MC-REPRISE-001/RAPPORT.md)
- [Audit et plan MC-HID-AUDIT-001](qualification/MC-HID-AUDIT-001/RAPPORT.md)
- [Roadmap](docs/ROADMAP.md) et [planning](docs/PLANNING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Développement et déploiement](docs/DEPLOIEMENT.md)
- [Accès distant secondaire](docs/ACCES-DISTANT-ET-SYNCHRONISATION.md)
- [Tests](docs/TESTS.md) et [décisions](docs/DECISIONS.md)
- [Consignes Codex](AGENTS.md)

Les mandats Codex restent exclusivement dans le chat. Les changements sont
publiés en PR Draft ; aucune fusion ou opération Bluetooth sensible n'est
implicite.
