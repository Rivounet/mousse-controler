# Instructions de travail — Codex sur mini-pc-backend

Ces consignes s'appliquent à toute intervention dans `Rivounet/mousse-controler`.

## Rôle et lieux

- **Développer, compiler et tester directement sur `mini-pc-backend`**, où Codex
  et le clone Git sont installés.
- Séparer le clone `source/` des releases et états d'exécution. Les outils
  SSH/SFTP existants sont secondaires : maintenance distante ou reprise, pas
  chemin normal de développement.
- `MonOrdinateur` reçoit les commandes par son **pilote Bluetooth HID natif**. Un **agent Windows visible** y mesure et transmet la position réelle sur LAN privé sécurisé ; cet agent ne reçoit ni n'exécute de commandes souris.
- Codex sur mini-pc-backend est responsable de l'intégration sur les deux machines dans le périmètre autorisé ; l'accès distant authentifié à MonOrdinateur doit être vérifié/établi sans supposer un accès à sa session interactive.
- **ChatGPT détient la responsabilité de la documentation de référence et peut effectuer des revues de code à la demande ou aux jalons convenus, sans revue systématique à chaque livraison**. Proposer les corrections documentaires dans le compte rendu ; ne pas déclarer un jalon validé sans vérification adaptée.

## Pour chaque mandat

1. Lire `docs/REPRISE.md` (état et mandat courant), puis `README.md`, `docs/ROADMAP.md`, `docs/PLANNING.md`, `docs/ARCHITECTURE.md` et les documents concernés.
2. Vérifier branche, état Git et fichiers préexistants. Ne jamais écraser des changements non liés.
3. Annoncer objectif, périmètre, risques et critères de réussite avant les modifications.
4. Faire une modification ciblée et testable. Utiliser une branche de travail et une PR pour les changements applicatifs ; ne pas pousser de code directement sur `main`.
5. Distinguer tests logiciels locaux et **preuves Bluetooth entre mini-pc-backend et MonOrdinateur**.
6. Fournir les résultats, commandes, SHA, fichiers modifiés, échecs, réserves et instructions de rollback.
7. Publier le diff, les tests et les preuves dans une PR Draft ; ChatGPT assure le suivi Git/GitHub et ne lance une revue de code approfondie que sur demande explicite ou au point de contrôle préalablement convenu. **Ne pas fusionner sans arbitrage explicite**.

## Sécurité / opérations

- Diagnostic initial **en lecture seule**. Aucun accès distant, port, outil ni droit administrateur n'est présumé disponible.
- Ne pas installer de service persistant, modifier le pare-feu, reconfigurer Bluetooth ou toucher à un service existant sans autorisation pertinente.
- Ne jamais publier de secrets ou d'identifiants, y compris dans les logs.
- L'API doit rester protégée ; éviter toute exposition réseau non justifiée.
- Ne pas émettre de clics/mouvements Bluetooth sans session de test autorisée et mécanisme d'arrêt effectif.
- Préserver la possibilité de retour arrière sur mini-PC. Ne pas faire de `git reset --hard`, `git clean -fdx`, `git pull` aveugle ni écraser des modifications inconnues dans la copie distante.
- Avant toute activation locale, vérifier SHA exact, état de la copie Git,
  permissions, espace disque et disponibilité du rollback ; relever ensuite le
  SHA réellement actif. Appliquer les mêmes contrôles d'identité d'hôte si une
  maintenance distante est exceptionnellement utilisée.
- Implémenter un mode `--dry-run`, des vérifications préalables, un verrou anti-déploiements concurrents, un contrôle de santé, une collecte de logs et un rollback sécurisé ; tester l'idempotence et les erreurs.
- Indiquer l'état d'avancement et le temps écoulé aux étapes clés d'un travail long ; signaler les blocages.

## Principes de conception

Privilégier les composants indépendants : réception API, validation/ordonnancement, moteur de séquences de zones, moteur de trajectoires, contrôleur de position sur mesures réelles, adaptateur HID et agent LAN sortant. Préférer un adaptateur simulé pour les tests unitaires. Ne pas supposer que Bluetooth Windows peut fonctionner comme périphérique HID tant que J2 ne l'a pas démontré. Les zones sont rectangle/cercle/polygone, avec point aléatoire interne ; les séquences A→B→C utilisent une attente temporisée ou une nouvelle commande. Les trajectoires courbes, vitesses variables et micro-variations pendant le mouvement sont configurables et testables, sans objectif de dissimulation d'automatisation ou d'usurpation Logitech. Éviter frameworks, services et abstractions non nécessaires au MVP.

