# Décisions techniques R5

## DT-R5-01 — Repli borné sur un sommet

Conserver le rejet historique afin de ne pas modifier les sorties ordinaires.
Après 10 000 échecs, choisir un sommet avec le RNG fourni. Un sommet d'un
polygone validé appartient à la zone ; le coût est borné et la reproductibilité
est préservée. Une triangulation ou un scan-line changerait davantage la
distribution et augmenterait le risque pour un bénéfice non requis.

## DT-R5-02 — Unicité avant insertion

Centraliser la seule primitive réellement dupliquée : tester le nom puis
insérer dans le dictionnaire. Commandes, actions et événements passent par
cette primitive. La validation finale du registre reste une défense de forme,
mais n'est plus chargée de découvrir un doublon déjà perdu.

## DT-R5-03 — Compatibilité des paramètres inconnus

Ne pas activer de rejet strict. Le catalogue annonce explicitement
`additional_parameters_allowed: true` et un test de compatibilité protège ce
comportement. Une évolution nécessiterait une version de contrat et une décision
API séparée.

## DT-R5-04 — Pas de refactoring structurel dans cette PR

Conserver les deux séquenceurs, les deux systèmes de persistance et les gros
composants. Leur séparation reflète des contrats distincts ; aucune extraction
faible risque avec réduction mesurable n'a été isolée. Les travaux sont
documentés sans être présentés comme terminés.

## DT-R5-05 — Conservation des sources C++ HOGP

Le chemin actif est démontré, mais l'absence d'usage manuel/diagnostic des deux
projets C++ ne l'est pas. Ils restent donc dans le dépôt. L'implémentation active
et le descripteur HID ne sont pas modifiés.
