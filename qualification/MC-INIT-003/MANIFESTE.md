# Manifeste de publication MC-INIT-003

Octets UTF-8/LF. Le manifeste est couvert par Git et ne s’auto-hache pas. Diff propre au mandat, relatif à la tête de la PR #2, pas à main. Aucun original local supprimé.

| Fichier | Origine | SHA-256 |
|---|---|---|
| `.gitattributes` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `a79691a93b46e49ce460c26ef22afcc03d6eca1e63bf2edbc20e96159510f6c9` |
| `RAPPORT.md` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `8c10671b610d8b3f564f277b07e79d7b863eceaeb1e418a01c0551cb40770a93` |
| `PROTOCOLE-LANCEMENT.md` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `6d98cd561bf59081604b9a255fb6d99cdcdcf8495fa4a4ffed0e6166b53080fe` |
| `evidence/demo-local.json` | Démonstration locale réelle à partir des commits explicitement identifiés ; aucun contact distant | `6bb0373c4213da3e6ed4dfc9cedc81cf2f8f4b9a5d5b17e1e7436c915fdf19b7` |
| `evidence/artifact-manifest.json` | Démonstration locale réelle à partir des commits explicitement identifiés ; aucun contact distant | `d9723067d434b9502b8e8ccfa203927b2491c7ce99434effe2abaa90902ca999` |
| `evidence/dry-run.json` | dry-run-raw.json ; seul le chemin réel de destination est remplacé | `e04d5243fde3b3f75601346f13686d551bf365a1f99732903b79eb9b945a8373` |
| `evidence/tests-local.txt` | Dernier passage unittest sur le commit technique ; sortie réussie sans chemin privé | `e0130c73f5bec1b9d09f83f13b7204c8640a6012be48caac4a7051137d14a2bc` |
| `evidence/demo-events.jsonl` | Journal réel du modèle local de releases ; identifiants d’opération et de releases, aucun PID Windows ni compte | `bc211c0d684f67bc224b7c2c35a8a483f8445fab66492e7c95bad18d79d456f0` |
| `evidence/tests-history.json` | Synthèse fidèle des quatre sorties locales ; traces brutes initiales exclues | `4d5c178050dd38277d1480e360499a7d43f422ac48259c91d84fc8b68d25115d` |
| `evidence/git.json` | Sorties Git observées et métadonnées du connecteur GitHub ; transcription sélectionnée, sans identité personnelle | `603b43924a3080bd388cb1370756bdc44bfb09bcace19ad262448f57c66b9377` |
| `../../scripts/remote/artifacts.py` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `45dc2218b5aa8a0ca5671f44df68de545f7392aa90ed910051d6989b763a11a1` |
| `../../scripts/remote/releases.py` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `97f7ec21f355a5f218bd06819fd18afd6eb0033bcfd8380df4d362bc29ff6dd2` |
| `../../scripts/remote/deployment.py` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `ca880af85082612350a982e0d81757116db166ca10d86731587d520ffaa1ba65` |
| `../../scripts/remote/test_deployment.py` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `3c464083bc3895468058fb0a9511682374764d1b23779b0cede444d294c58312` |
| `../../scripts/remote/DEPLOYMENT.md` | Développement/rédaction MC-INIT-003 ; aucun mandat copié ni document officiel édité | `46b534d4bc47f629bda00ae136e36fb476def6112a3e6cd9018eb913cd5e812b` |
| `MANIFESTE.md` | Rédaction de publication | Couvert par Git |

## Sélection et exclusions

- Nouveaux scripts techniques et tests : préparateur d’artefacts, modèle de release, CLI local et tests, guide technique. Aucun fichier source de MC-INIT-002 modifié. Les PID du modèle et les répertoires synthétiques des tests ne sont pas des coordonnées du mini-PC.
- Rapport et protocole : résultats locaux, comparaison des méthodes Windows et expérience future ; pas une copie du mandat ni une autorisation d’exécution. Aucun fichier de mandat ajouté.
- Sortie finale de tests : texte original normalisé UTF-8/LF. Les traces des échecs initiaux sont conservées localement et seulement résumées car leurs chemins ne sont pas publiables.
- Exemple d’artefact : manifeste et hash seulement. Les ZIP binaires, bundles A/B, releases extraites, snapshot d’état et modèle de runtime sont conservés uniquement en local. Le journal publié décrit des opérations locales de simulation et ne contient aucun PID réel.
- Dry-run : chemin de destination réelle remplacé par un marqueur ; aucune modification des SHA, hashes, sélection ou états de non-exécution distante.
- État Git/PR : transcription des valeurs observées, distinction de main et de la base dépendante. Le SHA final est celui de la tête de PR, différent du commit technique réellement préparé comme artefact.
- Configurations réelles, protocole exact d’un éventuel futur essai avec chemins privés, comptes, adresses, clés/empreintes d’hôte et fichiers de travail restent hors dépôt. Aucun accord antérieur MC-INIT-002 n’est réutilisé.
- Les originaux et publications MC-INIT-001/002 restent inchangés. Les documents hérités appartiennent à la base PR #2 ; leur présence ne représente aucune nouvelle publication du mandat MC-INIT-003 ni fusion dans main.

## Contrôles de publication

Relecture du diff propre au mandat, contrôle des formats de secrets et métadonnées privées dans les nouveaux fichiers, vérification des empreintes et des liens locaux, contrôle du périmètre scripts/remote et qualification/MC-INIT-003. Détection ciblée, sans certification exhaustive de confidentialité. Fichiers synthétiques de test et chaînes d’exemple de marqueurs de clés conservés pour tester les refus ; aucune clé privée réelle ni jeton sélectionné.

## Limites d’intégrité et de qualification

Les hashes vérifient les octets publiés ; ils ne remplacent pas l’authentification de l’auteur. L’artefact démontré référence le commit technique réel et ses fichiers Git, pas une release distante. 69 tests locaux PASS, dont 31 hérités inchangés ; les échecs initiaux et leur correction restent visibles dans l’historique expurgé.

Aucune nouvelle opération sur mini-pc-backend. Transfert de release, démarrage Windows autonome, santé/stop/rollback applicatifs distants, endurance, panne électrique et Bluetooth HID : NON_EXÉCUTÉS. La comparaison de PR reste dépendante de PR #2 tant que son intégration n’est pas décidée séparément. Aucune fusion ni force-push.