## Sources de vérité

- Roadmap : `docs/ROADMAP.md`
- Tâches et états : `docs/PLANNING.md`
- Architecture : `docs/ARCHITECTURE.md`
- Déploiement : `docs/DEPLOIEMENT.md`
- Accès distant et synchronisation : `docs/ACCES-DISTANT-ET-SYNCHRONISATION.md`
- Tests / revue : `docs/TESTS.md`
- Décisions : `docs/DECISIONS.md`
- Reprise : `docs/REPRISE.md`

## Mandats, revue et GitHub

- **ChatGPT fournit intégralement les mandats Codex dans la conversation**, avec objectifs, périmètre autorisé, critères de validation, risques et format des preuves. **Les mandats ne sont pas publiés ni archivés dans GitHub.** Les décisions, états de jalons, rapports, preuves et revues restent versionnés.
- **ChatGPT supervise Git/GitHub** : état de `main`, branches, PR, SHA, changements préexistants, cohérence local/distant et absence de fusion implicite. **Réception d'une livraison ≠ déclenchement automatique d'une revue de code**.
- Codex exécute le mandat directement sur mini-pc-backend dans le périmètre
  autorisé et publie une PR **Draft** pour les changements applicatifs, sans
  fusion ; il fournit à ChatGPT les traces de validation.
- Démarrage *from scratch* : commencer par vérifier le clone Git local et les environnements ; ne pas supposer que le mini-PC ou une connexion distante sont prêts.
- Aucun `push --force`, rebase destructif, nettoyage irréversible, reset de travail non committé, modification de `main` ni fusion sans mandat explicite.

## Publication obligatoire des livrables de revue

- **Codex publie sur GitHub les rapports et preuves utiles de chaque mandat**, dans une branche dédiée et une PR Draft, afin que ChatGPT les consulte directement sans transfert manuel par l'utilisateur.
- Convention : `qualification/<MANDAT>/RAPPORT.md` et `qualification/<MANDAT>/evidence/` pour les preuves sélectionnées, reproductibles et expurgées. Les scripts utiles au produit restent dans leurs dossiers techniques appropriés.
- Avant toute publication, examiner les fichiers et **exclure** secrets, clés, empreintes d'hôte non nécessaires, comptes, chemins privés, adresses réseau privées, journaux sensibles et artefacts volumineux ou binaires inutiles. Conserver localement les preuves brutes non publiables et indiquer leur existence, sans exposer leur contenu.
- Rapporter l'URL de PR, la branche, le SHA publié et la liste des preuves, en distinguant résultats vérifiés, déclarés et non exécutés. Ne jamais pousser directement sur `main` ni fusionner sans arbitrage.
- Si la publication est bloquée, documenter la cause et demander une décision ; **ne pas imposer à l'utilisateur un transfert manuel de fichiers comme procédure normale**.

## Mandats orientés résultats — autonomie encadrée

- Un mandat vise **un résultat fonctionnel vérifiable**, pas une succession de micro-tâches ; Codex choisit les étapes techniques nécessaires et corrige les échecs ordinaires dans le même mandat.
- Définir un objectif principal, des critères d'acceptation observables, des limites d'autorisation et des points d'arrêt pour les opérations sensibles. Ne pas élargir le périmètre produit sans décision.
- Ne pas interrompre l'exécution pour chaque choix technique mineur ; communiquer les jalons significatifs avec le temps écoulé, risques et blocages.
- Ne solliciter l'utilisateur qu'en cas de décision structurante, modification système/permission, risque de perte de données, fusion ou blocage véritable. Préserver les opérations existantes.
- Éviter une PR par sous-étape ; regrouper les changements cohérents dans une PR Draft, sans empiler indéfiniment des PR dépendantes. Les fusions restent explicitement autorisées.
- ChatGPT fournit **tout mandat intégralement dans le chat**, sans fichier de mandat dans GitHub ; aucune revue de code automatique à chaque livraison.
