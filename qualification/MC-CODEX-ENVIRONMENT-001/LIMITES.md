# Limites résiduelles

- Une nouvelle conversation Codex n'a pas été créée, car cela aurait ajouté
  un artefact utilisateur hors de cette PR. La persistance a été démontrée par
  des processus distincts et des seconds appels sans nouvelle décision. La
  règle projet rend le contexte explicite pour la prochaine conversation.
- Le secret DPAPI est volontairement lié au compte et à la machine. Une reprise
  après perte complète du mini-PC demanderait un escrow externe approuvé, non
  fourni par ce mandat.
- La tâche locale est inactive et son dernier résultat vaut `1`. C'est un état
  opérationnel observé, pas un blocage de l'environnement Codex; aucune activation
  n'était autorisée.
- Le nouveau certificat n'est pas approuvé et le MSIX n'est pas installé. Ce sont
  les points d'arrêt explicitement demandés, pas des défauts de préparation.
- L'état d'une session interactive ne peut pas être inféré d'une commande SSH.
  L'inspecteur se limite à l'identifiant de session du processus visible.
