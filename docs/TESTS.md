# Tests et qualification

## Qualification locale officielle

La décision du propriétaire exclut GitHub Actions et toute CI externe. La porte
reste locale sous Windows, avec provenance Git fail-closed. Les profils fermés
sont :

| Profil | Contenu | Exclusions structurelles |
|---|---|---|
| `fast` | tests unitaires, contrats et outillage de qualification | diagnostics matériels, processus d'intégration, installation, déploiement |
| `integration` | processus, sockets, fichiers, concurrence, rollbacks simulés et assemblage système hermétique | diagnostics matériels, SSH réel, installation, déploiement |
| `software` | `fast` puis `integration` | mêmes exclusions |
| `build` | mesure d'architecture, compilation Python, référence API, syntaxe PowerShell, PositionAgent, PairingTool, MouseWitness et MSIX HOGP production + qualification non signés | exécution des scripts analysés, signature et installation |
| `full-local` | `software` puis `build` | mêmes exclusions |

Commande de référence :

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

Les sept diagnostics matériels exclus sont trois diagnostics Bluetooth et
quatre diagnostics cible/session. Ils restent hors orchestrateur et exigent une
autorisation explicite.

Une qualification officielle refuse avant toute phase un dépôt sale, une
identité Git indisponible ou un arbre non résolu. Son résumé v2 contient commit,
empreinte d'arbre, branche, propreté, compteurs de tests, skips, erreurs
attendues, durées et empreintes des artefacts. Tout skip ou échec attendu non
explicitement sorti de la porte rend le profil logiciel non favorable.

Un chemin fourni avec `--output-dir` doit être nouveau. L'orchestrateur le crée
de manière exclusive et bloque avant toute phase s'il existe déjà, même vide,
afin qu'aucun résultat périmé ou concurrent ne puisse être accepté comme preuve.

L'organisation et les responsabilités des niveaux sont détaillées dans
[`tests/README.md`](../tests/README.md).

## Mesure de qualité sans dépendance externe

Le profil `build` exécute
`scripts/qualification/measure_test_architecture.py`. Son artefact JSON associe
chaque module Python de production aux fichiers de test qui l'importent
directement, compte les cas par niveau et refuse :

- un module de production sans propriétaire de test direct ;
- un retour des boucles de micro-polling par `time.sleep` de 10 ms ou moins.

Cette mesure est une porte d'architecture, pas une couverture de lignes ou de
branches. Les appels `read_text` et les attentes temporelles restantes sont
comptés pour rendre visible la dette de contrats statiques et de tests de
deadline. L'ajout d'un outil de couverture ou de mutation reste une décision de
dépendance distincte ; aucun pourcentage n'est inventé par cette porte.

## Gouvernance sans CI externe

`main` exige une pull request, refuse force-push et suppression, impose la
résolution des conversations et un historique linéaire. Aucun statut GitHub
Actions n'est requis puisque l'option retenue exclut toute CI externe.

Le modèle `.github/PULL_REQUEST_TEMPLATE.md` exige la preuve locale : commit et
arbre propres, profil, compteurs, builds, exclusions et lien vers le rapport.
Une PR reste Draft jusqu'à publication de cette preuve. Qualification favorable
et fusion restent deux décisions différentes ; aucune fusion n'est automatique.

## Contrats de convergence architecturale

`tests/integration/test_architecture_convergence.py` vérifie notamment que :

- une commande historique ne peut pas s'insérer pendant un maintien moderne ;
- une action annulée en attente du coordinateur n'acquiert jamais le HID ;
- position et topologie sont publiées sous la même génération ;
- une génération incohérente est refusée avant publication.

`tests/integration/test_controller_release.py` construit de vrais dépôts Git temporaires et
vérifie dépôt sale refusé, extraction des seuls objets sélectionnés, réutilisation
identique, exécution autonome du vérificateur, altération et fichier inattendu
refusés. Ces tests ne créent ni tâche ni processus applicatif persistant.

## Supervision HOGP et plan de contrôle cible

`tests/unit/test_hogp_health.py` verrouille la propriété architecturale issue de
la qualification réelle : un abonné absent laisse le provider vivant ; seule
une erreur du canal moteur autorise une reprise, avec temporisation observable.

