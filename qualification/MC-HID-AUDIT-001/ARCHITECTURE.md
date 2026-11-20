# Architecture recommandée

```text
client local autorisé
        │ commande authentifiée, TTL/idempotency key
        ▼
mini-pc-backend
  CommandGateway ──> MouseCommandEngine ──> PositionController
        │                    │                       │
        │                    └──────────────┐        │ mesure fraîche
        │                                   ▼        │
        │                           WindowsHogpEngine │
        │                                   │ BLE    │ HTTPS + HMAC
        │                                   ▼        │ (sortant cible)
        │                         pilote HID Windows  │
        │                                   │        │
        │                                   ▼        │
        └──────────────────────────── MonOrdinateur ──┘
                                      PositionAgent
                                      (GetCursorPos seulement)
```

## Frontières

- `CommandGateway` valide identité, durée de vie, bornes et idempotence ;
- `MouseCommandEngine` sérialise les actions et possède l'état des boutons ;
- `WindowsHogpEngine` traduit une action validée en rapport, sans connaître les
  coordonnées absolues ;
- `PositionController` est le seul composant autorisé à fermer la boucle ;
- `PositionReceiver` authentifie les mesures, rejette les replays et maintient
  un snapshot immuable ;
- `PositionAgent` observe et publie ; il n'expose aucun endpoint de commande.

Chaque interface possède un double en mémoire. Le matériel n'est requis que
pour les tests HOGP et de boucle complète.

## États de sécurité

```text
STOPPED -> ADVERTISING -> CONNECTED -> SUBSCRIBED -> READY
    ^            |            |            |           |
    └────────────┴────────────┴────────────┴── DEGRADED┘
```

Une transition inconnue ou une exception conduit à `DEGRADED`, puis à : rapport
de libération si possible, état boutons nul, purge des commandes, arrêt de la
publicité et refus de tout nouveau mouvement. `READY` exige simultanément Host
autorisé, lien chiffré/bondé, abonnement Report et retour position frais dans la
bonne session/topologie pour une commande absolue.

## Processus et installation

- mini-PC : deux processus au premier plan au maximum, contrôleur Python et
  moteur HOGP natif, lancés explicitement pendant la qualification ;
- cible : application utilisateur visible, démarrage automatique optionnel
  seulement après arbitrage, jamais service Session 0 ;
- configuration locale : JSON sans secret ; secrets dans DPAPI/ACL ;
- journaux structurés sans coordonnées historiques par défaut, sans adresse,
  clé, identifiant matériel ni contenu applicatif ; rotation bornée ;
- bouton/commande d'arrêt local sur les deux machines. L'arrêt du mini-PC est
  fail-closed même si le LAN est perdu.

## Contrats minimaux

### `IHogpTransport`

`start()`, `stop()`, `state()`, `send_relative(dx,dy,wheel,buttons)`,
`release_all()`. Valeurs bornées avant sérialisation ; aucun rejeu après erreur.

### `IPositionSnapshot`

Retourne position, génération écran, session, séquence, âge monotone et état de
validité. Aucun appel réseau depuis la boucle de calcul.

### Endpoint agent

`POST /v1/position` avec JSON borné et en-têtes `X-Agent-Key`, `X-Signature`.
Réponse `202 {"accepted_seq":42}` seulement. Les chemins supplémentaires, les
méthodes de commande et les corps de réponse exécutables sont interdits.

## Défense en profondeur

- Bluetooth : bonding volontaire, chiffrement requis, Host unique attendu,
  publicité découvrable limitée au mode appairage ;
- LAN : écoute mini-PC sur interface privée choisie, TLS, pinning, HMAC par
  agent, anti-rejeu, limite de taille/débit ;
- commandes : TTL, identifiant idempotent, enveloppe de mouvement, limites de
  fréquence et nombre d'itérations ;
- boutons : propriétaire unique, watchdog et libération sur toutes sorties ;
- sessions : `WM_WTSSESSION_CHANGE`, session console active et input desktop ;
- opérateur : états visibles et arrêt immédiat local.

## Repli

Si le serveur HOGP Windows/Realtek échoue malgré une implémentation conforme,
conserver toutes les interfaces et remplacer uniquement `IHogpTransport` par un
module BLE HID externe programmable. Aucun achat ou changement d'OS n'est
implicite.
