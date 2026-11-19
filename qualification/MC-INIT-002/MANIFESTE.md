# Manifeste — MC-INIT-002

Fichiers publiés, origine et empreinte SHA-256 des octets UTF-8/LF. Le manifeste est couvert par le commit Git et ne s’auto-hache pas. Les marqueurs remplacent les chemins réels ; ils ne sont pas exécutables.

| Fichier | Origine | SHA-256 |
|---|---|---|
| `evidence/ssh-readonly.json` | readonly-raw.json : liste de champs sélectionnés ; sortie SFTP personnelle exclue | `01dd65efb92c21476968b10f2ce5d208970ddb320de053ab6e14f20e4bd88d21` |
| `evidence/witness-roundtrip.json` | authorized-raw.json, bounded-process-failed-raw.json, bounded-process-output-check-raw.json, bounded-process-raw.json et final-state-raw.json ; extraction, reclassement explicite, métadonnées de processus/compte/chemins exclues | `346bbd7c45b194081bdc8cf9ffc0d75ea3c5136df94af950ddc80a46c37d9e10` |
| `evidence/tests-local.txt` | Dernière exécution unittest locale ; aucun chemin privé dans la sortie réussie | `87b37c93698109819d6f5806b8ea09e0d909f6f276cf3614ef884ab4e1166d14` |
| `evidence/sync-dry-run.json` | sync-plan-raw.json ; racine réelle remplacée ; ce plan cible le commit de base des scripts avant correction du processus | `b9121955dfedac16035c82ac715dbd3f42a8295bbfa5a4b6d5de5fef4f4057f7` |
| `evidence/commandes-temoin.md` | plan.local.json et bounded-process-command.local.ps1 : chemins locaux/distants et token remplacés ; attente encodée remplacée par sa description | `eeee207fc0decbe0d0709933e838a05ee41a7446e5921fd1c77b535818cfd12e` |
| `evidence/git.json` | Sorties Git observées et métadonnées de PR #1 obtenues via le connecteur GitHub ; transcription sélectionnée | `8b4d79a632ab54bfcfcd2e82157b57669af20329ea1d38a345535305f51623c4` |
| `RAPPORT.md` | Rédaction MC-INIT-002 fondée sur les sorties de ce mandat ; aucune édition du référentiel officiel | `86ced0d16f4ffffc6321b2b2a37ba7898c144dc3275369c4f2192202255f4477` |
| `../../scripts/remote/.gitattributes` | Développé localement durant MC-INIT-002 ; pas de secret/configuration réelle | `a79691a93b46e49ce460c26ef22afcc03d6eca1e63bf2edbc20e96159510f6c9` |
| `../../scripts/remote/plan_witness.py` | Développé localement durant MC-INIT-002 ; pas de secret/configuration réelle | `2023af1f1543b83378581f1dad5db1610893821a456aa9e0e98aa9976d2c3753` |
| `../../scripts/remote/README.md` | Développé localement durant MC-INIT-002 ; pas de secret/configuration réelle | `6f0a789890f02d4e8c1b1954b62035c911ba9d43383812ca9b0172679ee280fa` |
| `../../scripts/remote/remote.py` | Développé localement durant MC-INIT-002 ; pas de secret/configuration réelle | `bf8028e514b132e796fbae06e9f7d4aadeea967016a9e619494129a3aaaa2615` |
| `../../scripts/remote/test_remote.py` | Développé localement durant MC-INIT-002 ; pas de secret/configuration réelle | `397712ba6b1157434bc055fb91aa226ce742c03e23dedc30ac2df5d3379ae01b` |
| `.gitattributes` | Normalisation LF limitée à ce lot | `a79691a93b46e49ce460c26ef22afcc03d6eca1e63bf2edbc20e96159510f6c9` |
| `MANIFESTE.md` | Rédigé pour la publication | Couvert par Git |

## Exclusions et conservation locale

Tous les originaux MC-INIT-001 restent inchangés hors clone. Pour MC-INIT-002, configuration SSH/JSON, protocole d’autorisation exact, plan avec chemins réels, témoin initial et téléchargé, scripts d’orchestration, fichiers de travail de publication et contrôles bruts restent locaux. Aucune preuve brute n’a été supprimée ; les deux sorties intermédiaires du processus ont des fichiers distincts.

- readonly-raw.json : sélection des valeurs diagnostiques et flux Unicode fixes ; chemin du profil SFTP supprimé, nom réel ramené à l’alias du projet. Aucun compte ou empreinte d’hôte publié.
- authorized-raw.json : chemins, ACL détaillées, PID, dates et commande complète du processus exclus. Les données de transfert et hash du témoin non secret restent publiées. Son outcome global initial est contextualisé : ALREADY_EXITED ne prouvait pas un stop contrôlé.
- bounded-process-failed-raw.json et bounded-process-output-check-raw.json : erreurs et correction résumées dans witness-roundtrip.json ; textes CLIXML détaillés et métadonnées inutiles gardés locaux.
- bounded-process-raw.json et final-state-raw.json : flux fixes et états booléens sélectionnés ; dernier résultat du stop et absence des processus témoins conservés.
- sync-plan-raw.json : seul le chemin cible est remplacé. Le SHA désigne bien le commit auquel ce plan local a été appliqué ; pas une révision exécutée sur mini-PC.
- plan.local.json et bounded-process-command.local.ps1 : commandes sélectionnées dans commandes-temoin.md ; chemins et identifiant du témoin remplacés, attente encodée décrite en clair. Le générateur versionné fournit le code reproductible.
- tests-local.txt : sortie réussie publiée ; mocks hors réseau et vrai sous-processus local borné. Pas de journal matériel privé.
- Identité/accord utilisateur : le périmètre et l’accord sont attestés dans le rapport, pas la conversation complète ni le compte personnel.

## Confidentialité et intégrité

Relecture du diff et recherche ciblée de formats de jetons, clés privées, mots de passe, empreintes SSH, SID, adresses réseau, comptes, chemins personnels et identifiants matériels uniques avant push. Les chemins synthétiques des tests et le nom de l’alias déjà public du projet ne sont pas des coordonnées personnelles. Aucune configuration réelle ni sortie personnelle brute dans l’index.

Contrôle des liens locaux, hashes de ce manifeste et périmètre de diff limité à scripts/remote et qualification/MC-INIT-002. Les contrôles ciblés ne constituent pas une certification exhaustive. Les hashes portent sur les fichiers publiés, pas sur l’intégralité des originaux expurgés.

## Résultat et réserves

PASS : 31 tests locaux, sondes SSH/SFTP, flux UTF-8 et code 37, timeout attendu, transfert/hash/retour du témoin autorisé, refus de réutilisation du dossier, nettoyage limité, arrêt contrôlé en une session SSH, absence finale des processus témoins et de la racine créée. Les échecs intermédiaires sont conservés explicitement.

NON_EXÉCUTÉ : déploiement/rollback applicatifs, synchro d’une copie distante par SHA, santé applicative, gestion complète des déploiements concurrents, persistance après déconnexion SSH et HID. Les documents officiels et PR #1 restent inchangés ; aucune fusion.