`tests/unit/test_hogp_control.py` vérifie la liaison aux identités enrôlées, la
génération du provider, l'unicité et l'expiration des commandes, les
acquittements, l'absence de commande sans élévation et le refus fail-closed si
le statut transport est indisponible. La grâce et le cooldown suivent une
horloge monotone ; `not_required` prouve qu'une reprise devenue inutile n'est
ni exécutée ni rejouée. L'écho d'un acquittement survit à la rotation ou au
redémarrage backend ; un acquittement sans correspondance ne supprime jamais
une autre commande et peut être confirmé avant sa livraison dans la même
réponse. Un scénario distinct vérifie que l'expiration simultanée d'une autre
commande ne remplace pas cet écho, tout en restant observable au cycle suivant.
Le test système traverse réellement
`POST /v1/hogp-control` avec TLS remplacé par un serveur hermétique, HMAC et
anti-rejeu inchangés.
Il prouve aussi l'exclusion croisée des clés entre télémétrie/capture et plan de
contrôle afin qu'un runtime de contrôle ne puisse jamais falsifier une position.
Un secret réutilisé sous deux identifiants est refusé avant création du transport.
Une identité de contrôle reste exclue lorsque le plan est désactivé. Le mode
`position-only` exclut lui aussi la clé de contrôle et les tests observent
l'effacement des secrets lorsque la composition échoue ou que le serveur ferme.

`tests/contract/test_hogp_control_agent_contract.py` interdit au runtime cible
les API GATT, de pairage et d'injection, exige les quatre empreintes PnP/AEP,
le binaire `pnputil` système exact et une tâche distincte `RunLevel=Highest`.
Il impose aussi une énumération AEP limitée par le sélecteur Windows des seuls
périphériques BLE appairés, bornée à 30 secondes. Cette contrainte couvre la
régression matérielle où l'énumération BLE générale dépassait dix secondes sur
`DESKTOP-NPIHO8K` ; le sélecteur ne crée aucun client BLE ou GATT.
Le profil `build` compile ce runtime séparément ; aucun test logiciel ne lance
de commande PnP ou Bluetooth réelle.
Le contrat exige aussi l'inspection d'identités sans identifiant brut, l'état
atomique anti-rejeu, le verrou mono-instance, l'installation sous répertoires
protégés, les empreintes attendues et l'absence de binaire élevé sous
`LOCALAPPDATA`. Le rôle matériel `USB`/`PCI`, le déclencheur `AtLogOn`, le SID,
le type `Interactive`, le répertoire de travail, l'écho exact des acquittements
et l'absence de droit de mutation ACL pour tout principal inattendu sont
verrouillés. Le contrat interdit les masques ACL agrégés qui classeraient
`ReadAndExecute` comme écriture. Les tests
unitaires font tourner la génération après reprise du
provider, traitent l'absence du statut `advertising` comme une rupture du canal
et distinguent `advertising=False` de la simple absence d'abonné. Un statut de
transport absent ou non structuré ferme aussi le plan de reprise.
Les tests suspendent une commande déjà en attente pendant un statut invalide ou
`advertising=False`, puis vérifient la reprise du même identifiant seulement
après retour à un statut sain.
Une course avec l'arrêt ne fait ni tourner la génération provider ni publier
une reprise fictive : la rotation traverse une section critique commune à
l'arrêt du processus et à l'intention d'arrêt du contrôleur. Un compteur
d'époque garantit également qu'une intention d'arrêt publiée pendant
`transport.start()` gagne avant l'activation du contrôleur.

## Assemblage système hermétique

`tests/system/test_runtime_composition.py` construit le même graphe d'objets que
le runtime de production via `build_runtime`. Il démarre les vrais serveurs de
position, commande et événements sur des ports éphémères, puis vérifie :

- l'acceptation d'une position signée et sa lecture par la commande locale ;
- le refus d'une commande sans jeton ;
- la soumission d'une action sans effet HID et ses transitions WebSocket ;
- la fermeture de toutes les ressources et l'absence de rapport souris.

