# Architecture MC-MOUSE-ACTIONS-001

```text
client loopback ── bearer ──► CommandGateway ─► ActionExecutor (file unique)
                                      │                 │
                                      │                 ├─ journal anti-rejeu
                                      │                 ├─ MouseController ─ HOGP
                                      │                 └─ CaptureBroker
                                      └─ WebSocket loopback ◄─ ActionRegistry

MonOrdinateur / PositionAgent visible
  position + poll capture ───── HTTPS/TLS pin/HMAC ────► mini-PC
  PNG moniteur sous curseur ─── HTTPS/TLS pin/HMAC ───► CaptureBroker
```

Le plan d'exécution est strictement séquentiel pour éviter le mélange de
rapports non idempotents. Les bornes portent sur file, nombre d'actions,
clics, durées, rapports de roulette, abonnés WebSocket, captures, octets et
rétention. L'arrêt d'urgence annule les contrôles, libère les boutons et arrête
le transport sous le verrou historique.

Le journal local conserve chaque identifiant et dernier état. Au démarrage,
`ACCEPTED` ou `RUNNING` devient `UNKNOWN`; l'identifiant reste occupé. Une
reconnexion HOGP ne consulte jamais la file et ne peut donc rejouer un rapport.

Le canal de capture ne donne pas à l'agent une API souris. L'agent découvre une
demande uniquement dans la réponse TLS épinglée à son POST de position. Il
relit curseur et écrans au moment effectif, copie le moniteur contenant le point,
indique visiblement la capture, puis signe l'enveloppe PNG. Aucun listener cible,
aucune capture périodique ou indépendante, aucun moteur d'analyse.

Le descripteur HOGP qualifié est conservé : boutons 1–5, X/Y int16, molette
verticale int8. La molette horizontale n'est pas déclarée et n'est pas simulée.
