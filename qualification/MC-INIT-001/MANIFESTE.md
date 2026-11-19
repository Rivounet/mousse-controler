# Manifeste de publication — MC-INIT-001

Les originaux restent inchangés dans le répertoire local `qualification` extérieur au clone. Aucun fichier brut n’est remplacé. Les noms ci-dessous identifient leur origine sans exposer le chemin privé. Les extractions JSON utilisent une liste de champs autorisés ; les valeurs retenues ne sont pas des résultats de nouveaux diagnostics. Les métadonnées techniques publiées (OS, versions, modèle CPU, RAM, disque, VID/PID génériques et état BLE) sont nécessaires à la revue.

## Fichiers publiés

| Fichier | Origine | SHA-256 du fichier publié |
|---|---|---|
| `evidence/windows-inventory.json` | windows-inventory.txt | `0d1dd4fe7fdee2e20864b885e9af2381db71f24a7081e98970a143e007f6ee9e` |
| `evidence/mini-pc-inventory.json` | mini-pc-inventory.txt | `1702dd55db1c4bb0cdf949d8a5f4ee5012993bd694580d91b8d527933b9316fb` |
| `evidence/windows-bluetooth-capability.txt` | windows-bluetooth-capability.txt | `61e3761eb02efcdc09cb15ddc6f8cebfa52bec68aadead0157aebb5b7d6ffe7d` |
| `evidence/mini-pc-bluetooth-capability.txt` | mini-pc-bluetooth-capability.txt | `61e3761eb02efcdc09cb15ddc6f8cebfa52bec68aadead0157aebb5b7d6ffe7d` |
| `evidence/Read-BluetoothCapability.ps1` | Read-BluetoothCapability.ps1 | `09307feb54ac67b233e4456101d233f2a3d69254f7024ee579f93406b8d511f4` |
| `evidence/git-final.txt` | git-final.txt | `57992e38994b3a4dec1cb32c81817d63535d887c316ab7855c556cab14fa39f2` |
| `evidence/remote-access.txt` | remote-access-checks.txt + sftp-readonly.txt | `13ebb72a938e74b26a91c6faa94b9955812b873cf98913282bf4cebe8fd49192` |
| `RAPPORT.md` | MC-INIT-001-RAPPORT.txt (édition expurgée et contextualisée) | `a9532966d5c634808eedf4a39535994a44fb149f7bfff67b8c5e2d4aaa4a6f7e` |
| `evidence/git-publication.txt` | sorties locales observées pendant MC-INIT-001-PUBLICATION ; transcription sélectionnée | `a4ad532ad6e577d06b0d3f0afed55e1eb8157a31613d99a5c551248a51d96bb1` |
| `MANIFESTE.md` | Créé pour cette publication | Non auto-haché ; couvert par le commit Git |

## Suppressions et transformations

- Inventaires : seuls Time, OS, Hardware, Shell, Versions, Storage, noms des outils, contrôleur Realtek (VID/PID sans instance unique), pilotes, descriptions/interfaces réseau et services distants sélectionnés sont retenus. Les tableaux de services contiennent des valeurs numériques conservées, expliquées dans SelectionNote. Shell contient successivement PSVersionTable, Is64BitProcess et IsInRole(Administrator) ; le dernier booléen est false en local et true en distant.
- Supprimés : comptes personnels, chemins privés/absolus, SID et ACL détaillées, identifiants d’instance uniques Bluetooth, appareils personnels mémorisés, adresses réseau, ports applicatifs, PIDs, chemins/processus de projets tiers, inventaire des clones et listing du profil utilisateur.
- Accès : empreintes de clés publiques, identités de compte et détails de session expurgés ; espaces de fin de ligne retirés. Le succès de listing est conservé sans son contenu. La politique PowerShell et le shell par défaut restent lisibles. La configuration SSH détaillée et la correspondance d’identité restent des constats du rapport initial, pas des sorties brutes publiées.
- Rapport : même conclusion et réserves, titres Markdown, métadonnées privées remplacées par des marqueurs et note séparant la situation Git historique de celle de publication. Références de preuves adaptées. Pas de modification des documents officiels.
- Deux résultats WinRT et le script de lecture de capacités : contenu textuel conservé, normalisation UTF-8 et fin de fichier. Le script ne contient aucun identifiant matériel/personnel et ne démarre aucune publicité ni service GATT.
- git-final.txt : contenu historique conservé, fins de fichier normalisées. git-publication.txt est une transcription explicitement identifiée, distincte de ce journal historique.

## Originaux conservés seulement en local

| Original | Traitement |
|---|---|
| MC-INIT-001-RAPPORT.txt | Original intégral local ; édition expurgée RAPPORT.md publiée |
| windows-inventory.txt | Brut intégral local ; extrait JSON publié |
| mini-pc-inventory.txt | Brut intégral local ; extrait JSON publié |
| remote-access-checks.txt | Brut intégral local ; extrait combiné expurgé publié |
| sftp-readonly.txt | Listing personnel intégral local ; seules commandes et réussite retenues |
| Inventory-ReadOnly.ps1 | Local uniquement : collecte large de chemins, comptes, périphériques et projets tiers ; aucune nouvelle exécution |
| Read-BluetoothCapability.ps1 | Original local conservé ; copie textuelle publiée |
| windows-bluetooth-capability.txt | Original local conservé ; copie textuelle publiée |
| mini-pc-bluetooth-capability.txt | Original local conservé ; copie textuelle publiée |
| git-final.txt | Original local conservé ; copie textuelle historique publiée |

L’outil local de préparation, les empreintes de contrôle des originaux et les fichiers de travail de publication restent hors dépôt. Aucun secret, jeton, mot de passe ou clé privée n’a été sélectionné.

## Contrôles avant publication

Relecture des extraits et du diff, contrôle par expressions régulières des formats de secrets et des métadonnées exclues, vérification des liens locaux et des empreintes de ce manifeste, contrôle que le diff ne contient que qualification/MC-INIT-001. Comparaison des SHA-256 des dix originaux avant/après préparation. Ces contrôles sont ciblés et ne constituent pas une certification exhaustive de confidentialité.

## Limites de preuve

Constats historiques, non réexécutés pendant cette publication. Les extractions permettent de vérifier les valeurs retenues et le code WinRT ; les sorties exclues ne sont pas auditables depuis GitHub. SSH/consultation SFTP qualifiés, transfert aller-retour et déploiement non testés ; rôle périphérique annoncé favorable, HID non démontré. J1 reste ouvert. Aucune nouvelle opération sur mini-pc-backend ; MC-INIT-002 non commencé.
