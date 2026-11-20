# MC-ROBUSTNESS-R1-001 — rapport de qualification

Date : 20 novembre 2026

Base obligatoire : `d8b412f8620ba85de1b9e864af2f11ed31271006`

Branche : `fix/mc-robustness-r1-001`

## Verdict

**PASS_WITH_RESERVATIONS** pour la qualification logicielle R1.

Les défauts C-02, C-05 et C-06 sont corrigés dans les limites des doubles
logiciels. Aucun essai matériel ne permet d'affirmer que le Host Bluetooth a
physiquement reçu un relâchement ; le code conserve donc `UNKNOWN` et publie
explicitement `release_confirmed=false` après une transition ambiguë.

## Résultats fonctionnels

### C-02 — boutons incertains

- `ActionExecutionError` distingue désormais une émission non idempotente d'un
  état de boutons spécifiquement incertain.
- Les six familles concernées (`press`, `release`, `hold`, `drag`,
  `move_with_buttons`, `click`) passent en sécurité pour `stop`, `continue` et
  `retry`.
- L'action reste `UNKNOWN`, toutes les opérations sont réveillées/annulées,
  l'arrêt contrôleur tente `release_all`, et l'exécuteur refuse toute nouvelle
  soumission.
- Une séquence ne poursuit jamais le prochain enfant après un enfant bouton
  ambigu, même si sa politique vaut `continue`.
- Aucune action non idempotente ambiguë n'est rejouée.

### C-05 — arrêt global

- L'intention est publiée séparément à `ActionExecutor` et `SequenceRunner`
  avant l'arrêt du contrôleur partagé.
- Les attentes et pauses sont réveillées ; les états MOVING, WAITING et PAUSED
  convergent vers STOPPED.
- Les arrêts répétés et concurrents restent idempotents au niveau des effets.
- Une erreur d'un moteur est collectée sans empêcher la notification du moteur
  suivant ni la tentative d'arrêt contrôleur.

### C-06 — fermeture de la file

- La fermeture et la soumission sont sérialisées sous le verrou d'admission.
- Les entrées non commencées deviennent durablement `CANCELLED` avec
  `EXECUTOR_CLOSED`.
- L'action active est réveillée ; un simple `wait` devient `CANCELLED`.
- Un `hold` déjà émis pendant la fermeture devient `UNKNOWN`, jamais
  `CANCELLED`, car le relâchement tenté n'est pas une preuve physique.
- Le worker reçoit un sentinel après drainage et termine dans la borne simulée.
- Le journal et le registre `.ids` conservent les états et bloquent la
  resoumission après redémarrage.

## Périmètre des changements

- moteur d'actions et cycle de fermeture ;
- coordination de la commande globale `stop` ;
- publication d'arrêt du séquenceur historique ;
- tests R0 A01/A04/A05 adaptés au comportement corrigé ; A02 et A03 conservés ;
- tests comportementaux R1 et documentation.

Aucun protocole HOGP, descripteur HID, serveur LAN, quota de captures, agent C#,
configuration ou composant de production n'a été modifié.

## Réserves

1. Les doubles prouvent l'ordonnancement et les états logiciels, pas la réception
   physique du rapport de relâchement par `MonOrdinateur`.
2. Le délai du worker de `close()` est borné. La durée d'un appel synchrone déjà
   bloqué dans le transport HOGP reste dépendante de C-01 et appartient à R2 ;
   R1 ne contourne ni ne corrige ce canal.
3. Aucune qualification matérielle, aucun HID réel, aucune capture et aucun
   accès à la cible n'ont été réalisés.

## Correctif de revue de la PR #14

La revue du SHA `c73fab0da4f71f0770d1888106dfc02bec722ed1` a identifié
une fenêtre entre la fin normale de l'attente d'un `hold` et son relâchement.
Le contrôle de `button_state_uncertain`, déjà appliqué à `drag` et
`move_with_buttons`, est désormais exécuté après le `finally` de `hold`.
Une incertitude lève `ActionExecutionError` avec `emitted=true`, conserve
`UNKNOWN`, déclenche la quarantaine et publie `release_confirmed=false`.

Un double synchronisé force l'arrêt exactement avant l'acquisition du verrou
de relâchement. Les politiques `stop`, `continue` et `retry`, l'enfant de
séquence, le non-rejeu après redémarrage et les chemins de succès de `drag` et
`move_with_buttons` sont couverts. La suite logicielle compte maintenant
**222/222 PASS**.

## Rollback

Le rollback Git consiste à revenir au parent du commit R1. Aucun état de
production, journal réel, appairage ou configuration n'a été touché. Ne pas
appliquer un rollback logiciel à une production active sans la procédure de
synchronisation et une décision séparée.
