# Architecture technique

## Parcours cible

```text
Client API autorisé
    │ HTTP local par défaut
    ▼
mini-pc-backend
    ├── API et authentification
    ├── validation, file bornée et expiration
    ├── arrêt immédiat et journalisation expurgée
    └── interface HidAdapter
          ├── SimulatedHidAdapter (tests)
          └── WindowsHogpAdapter (production)
                         │ Bluetooth LE appairé
                         ▼
MonOrdinateur
    ├── pile Bluetooth + pilote HID natifs → curseur
    └── agent GetCursorPos ── HTTPS/HMAC sortant ──> retour mini-PC
```

## Rôles des machines

- **mini-pc-backend** : Codex, clone Git, développement, tests, exécution,
  future API et émission HOGP.
- **MonOrdinateur** : cible Bluetooth HID native et agent utilisateur minimal de
  position. L'agent ne reçoit ni n'exécute de commande souris et n'analyse pas
  l'écran.
- **GitHub** : source versionnée officielle, sans être un mécanisme d'exécution.

## État qualifié au 19 novembre 2026

Le mini-PC exécute Windows 11 Professionnel 26H2 x64 avec un adaptateur Realtek.
WinRT retourne `true` pour BLE et le rôle périphérique. Les API de serveur GATT,
création de caractéristiques, notification, publicité et appairage sont présentes.
Le service Bluetooth principal est actif.

Ces résultats prouvent les préconditions, pas HOGP complet : le fournisseur HID
et sa forme minimale ont été créés sans publicité, mais jamais publiés ou
appairés. Le verdict produit reste `GO_WITH_RESERVATIONS` jusqu'à la
démonstration décrite dans
[`PROTOCOLE-HID.md`](../qualification/MC-REPRISE-001/PROTOCOLE-HID.md).

Le complément MC-HID-AUDIT-002 a confirmé que `Off` était la cause de
`RadioNotAvailable` : radio `On`, les fournisseurs HID et Battery, quatre
caractéristiques HID et Report Reference retournent `Success`. Device
Information retourne `DisabledByPolicy`, service réservé par Windows. Aucun
appel à la publicité, à l'appairage ou aux notifications ; état final `Off`.

## Contraintes HOGP à respecter

- service HID `0x1812`, Report Map de souris relative et Report characteristic ;
- services/attributs complémentaires exigés par le profil ;
- notifications vers le Host et gestion du Client Characteristic Configuration ;
- lien chiffré, mode bondable et appairage ;
- publicité connectable/découvrable arrêtée explicitement ;
- aucune émission avant abonnement du Host et consentement de la session de test.

## Organisation locale

```text
Mousse-controler/
    source/       # clone Git et tests
    releases/     # artefacts immuables par SHA
    staging/      # préparation contrôlée
    state/        # activation, verrous et états
    logs/         # journaux locaux expurgés
```

Le clone n'est jamais remplacé par une release. Les composants SSH/SFTP restent
isolés dans `scripts/remote/` et ne sont pas une dépendance de l'application.

## Limites du MVP

Commandes prévues : `move(dx, dy)`, `click(button)`, `press`, `release`,
`scroll(delta)`, `status()` et `stop()`. Les coordonnées absolues, l'analyse de
l'écran et le contrôle intelligent des applications sont hors périmètre.

L'API de commande est liée à `127.0.0.1` par défaut. Un endpoint LAN distinct,
HTTPS et authentifié, reçoit uniquement les mesures de position émises par la
cible ; il n'est pas une API de commande.

L'architecture détaillée et la boucle de position sont spécifiées dans
[`MC-HID-AUDIT-001/ARCHITECTURE.md`](../qualification/MC-HID-AUDIT-001/ARCHITECTURE.md).

## Alternative en cas de NO-GO

Si le prototype conforme échoue sur la pile Windows/Realtek, comparer d'abord un
adaptateur externe programmable capable d'HOGP. Un changement d'OS, de pilote ou
de matériel nécessite une décision explicite ; aucune installation implicite.
