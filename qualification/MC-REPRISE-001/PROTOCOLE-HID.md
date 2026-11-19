# Protocole contrôlé de démonstration HOGP

**Statut : préparé, non exécuté. Autorisation explicite requise.**

## But

Passer du verdict `GO_WITH_RESERVATIONS` à `GO` ou `NO-GO` en démontrant sur
le matériel réel que `mini-pc-backend` peut être découvert, appairé et reconnu
par `MonOrdinateur` comme souris Bluetooth native.

## Préconditions

- Session de test convenue, utilisateur devant `MonOrdinateur`.
- Souris physique disponible et document sans risque ouvert comme surface de test.
- Prototype lancé au premier plan, sans démarrage automatique ni service persistant.
- Commande d'arrêt locale testée avant publicité : `Ctrl+C`, avec
  `StopAdvertising()` garanti dans un bloc de nettoyage.
- Aucun port réseau, pilote, service Windows ou paramètre Bluetooth modifié.

## Étapes soumises à autorisation

1. Créer localement le service HID `0x1812` et ses caractéristiques, Battery et
   Device Information requis, avec lecture/écriture/notification protégées par
   chiffrement. Effet : table GATT locale créée, pas encore visible.
2. Démarrer une publicité BLE connectable et découvrable sous un nom de test.
   Effet : `mini-pc-backend` devient visible à proximité. Arrêt : `Ctrl+C` ou
   commande `stop`, qui appelle `StopAdvertising()` et libère les providers.
3. Depuis les paramètres Bluetooth de `MonOrdinateur`, lancer l'appairage.
   Effet : création d'un bond Bluetooth révocable sur les deux machines.
4. Vérifier, sans mouvement, que Windows charge son transport HID BLE natif et
   classe le périphérique comme souris.
5. Dans une zone sûre, émettre successivement : déplacement relatif de +5 px en
   X, déplacement de -5 px, un cran de défilement, puis un clic uniquement si
   l'utilisateur le confirme à ce moment. Aucun mouvement continu.
6. Arrêter la publicité et le prototype, vérifier l'absence d'émission, puis
   supprimer l'appairage seulement si l'utilisateur le demande.

## Preuves et verdict

- `GO` : appairage, pilote HID natif et au moins un mouvement relatif observés.
- `NO-GO` : blocage reproductible du service HID, de la publicité, du bonding
  ou du chargement HID malgré une implémentation conforme.
- `INCOMPLETE` : essai interrompu ou observation ambiguë.

Ne publier ni adresse Bluetooth, identifiant de périphérique, capture de session
privée ou journaux Windows bruts.
