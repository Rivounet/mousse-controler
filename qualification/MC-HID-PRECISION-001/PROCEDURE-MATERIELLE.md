# MC-HID-PRECISION-001 — Requalification matérielle minimale

Cette procédure est **préparée mais non autorisée par le mandat logiciel**. Elle
ne peut commencer qu'après publication de `SOFTWARE_FIX_QUALIFIED`, déploiement
autorisé du SHA qualifié et confirmation immédiate de la disponibilité de
l'utilisateur devant MonOrdinateur.

## Préconditions

- arrêt d'urgence immédiatement accessible et contrôleur/PositionAgent sains ;
- HOGP abonné, `buttons=0`, position fraîche, aucune action active ;
- surface sûre, positions initiale et cible dans la topologie observée ;
- aucune capture, aucun clic, aucun défilement ; arrêt au premier résultat
  incertain, sans répétition automatique.

## Scénario unique

1. Soumettre une seule action `move_relative_confirmed` de `-10` pixels en X,
   Y inchangé, avec `tolerance_px=0`, `timeout_seconds=3`, `max_step=16`,
   `max_iterations=16`, `max_total_movement=64`, limites de stagnation,
   oscillation et absence de progrès actives.
2. Vérifier l'état `CONFIRMED` et l'écart observé de exactement -10 pixels.
3. Soumettre une seule action `move_relative_confirmed` de `+10` pixels en X
   avec les mêmes bornes.
4. Vérifier le retour exact à la position initiale, `buttons=0`, aucune action
   résiduelle et la corrélation des événements WebSocket.
5. Arrêter le scénario et annoncer immédiatement que la souris est libre.

Toute anomalie produit `MATERIAL_FAIL`. Aucun rattrapage manuel, troisième
mouvement ou capture supplémentaire n'est permis sans nouveau mandat.

## Exécution finale du 21 novembre 2026

Cette porte a ensuite été couverte par le mandat plus large
`MC-FINAL-VALIDATION-001`, après consentement immédiat de l'utilisateur. Les
deux déplacements confirmés ont atteint exactement -10 puis +10 pixels avec
retour exact, événements corrélés, boutons à zéro et aucune action résiduelle.
Le `MATERIAL_FAIL` antérieur reste conservé comme preuve du contrat HID brut.
