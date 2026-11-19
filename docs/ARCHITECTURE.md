# Architecture technique — cible et inconnues

## Parcours des commandes

```text
Client API autorisé
    │ HTTP local / LAN privé (à choisir)
    ▼
mini-pc-backend
    ├── Réception et authentification API
    ├── Validation, file de commandes, temporisation
    ├── Sécurité : bornes, arrêt immédiat, journalisation
    └── Adaptateur d'émulation Bluetooth HID
                 │
                 │ Bluetooth appairé
                 ▼
PC Windows cible (également poste de développement Codex)
    └── Pile Bluetooth + pilote HID natifs → curseur
```

## Contraintes validées

- Le code est **développé localement via Codex Desktop sur PC Windows**.
- Son exécution, ses diagnostics et ses tests d'intégration s'effectuent sur **mini-pc-backend**.
- Le PC cible est Windows, reçoit les événements Bluetooth HID, sans application réceptrice dédiée.
- La souris physique du PC doit rester utilisable ; le système ne doit pas exiger le remplacement de son pilote.
- Les commandes proviennent d'une API ; elles ne sont pas générées directement depuis le PC cible par un agent installé sur celui-ci.

## Points **non vérifiés**

- Version exacte de Windows et caractéristiques Bluetooth sur mini-pc-backend ; inventaire à obtenir.
- Support effectif du rôle **périphérique BLE**, du serveur GATT et du profil **HID over GATT (HOGP)** sous l'OS et le pilote présents.
- Gestion de l'appairage, publicité BLE, reconnexion, stabilité en fonctionnement prolongé.
- Accès distant/permissions et mécanisme de transfert depuis Codex Desktop.
- Contrat précis de l'API, langage, bibliothèque Bluetooth et mode de lancement.

La présence d'un adaptateur Bluetooth ou d'un pilote HID **ne prouve pas** à elle seule la capacité à simuler une souris Bluetooth. Il faut une preuve d'appairage et de réception d'événements côté cible.

## Interfaces envisagées (proposition, non implémentée)

- `move(dx, dy)` : mouvement relatif en unités HID.
- `click(button)` : appui puis relâchement ; `press`/`release` si glisser-déposer ultérieur.
- `scroll(delta)` : défilement.
- `status()`, `stop()` : état et arrêt d'urgence.

Les coordonnées absolues nécessitent une connaissance fiable de la position et une calibration distincte ; elles ne sont **pas promises au MVP**.

## Sécurité dès le prototype

API liée par défaut à `127.0.0.1` sur mini-PC ; toute ouverture LAN doit être volontaire, filtrée et authentifiée. Limiter les amplitudes et fréquences de mouvements, prévoir expiration des commandes en attente, journaliser sans secrets. Tester dans une session contrôlée, avec possibilité de couper immédiatement l'émission Bluetooth/API. Aucun contrôle invisible du PC cible, aucun contournement des politiques Bluetooth.

## Alternative si le Bluetooth natif échoue

Comparer les solutions selon preuve de compatibilité, coût, maintien d'une absence d'agent sur le PC cible, simplicité de déploiement : OS/hôte différent si compatible, puis périphérique externe Bluetooth HID programmable. Toute modification matérielle est une décision explicite.
