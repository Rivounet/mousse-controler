# État officiel du programme de robustesse R0–R6

**Base de fusion auditée :** `origin/main` après la PR #26, commit de fusion
`5ed7045823a0d7b8c7c6418ca5586008e35ba2d2`, le 27 novembre 2026. Les travaux
de convergence sont livrés et qualifiés par la PR #27.

Ce document est la source unique pour l'état des constats C-01 à C-17. Les
rapports R0–R5 et les audits originaux restent des preuves historiques et ne
sont pas réécrits.

## Lots fusionnés

| Lot | PR | Commit de fusion | Portée |
|---|---:|---|---|
| R0 | [#13](https://github.com/Rivounet/mousse-controler/pull/13) | `d8b412f8620ba85de1b9e864af2f11ed31271006` | baseline et caractérisations |
| R1 | [#14](https://github.com/Rivounet/mousse-controler/pull/14) | `5b158a68325154be0621fd8764fb3d09b6d2e398` | sûreté actions et arrêt |
| R2 | [#15](https://github.com/Rivounet/mousse-controler/pull/15) | `a938b7455638c71846a20f7c4dc6c6c1f887e6e6` | transport HOGP et serveur LAN |
| R3 | [#16](https://github.com/Rivounet/mousse-controler/pull/16) | `54c24aa197e2075709b71311fa7e5c1b621077a0` | quotas, ressources et récupération |
| R4 | [#17](https://github.com/Rivounet/mousse-controler/pull/17) | `c5d8ef6bdb06b0fb6295b946d0be578956e35d93` | qualification locale et builds |
| R5 ciblé | [#18](https://github.com/Rivounet/mousse-controler/pull/18) | `0817823eb2e7a5e8d477ed3e382ef128611fd5b9` | C-13/C-14 ; analyse des travaux différés |

La PR [#11](https://github.com/Rivounet/mousse-controler/pull/11) d'audit
indépendant reste **ouverte, Draft et non fusionnée**. La PR #12 de
consolidation des audits est fusionnée. Une présence de contenu ailleurs ne
change pas le statut propre de la PR #11.

## Sens des statuts

- `CORRIGÉ_LOGICIEL` : correctif fusionné, couvert localement/simulé ; aucune
  qualification matérielle implicite.
- `QUALIFIÉ_LOCAL` : vérification locale Windows réussie au SHA indiqué.
- `MATÉRIEL_NON_REQUALIFIÉ` : réserve de qualification, jamais un succès déduit.
- `DIFFÉRÉ` : étudié mais volontairement non réalisé.
- `DOCUMENTÉ` : état clarifié sans changement applicatif.
- `À_VÉRIFIER` : état externe ou opérationnel non observé pendant R6.
- `CORRIGÉ_SUR_BRANCHE` : correctif implémenté et testé sur la branche de
  convergence, sans fusion ni activation implicite.

## Matrice C-01 à C-17

| ID | Description synthétique | Priorité initiale | Lot | Statut actuel | PR et preuve | Réserve restante | Prochaine action éventuelle |
|---|---|---|---|---|---|---|---|
| C-01 | attente HOGP, stderr et arrêt non bornés | P1 | R2 | `CORRIGÉ_LOGICIEL` | PR #15 ; tests processus muet/partiel/mort | `MATÉRIEL_NON_REQUALIFIÉ` ; annulation WinRT best-effort | requalifier seulement sur mandat matériel |
| C-02 | bouton incertain pouvait poursuivre l'exécution | P1 | R1 | `CORRIGÉ_LOGICIEL` | PR #14 ; états `UNKNOWN`, quarantaine et non-rejeu | libération physique non prouvable après rupture transport | conserver arrêt/récupération explicites |
| C-03 | quota capture admis trop tard | P1 | R3 | `CORRIGÉ_LOGICIEL` | PR #16 ; pic instrumenté, temporaires/index/orphelins | quota non atomique entre processus indépendants | aucun travail sans besoin multi-processus démontré |
| C-04 | serveur LAN sans bornes effectives | P1 préventif | R2 | `CORRIGÉ_LOGICIEL` | PR #15 ; TLS loopback, clients muets/trickle | Schannel et réseau réels non requalifiés | requalifier seulement sur mandat matériel |
| C-05 | arrêt global incomplet du séquenceur historique | P1/P2 | R1 | `CORRIGÉ_LOGICIEL` | PR #14 ; MOVING/WAITING/PAUSED | `MATÉRIEL_NON_REQUALIFIÉ` | aucune |
| C-06 | fermeture de l'exécuteur laissait des actions acceptées | P2 | R1 | `CORRIGÉ_LOGICIEL` | PR #14 ; drainage/annulation durable | `MATÉRIEL_NON_REQUALIFIÉ` | aucune |
| C-07 | ressources serveur orphelines après démarrage partiel | P2 | R3 | `CORRIGÉ_LOGICIEL` | PR #16 ; pile inverse best-effort et erreurs agrégées | threads Python bloqués non tuables sûrement | surveiller en exploitation |
| C-08 | mise à jour agent sans récupération sûre | P2 | R3 | `CORRIGÉ_LOGICIEL` | PR #16 ; rollback borné et `RECOVERY_REQUIRED` | tâches/ACL/disque réels non requalifiés ; récupération limitée | mandat opérationnel distinct si déploiement |
| C-09 | sources C++ HOGP historiques parallèles | P2 | R5 | `DIFFÉRÉ` | PR #18 ; inventaire HOGP | absence totale d'usage manuel non démontrée | reprendre seulement avec preuve d'inutilité |
| C-10 | tests de panne et séparation matériel insuffisants | P2 | R4 | `QUALIFIÉ_LOCAL` | PR #17 ; `full-local` 269/269 final | 7 diagnostics matériels exclus ; aucune CI externe | conserver profils locaux fermés |
| C-11 | deux séquenceurs pouvaient émettre par des voies concurrentes | P3, réévaluée P1 | convergence | `QUALIFIÉ_LOCAL` | PR #27 ; test maintien moderne + déplacement historique ; bail exclusif partagé | deux modèles d'état restent publics pour compatibilité | aucune sans rupture de contrat explicitement décidée |
| C-12 | responsabilités concentrées dans deux gros composants | P3 | convergence | `QUALIFIÉ_LOCAL` partiel | PR #27 ; couche `application`, coordinateur et stockage feedback extraits | `actions.py` et PositionAgent restent volumineux | extraire seulement sur gain mesuré |
| C-13 | polygones extrêmes parfois non échantillonnables | P3 | R5 | `QUALIFIÉ_LOCAL` | PR #18 ; 271/271 final, graines extrêmes | repli borné non uniforme vers un sommet | aucune sans nouveau contrat d'échantillonnage |
| C-14 | doublon catalogue écrasé avant contrôle | P3 | R5 | `QUALIFIÉ_LOCAL` | PR #18 ; commandes/actions/événements protégés | paramètres inconnus toujours tolérés par compatibilité | versionner le contrat avant rejet strict |
| C-15 | chemins Build Tools/SDK non découvrables | P2/P3 | R4 | `QUALIFIÉ_LOCAL` | PR #17 ; builds et outils découverts | build bit-à-bit non garanti | aucune exigence CI externe |
| C-16 | statuts documentaires contradictoires | P2 documentaire | R6 | `DOCUMENTÉ` | PR R6 ; présente matrice et documents consolidés | fusion R6 encore soumise à décision | revue documentaire puis décision de fusion |
| C-17 | répétitions techniques et persistances séparées | P3 optionnel | R5 | `DIFFÉRÉ` | PR #18 ; analyse sans mutualisation | contrats de stockage distincts | mandat spécifique seulement si gain démontré |

## Réserves officielles

### Code et conception

- C-11 est corrigé et qualifié par la PR #27 ; C-12 est réduit sans réécriture
  générale. C-09 et C-17 restent différés.
- L'annulation WinRT demeure best-effort ; la terminaison défaillante impose une
  récupération explicite.
- Le quota de capture n'est pas une transaction entre processus indépendants.
- Le descripteur HID actuel ne fournit pas de roulette horizontale.

### Qualification

- Aucun correctif R1–R5 n'a été requalifié matériellement.
- Sept diagnostics matériels sont exclus des profils locaux.
- Les builds ne sont pas garantis reproductibles bit-à-bit.
- Les revues ChatGPT des PR #13–#18 sont des lectures indépendantes des diffs et
  preuves ; elles n'ont pas réexécuté les suites Windows, sauf qualification
  Codex publiée séparément aux SHA finaux R4/R5.

### Exploitation

- La libération physique d'un bouton peut rester incertaine après une rupture de
  transport malgré l'état logiciel `UNKNOWN` et la quarantaine.
- Les récupérations après panne sont bornées et peuvent aboutir à
  `RECOVERY_REQUIRED`.
- La latence LAN aller simple absolue reste inconnue sans synchronisation
  d'horloges ; une reprise GATT transitoire peut précéder l'abonnement stable.
- Le processus mutable observé au début de l'audit du 27 novembre a été remplacé
  par une release immuable vérifiée, après sauvegarde et contrôle du rollback.

## Qualification et gouvernance

La commande officielle est :

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

Les profils `software`, `build` et `full-local` sont locaux sous Windows. Aucun
GitHub Actions ni service CI externe n'est utilisé. Les diagnostics matériels,
l'accès cible, l'installation et le déploiement restent séparés et soumis à une
autorisation explicite.
