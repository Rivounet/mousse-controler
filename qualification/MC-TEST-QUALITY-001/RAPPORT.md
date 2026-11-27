# MC-TEST-QUALITY-001 — builds, mesure et gouvernance

## Objectif

Fermer les derniers écarts de la stratégie de tests : qualifier tous les
artefacts actifs, attribuer chaque module Python à des tests, couvrir les
frontières client/DPAPI encore absentes et conventionner la preuve locale sans
introduire de CI externe.

## Corrections

- le profil `build` fabrique séparément PositionAgent, PairingTool,
  MouseWitness et le MSIX HOGP non signé ;
- chaque phase exige la présence de son artefact avant de pouvoir réussir ;
- le staging HOGP est unique, borné au répertoire de sortie sélectionné et
  supprimé en `finally` ;
- `command_client` possède des tests comportementaux d'enveloppe,
  authentification, loopback, timeout et traduction d'erreur HTTP ;
- DPAPI possède un round-trip CurrentUser avec secret aléatoire non persisté et
  un test de refus Base64 ;
- les secrets DPAPI du runtime et du client de commande sont convertis en
  tampons mutables puis écrasés à la fermeture ; le test système vérifie cet
  effacement ;
- une mesure AST sans plugin produit la matrice module-vers-tests, les cas par
  couche, les assertions, lectures de source et attentes temporelles ;
- le modèle de PR demande SHA, arbre, compteurs, builds, exclusions et rapport.

## Corrections de contre-revue

- une qualification acquiert désormais son répertoire de sortie par création
  atomique et exclusive ; tout chemin préexistant, même vide, rend l'exécution
  `BLOCKED` avant la première phase et n'est jamais modifié ;
- cette précondition empêche une exécution de lire des métadonnées de tests ou
  des artefacts périmés, ainsi que deux exécutions concurrentes de partager
  leurs preuves ;
- un échec de construction du service applicatif ou de la passerelle de
  commandes ferme immédiatement le runtime partiellement composé : worker
  d'actions, contrôleur et secrets mutables sont tous nettoyés ;
- les 18 tests ciblés d'orchestration et de cycle de vie passent, avec les
  chemins vide/périmé et les deux constructeurs couverts ;
- le point d'entrée historique `run_r0_software_tests.py` initialise désormais
  explicitement la racine du dépôt avant son import et une régression le lance
  depuis un répertoire externe ;
- les commandes opératoires ont été réalignées sur les niveaux `unit`,
  `contract`, `integration` et `qualification`, sans réécrire les preuves
  historiques.

## Mesures de développement

- modules Python de production avec propriétaire direct : 18/18 ;
- cas découverts dans `unit`, `contract`, `qualification`, `integration` et
  `system` : 254 ;
- micro-pollings `time.sleep` de 10 ms ou moins : 0 ;
- lectures de source dans les tests : 36 ; attentes `time.sleep` restantes :
  11, réservées aux fenêtres négatives et deadlines ;
- tests ciblés client, DPAPI et mesure : 6/6 PASS ;
- tests contrôleur, trajectoire et mesure : 46/46 PASS ;
- profil `fast` final de développement : 148/148 PASS ;
- profil `integration` final de développement : 180/180 PASS.

Les quatre builds de développement ont réussi. Les empreintes officielles sont
publiées depuis la qualification du commit propre, et non depuis cet arbre de
développement.

## Limites explicites

La matrice de propriété n'est pas une couverture de lignes/branches et ne
mesure pas la qualité des assertions. Aucun outil externe de couverture ou de
mutation n'est ajouté sans décision de dépendance. Les contrats C# de capture
et reconnexion conservent des assertions statiques, complétées par compilation
stricte et tests transactionnels PowerShell, mais sans instrumentation interne
du binaire. Les sept diagnostics matériels et toute opération réelle restent
hors porte.

## Gouvernance

L'option B conserve la qualification locale Windows. `main` est protégé sans
statut CI requis : pull request, historique linéaire, conversations résolues,
administrateurs inclus, force-push et suppression refusés. Fusion, installation
et déploiement restent soumis à des décisions séparées.

La preuve officielle `full-local`, l'état exact de la protection et les
empreintes des quatre builds sont publiés sur la PR Draft après commit.
