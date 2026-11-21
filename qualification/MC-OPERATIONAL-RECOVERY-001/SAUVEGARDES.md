# Sauvegardes et restauration

## Sauvegarde créée

Une copie locale non publiable a été créée sous :

`backups/MC-OPERATIONAL-RECOVERY-001/snapshot-20261121-pre-recovery/`

Elle contient `runtime`, `state`, `logs`, `releases`, `staging` et
`source/out`, y compris les configurations DPAPI et artefacts antérieurs.

| Contrôle | Résultat |
|---|---|
| Fichiers manifestés | 67 |
| Volume | 915 495 octets |
| SHA-256 du manifeste | `14F9CB8E0E7EB9F8CFE7794B8E0896E90811B13935F5AA4B8C5EA1C0DF835891` |
| Vérification source/copie | 0 fichier absent ou divergent |
| Référence Git de sauvegarde | `backup/mc-operational-recovery-001-pre-sync` → `34b2612…` |

Le manifeste détaillé et les fichiers sensibles restent hors GitHub.

## Restauration prévue

1. Ne démarrer aucun composant.
2. Vérifier que les tâches et processus concernés sont arrêtés sous un mandat
   opérationnel distinct.
3. Comparer les empreintes courantes au manifeste avant remplacement.
4. Restaurer ensemble journal d'actions et `.ids`, puis index et images de
   capture ; ne jamais restaurer un seul membre d'une paire persistante.
5. Restaurer la configuration contrôleur et les artefacts par copie atomique.
6. Vérifier toutes les empreintes après restauration.
7. Conserver un marqueur `RECOVERY_REQUIRED` si l'état est ambigu ; ne pas
   tenter une nouvelle activation automatique.
