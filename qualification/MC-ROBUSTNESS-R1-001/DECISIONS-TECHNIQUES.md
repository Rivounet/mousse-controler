# MC-ROBUSTNESS-R1-001 — décisions techniques

## D-R1-01 — distinguer incertitude bouton et émission générique

`ActionExecutionError` porte `button_state_uncertain`. Cette information suit
l'erreur jusque dans les séquences et prime sur `error_policy`. Une liste de
codes ou de chaînes aurait été plus fragile et aurait perdu la cause lors de
l'encapsulation parent/enfant.

## D-R1-02 — quarantaine de l'exécuteur

Une incertitude bouton publie l'arrêt à tous les contrôles, tente l'arrêt du
contrôleur, conserve `UNKNOWN` et interdit les nouvelles soumissions. Il n'y a
ni nouveau superviseur, ni reprise implicite. La remise en service reste un
nouveau cycle explicite du composant.

## D-R1-03 — publication avant arrêt matériel

`request_stop()` ne prend pas le verrou HID : il positionne les événements et
réveille les attentes. `CommandGateway` l'appelle sur les deux moteurs puis
appelle une seule fois `MouseController.emergency_stop()`. Cette séparation
évite qu'un arrêt lent du premier moteur empêche de notifier le second.

## D-R1-04 — fermeture par admission atomique et drainage

`submit()` et le début de `close()` partagent le verrou d'admission. Après
fermeture, la file est drainée explicitement et chaque entrée `ACCEPTED` reçoit
un état terminal journalisé. Le worker traite seulement l'action qu'il avait
déjà retirée puis le sentinel.

## D-R1-05 — ne pas transformer une tentative en confirmation

Même si le double de transport accepte `release_all`, le résultat publié reste
`release_confirmed=false`. Une action bouton active au moment de l'arrêt est
`UNKNOWN` si son relâchement n'a pas de preuve indépendante. Cette décision est
plus conservatrice que `CANCELLED` et respecte le contrat de non-rejeu.

## D-R1-06 — frontière avec R2

R1 borne la terminaison du worker et ne modifie pas le protocole HOGP. Un appel
transport natif déjà bloqué reste le défaut C-01, dont le traitement appartient
au lot R2. Aucun thread de contournement ni terminaison forcée du processus
WinRT n'est ajouté dans R1.
