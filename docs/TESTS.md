# Tests et qualification

## Qualification locale officielle

La décision R4 exclut GitHub Actions et toute CI externe. Les trois profils
fermés sont :

| Profil | Contenu | Exclusions structurelles |
|---|---|---|
| `software` | tests unitaires et intégrations simulées | diagnostics matériels, SSH, installation, déploiement |
| `build` | compilation Python, référence API, syntaxe PowerShell, PositionAgent | exécution des scripts analysés et installation |
| `full-local` | `software` puis `build` | mêmes exclusions |

Commande de référence :

```powershell
python -B scripts/qualification/qualify.py --profile full-local
```

Les sept diagnostics matériels exclus sont trois diagnostics Bluetooth et
quatre diagnostics cible/session. Ils restent hors orchestrateur et exigent une
autorisation explicite.

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