Seules les frontières matérielles (DPAPI, TLS déjà couvert en intégration et
transport HOGP) sont remplacées. Les attentes asynchrones partagées utilisent
`tests/support/waiting.py`, avec échéance et diagnostic explicites.

## Dernières qualifications du programme

| Lot | SHA de branche qualifié | Résultat déclaré par Codex | Revue ChatGPT |
|---|---|---|---|
| R0 | `1b00b067…` | 206/206 PASS | revue statique favorable avec réserves ; tests non réexécutés |
| R1 | `64aa1bec…` | 222/222 PASS après correctif | correctif relu, tests non réexécutés |
| R2 | `4601bb6d…` | 242/242 PASS après correctifs | B1/B2 relus, tests non réexécutés |
| R3 | `5955889c…` | 263/263 PASS après correctifs | B1/B2/B3 relus, tests non réexécutés |
| R4 | `cf5f7731…` | 269/269 PASS, `full-local` final | commentaire de qualification final ; revue statique distincte |
| R5 | `8c15c82f…` | 271/271 PASS, `full-local` final | C-13/C-14 relus ; qualification finale commentée séparément |
| PR #26 précision | `aa53504a…` | 301/301 PASS, 175,531 s | correction logicielle publiée, matériel encore distinct à ce SHA |
| MC-FINAL-VALIDATION-001 | commit portant le rapport | 302/302 PASS lors de la consolidation, 125,109 s | matériel réel, récupération et preuves expurgées documentés séparément |

Les détails, durées, artefacts et exclusions sont dans les rapports R0–R5 et
les commentaires des PR #13–#18. La matrice des défauts est dans
[ROBUSTESSE.md](ROBUSTESSE.md).

## Portée des preuves

- `CORRIGÉ_LOGICIEL` signifie que le correctif est fusionné et couvert par des
  tests locaux/simulés.
- `QUALIFIÉ_LOCAL` signifie qu'un profil local Windows a réussi au SHA indiqué.
- Une revue ChatGPT vérifie le diff et les preuves ; sauf mention contraire,
  elle ne réexécute pas les commandes Windows de Codex.
- Aucune de ces mentions ne vaut qualification matérielle post-R1–R5,
  synchronisation des machines ou déploiement.

### Porte de reconnexion HOGP native

La qualification courante interdit tout moniteur GATT persistant sur la cible.
Après le diagnostic ponctuel de la paire, toutes ses références sont libérées et
les preuves de reprise proviennent du pilote HID Windows et du fournisseur
backend : retour de l'unique abonné autorisé, session active, boutons à zéro et
absence de nouveau consentement. Les cas obligatoires sont le redémarrage du
provider, le cycle radio cible, le redémarrage cible et la mise à jour du runtime
à identité/descripteur inchangés. Un succès obtenu seulement pendant l'exécution
de `PairingTool Connect` ne qualifie pas la reconnexion native.

## Preuves matérielles historiques

MC-HID-EXEC-001 et MC-MOUSE-ACTIONS-001 ont qualifié antérieurement, dans leurs
périmètres et avant R1–R5, l'appairage HOGP, le HID natif, le retour de position,
les actions souris, les captures autorisées, l'arrêt et la reconnexion. Leurs
rapports restent les sources historiques ; les réserves LAN/GATT, roulette
horizontale et consentement opérationnel demeurent.

Le rapport [MC-FINAL-VALIDATION-001](../qualification/MC-FINAL-VALIDATION-001/RAPPORT.md)
distingue les preuves matérielles des scénarios simulés. Il conserve le premier
`MATERIAL_FAIL`, puis documente les déplacements confirmés exacts, les actions
souris, une capture avant/après supprimée après empreinte, l'arrêt d'urgence,
le redémarrage et le refus de rejeu. Le test de l'exporteur exécute réellement
Windows PowerShell et compare son SHA-256 au calcul Python.

## Compte rendu obligatoire

Chaque qualification indique SHA, machine, commandes, nombre de tests, durée,
builds, exclusions, effets matériels éventuels et réserves. Ne publier aucun
secret, identifiant matériel, adresse privée ou chemin personnel.
