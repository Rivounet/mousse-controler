# MC-ROBUSTNESS-R5-001 — Rapport

## Verdict

**PASS ciblé pour C-13 et C-14, travaux structurels différés.**

La branche part de `main` au SHA obligatoire
`c5d8ef6bdb06b0fb6295b946d0be578956e35d93`. La correction reste limitée à
l'échantillonnage des polygones extrêmes et à l'insertion sans écrasement dans
le catalogue. Aucun contrat public, format persistant, état, délai HOGP,
descripteur HID, mécanisme d'ordonnancement ou règle de validation géométrique
n'est modifié.

## Résultats

- C-13 : reproduction exacte de 7 échecs sur 20 graines pour le triangle
  `[(0,0),(16383,1),(16382,1)]`; après correction, 0 échec sur les géométries
  extrêmes couvertes et résultats reproductibles.
- C-14 : commandes, actions et événements refusent un identifiant déjà présent
  avant toute mutation du registre.
- Paramètres inconnus : tolérance existante conservée et testée, car un rejet
  strict serait une rupture du contrat public.
- C-09 : sources C++ conservées faute de preuve sur leur absence d'usage manuel
  ou diagnostic ; moteur MSIX actif identifié comme PowerShell/WinRT.
- C-11/C-12/C-17 : extractions différées ; les frontières proposées croisent
  les garanties de sûreté et de persistance sans réduction isolée démontrée.

La qualification finale et le SHA qualifié sont consignés dans
[TESTS.md](TESTS.md) et [evidence/EXECUTIONS.md](evidence/EXECUTIONS.md).

## Périmètre opérationnel

Aucun accès à `MonOrdinateur`, HID réel, capture réelle, installation,
déploiement, tâche Windows, modification de protection, GitHub Actions ou CI
externe. Les diagnostics matériels restent exclus.

## Réserves et suite

Les gros composants recensés restent volontairement inchangés. Une éventuelle
extraction de l'exécution d'actions, de la persistance, de la capture ou du
transport de l'agent doit faire l'objet d'une PR indépendante avec
caractérisation comportementale et mesure avant/après. Les sources HOGP C++ ne
pourront être archivées qu'après confirmation de leurs consommateurs manuels.

