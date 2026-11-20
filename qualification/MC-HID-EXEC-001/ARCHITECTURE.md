# Architecture réalisée

```text
API HTTP loopback + bearer DPAPI
              │
              ▼
CommandGateway ── SequenceRunner ── TrajectoryEngine
              │                         (pur, seedé)
              ▼
PositionController ── HogpTransport ── PowerShell/WinRT GATT/HOGP
       ▲                                      │ BLE HID
       │ HTTPS TLS épinglé + HMAC              ▼
PositionAgent .NET 4.8 ─────────────── MonOrdinateur / pilote HID natif
```

## Frontières de sécurité

- commandes liées à `127.0.0.1`, bearer secret DPAPI, TTL ≤5 s, identifiants
  idempotents et limite de débit ;
- position : flux cible→mini-PC uniquement, TLS 1.2+, certificat épinglé,
  HMAC-SHA-256, séquence monotone et fenêtre temporelle ;
- pare-feu : réseau privé, programme/port/hôte source exacts ;
- agent cible visible, sans listener, sans service et sans API d'entrée ;
- HOGP : identité MSIX, hôte Microsoft-signé compatible Smart App Control,
  propriétés chiffrées, aucun rapport sans client abonné, bornes int16 /
  int8, libération des boutons et arrêt de publicité.

## Séquences

Les zones utilisent les coordonnées physiques du bureau. La validation refuse
les dimensions nulles, polygones dégénérés et géométries non entièrement
contenues dans un écran. Le point cible seedé est conservé dans `StepResult`.
Chaque point de trajectoire est exécuté par la boucle de correction et l'arrivée
finale est confirmée par la mesure réelle, jamais par intégration estimée.
