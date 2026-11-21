# MC-FINAL-VALIDATION-001 — Rapport consolidé

## Verdict

**`FULL_VALIDATION_PASS`**

La validation porte sur le commit qui contient ce rapport dans la PR #26. Le
SHA exact et le résultat `full-local` final sont publiés dans le commentaire de
qualification de la PR, à partir du `summary.json` produit sur ce commit.

Le premier `MATERIAL_FAIL` reste inchangé : il démontrait qu'une unité HID
brute n'est pas un pixel. La présente validation qualifie le contrat corrigé en
pixels et ne réécrit pas ce résultat historique.

## Versions et déploiement

| Composant | Version ou empreinte vérifiée | État |
|---|---|---|
| Contrôleur candidat | PR #26, base logicielle `aa53504a5c786f7d74727a28782b88b06b45dc95`, puis commit de clôture | tâche active, rollback vers `fc88e330…` prêt |
| HOGP MSIX | 1.0.0.3, SHA-256 `94770EE3981FE84D9712A281D79F2B69341C4B041BD97F7055F9D78DA784A3F2` | installé, signature Windows valide |
| PositionAgent installé | SHA-256 `F9D5E982592398E279FF64A817A2E9067C9D7CB7F4872DB67A583BE6ADD7E4FA` | une instance dans la session interactive, télémétrie fraîche |
| PositionAgent rollback | SHA-256 `0562CC27694964406311C62E963B5F1BA6913B49EE2A3D6B0605F9088FEDF73F` | disponible |

La sauvegarde pré-déploiement couvre configuration, journal et `.ids`, index et
captures ainsi que la tâche. Son manifeste local porte l'empreinte
`6AC88E3AB6E700DF32D5C1AEEF18BE23567C2B03FACB66610DABBFF8ABF72019`.
Aucun secret, chemin privé ou compte n'est publié.

## Résultats vérifiés

| Domaine | Résultat réel |
|---|---|
| Précision confirmée | aller/retour horizontal de 10 px exact ; aller/retour vertical de 10 px exact ; déplacements moyens, absolus et retour exacts |
| Tolérance et bornes | erreur observée 1,414 px acceptée avec tolérance 2 ; limite cumulée 1 refusée par `POSITION_MOVEMENT_LIMIT` sans émission |
| HID brut | un rapport demandé à -10 a produit -7 px après stabilisation ; aucune assimilation HID/pixel |
| Trajectoire | séquence courbe terminée, puis retour exact |
| Actions souris | clic gauche simple/double/triple, droit, central, arrière/avant, combinaison, maintien/libération, glisser-déposer et roulette verticale exécutés |
| Séquences | temporisation et composition exécutées ; arrêt pendant attente annulé avant le clic |
| États et événements | transitions `ACCEPTED/RUNNING/EXECUTED/CONFIRMED`, identifiants d'événements uniques et corrélés |
| API | requête sans jeton rejetée HTTP 401 ; API authentifiée opérationnelle |
| PositionAgent | session et topologie stables pendant les actions, positions fraîches, reconnexion après redémarrage |
| Captures | avant/après liées à l'action ; capture après action 283 093 octets, SHA-256 `939B8DBFFC0059D65BDC01767E17D7AF2B0017D7169FC9762B269EDA8A5CEAF5`, puis état `DELETED` et fichier absent |
| Arrêt d'urgence | séquence annulée `CANCELLED` avant clic ; boutons à zéro ; aucune action active |
| Récupération | tâche redémarrée sur le candidat, HOGP réabonné, télémétrie fraîche ; ancien identifiant refusé `duplicate action id` après redémarrage |

Les positions absolues et la capture brute ne sont pas publiées. L'export
recadré a révélé l'absence de `Get-FileHash` dans le contexte Windows PowerShell
utilisé. L'exporteur calcule désormais SHA-256 via .NET ; un test exécute le
script et compare l'empreinte réelle. La source brute résiduelle a été supprimée.

## Qualification logicielle

La préqualification de consolidation a produit `PASS`, 302/302 tests, en
125,109 s : compilation Python, référence API, analyse syntaxique de 28 scripts
PowerShell et build PositionAgent réussis. Les sept diagnostics matériels de
l'orchestrateur restent structurellement exclus ; les essais matériels sont
documentés séparément ci-dessus. Le commentaire final de la PR porte les
mesures du second `full-local` exécuté sur le SHA publié.

Les scénarios simulés complètent la preuve réelle pour les défauts qui ne sont
pas provoqués sur une session interactive : retour absent/périmé, stagnation,
oscillation, absence de progrès, émission incertaine sans rejeu, quotas et
expiration de captures, échec de suppression et récupération après interruption.

## Robustesse, limites et rollback

L'arrêt global a annulé l'action avant tout clic et remis les boutons logiques à
zéro. Le moteur HOGP n'a pas acquitté son arrêt protocolaire avant la deadline ;
la commande a donc signalé cette erreur bornée. Le runtime n'a pas été réutilisé
et la procédure qualifiée a rétabli un état sain. Ce diagnostic est conservé,
mais ne constitue pas un défaut bloquant de sûreté ou de récupération.

Le rollback arrête le candidat, repointe la tâche vers le worktree
`fc88e330923037de1345b0c2f975739c0b261380`, redémarre puis contrôle tâche,
processus, ports, télémétrie, abonnement HOGP, boutons et actions actives. Il ne
modifie ni MSIX, ni certificat, ni appairage, ni PositionAgent.

La PR #26 reste Draft, ouverte et non fusionnée. Toute nouvelle manipulation
matérielle requiert un nouveau consentement immédiat.
